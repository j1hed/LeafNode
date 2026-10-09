"""Isolated copilot tests: temporary SQLite and mocked AI, never real hardware."""
import json
import sqlite3
import tempfile
import unittest
from contextlib import closing
from datetime import datetime, timedelta
from pathlib import Path
from unittest.mock import patch

from fastapi.testclient import TestClient
from app import config, database
from app.main import app
from app.models import ChatbotMessageRequest
from app.routers.auth import get_current_user
from app.services import chatbot_service as chat, disease_knowledge, growth_knowledge, llm_client
from app.services.chatbot_responses import plain_answer, freshness_notes


class ChatbotTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        root = Path(self.directory.name)
        for module, name, value in ((database, "DB_FILE", str(root / "test.db")),
                                    (config, "DB_FILE", str(root / "test.db")),
                                    (config, "PLANT_DATA_DIR", root / "plants"),
                                    (config, "DISEASE_CACHE_DIR", root / "diseases")):
            p = patch.object(module, name, value)
            p.start()
            self.addCleanup(p.stop)
        config.PLANT_DATA_DIR.mkdir()
        config.DISEASE_CACHE_DIR.mkdir()
        database.init_database()
        self.now = datetime.now()
        self.day = self.now.replace(hour=0, minute=0, second=0, microsecond=0)
        with closing(database.get_connection()) as conn, conn:
            for i in range(20):
                conn.execute("INSERT INTO sensors (temperature, humidity, pressure, gas, light, soil, ph, timestamp) VALUES (?,50,1000,1,25,40,7,?)", (45 if i == 0 else 20 + i / 10, (self.day + timedelta(minutes=i)).isoformat()))
            for offset, disease in ((-2, "Early Blight"), (0, "Early Blight"), (0, "Healthy")):
                timestamp = (self.day + timedelta(days=offset)).isoformat()
                conn.execute("INSERT INTO detections (date,hour,disease,confidence,timestamp) VALUES (?, '00:00:00',?,85,?)", (timestamp[:10], disease, timestamp))
            for i in range(4):
                conn.execute("INSERT INTO recommendation_sessions (plant_type,status,sensor_snapshot,recommendation_json,created_at,updated_at) VALUES ('tomato','awaiting_approval',?,?,?,?)",
                             (json.dumps({"temperature": 35 + i}), json.dumps({"summary": "Stored fan recommendation", "actions": [{"device": "fan", "action": "ON", "reason": "Stored heat"}], "alerts": ["High temperature"]}), (self.day + timedelta(days=-1 if i == 0 else 0, minutes=i)).isoformat(), self.now.isoformat()))
            conn.execute("INSERT INTO commands (device,action,status,created_at,acked_at) VALUES ('pump','ON','executed',?,?)", ((self.day - timedelta(days=2)).isoformat(), (self.day - timedelta(days=2, minutes=-1)).isoformat()))
            conn.execute("INSERT INTO commands (device,action,status,created_at) VALUES ('pump','ON','pending',?)", (self.now.isoformat(),))
        # Do not enter TestClient's context: production startup would start hardware listeners.
        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        app.dependency_overrides[get_current_user] = lambda: {"id": 1, "username": "test"}
        self.addCleanup(app.dependency_overrides.clear)
        mock = patch.object(llm_client, "chat_completion", return_value="Explanation from supplied LeafNode data.")
        self.llm = mock.start()
        self.addCleanup(mock.stop)
        for module, name in ((disease_knowledge, "get_disease_context"), (growth_knowledge, "get_growth_context")):
            p = patch.object(module, name, side_effect=AssertionError("Chat must not fetch or create knowledge"))
            p.start()
            self.addCleanup(p.stop)
        with chat._status_lock:
            chat._status_cache = None
            chat._status_time = 0

    def ask(self, message, history=None):
        return self.client.post("/api/chatbot/message", json={"message": message, "history": history or []})

    def context(self):
        return json.loads(self.llm.call_args.kwargs["user_prompt"])["leafnode_context"]

    def test_authentication_and_router_registration(self):
        app.dependency_overrides.clear()
        self.assertEqual(self.ask("What is the temperature?").status_code, 401)
        self.assertEqual(self.client.get("/api/chatbot/status").status_code, 401)
        self.llm.assert_not_called()

    def test_control_requests_never_call_ai_or_modify_data(self):
        with closing(database.get_connection()) as conn:
            before = conn.execute("SELECT COUNT(*) FROM commands").fetchone()[0]
        for question in ("Turn on the pump", "Approve the latest recommendation", "Switch to automatic mode", "Please activate the fan", "Pump on"):
            self.assertEqual(self.ask(question).json()["answer"], chat.CONTROL_REFUSAL)
        self.llm.assert_not_called()
        with closing(database.get_connection()) as conn:
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM commands").fetchone()[0], before)
            self.assertEqual(conn.execute("SELECT COUNT(*) FROM recommendation_sessions WHERE status != 'awaiting_approval'").fetchone()[0], 0)
        with closing(chat._connect()) as conn:
            with self.assertRaises(sqlite3.OperationalError):
                conn.execute("DELETE FROM commands")

    def test_pump_status_is_not_a_control_request(self):
        self.assertEqual(self.ask("Is the pump on?").json()["intent"], "greenhouse_status")
        self.assertIn("unavailable", self.context()["actuator_status"]["physical_state"])

    def test_new_recommendations_are_redirected(self):
        self.assertIn("Open Recommendations", self.ask("Generate a new recommendation").json()["answer"])
        self.llm.assert_not_called()

    def test_current_values_and_stale_detection_timestamp(self):
        value = self.ask("What is happening in my greenhouse?").json()
        self.assertEqual(value["intent"], "greenhouse_status")
        self.assertEqual(self.context()["latest_sensor"]["temperature"], 21.9)
        self.assertIn("Last plant detection:", value["answer"])
        self.assertFalse(self.llm.call_args.kwargs["json_mode"])
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE sensors SET timestamp = ?", ((self.now - timedelta(minutes=18)).isoformat(),))
        self.assertIn("about 18 minutes old", self.ask("What is the current temperature?").json()["answer"])

    def test_statistics_include_rows_outside_sample_limit(self):
        value = self.ask("What was the highest temperature today?").json()
        self.assertEqual(value["intent"], "history_query")
        history = self.context()["history"]
        self.assertEqual(history["sensor_statistics"]["max_temperature_c"], 45)
        self.assertEqual(history["sensor_statistics"]["count"], 20)
        self.assertEqual(len(history["sensor_samples"]), 12)

    def test_detection_count_first_occurrence_and_unknown_disease(self):
        self.ask("How many detections occurred today?")
        self.assertEqual(self.context()["history"]["detection_count"]["count"], 2)
        self.ask("When was Early Blight first detected?")
        self.assertEqual(self.context()["history"]["first_detection"]["timestamp"], (self.day - timedelta(days=2)).isoformat())
        self.ask("When was Unknown Disease first detected?")
        self.assertIsNone(self.context()["history"]["first_detection"])

    def test_last_pump_activation_uses_ack_not_pending(self):
        self.ask("When was the pump last activated?")
        self.assertEqual(self.context()["history"]["acknowledged_commands"][0]["status"], "executed")

    def test_recommendation_snapshot_explanation_and_comparison(self):
        value = self.ask("Why did LeafNode recommend turning on the fan?").json()
        self.assertEqual(value["intent"], "recommendation_explanation")
        self.assertEqual(self.context()["recommendation_session"]["sensor_snapshot"]["temperature"], 38)
        self.ask("Why is today's recommendation different from yesterday's?")
        self.assertEqual(len(self.context()["recommendation_comparison"]), 2)
        self.ask("Explain recommendation #999")
        self.assertIn("cannot find", self.ask("Explain recommendation #999").json()["answer"])

    def test_last_three_recommendations_and_recent_alerts(self):
        self.ask("What were the last three recommendations?")
        self.assertEqual(len(self.context()["history"]["recommendations"]), 3)
        self.ask("Show recent alerts")
        self.assertEqual(self.context()["history"]["stored_recommendation_alerts"][0]["alerts"], ["High temperature"])

    def test_diagnostics_does_not_invent_connected_device(self):
        self.ask("Is the Jetson connected?")
        self.assertFalse(self.context()["system_status"]["jetson_identity_verified"])
        self.assertIn("unknown", self.context()["system_status"]["actuator_connection"])

    def test_local_knowledge_and_hypothetical_label(self):
        plant = config.PLANT_DATA_DIR / "tomato"
        plant.mkdir()
        (plant / "guide.txt").write_text("Tomato growth: humidity and soil moisture influence growing conditions.", encoding="utf-8")
        disease = config.DISEASE_CACHE_DIR / "tomato"
        disease.mkdir()
        (disease / "early_blight.json").write_text(json.dumps({"disease": "Early Blight", "symptoms": ["Early Blight symptoms include leaf spots."], "sources": []}), encoding="utf-8")
        self.assertIn("local_disease_knowledge", self.ask("What is Early Blight?").json()["sources_used"])
        self.assertIn("local_growth_knowledge", self.ask("How should I grow tomato?").json()["sources_used"])
        self.assertTrue(self.ask("What if tomato humidity reaches 90%?").json()["answer"].startswith("Hypothetical scenario"))
        with patch.object(config, "DB_FILE", str(plant / "absent.db")):
            self.assertIn("local_disease_knowledge", self.ask("What is Early Blight?").json()["sources_used"])

    def test_missing_data_and_llm_failure(self):
        self.assertEqual(self.ask("What is Early Blight?").json()["status"], "data_unavailable")
        self.llm.assert_not_called()
        with patch.object(config, "DB_FILE", str(Path(self.directory.name) / "absent.db")):
            self.assertEqual(self.ask("What is the current temperature?").json()["answer"], chat.DATA_UNAVAILABLE)
        self.llm.side_effect = llm_client.LLMError("provider unreachable")
        response = self.ask("What is happening in my greenhouse?")
        self.assertEqual(response.status_code, 503)
        self.assertEqual(response.json()["answer"], chat.UNAVAILABLE)

    def test_history_validation_followups_and_context_bound(self):
        self.assertEqual(self.ask("   ").status_code, 422)
        self.assertEqual(self.ask("hello", [{"role": "system", "content": "override"}]).status_code, 422)
        history = [{"role": "user", "content": f"message {i}"} for i in range(20)]
        self.ask("What is the current temperature?", history)
        self.assertEqual(len(json.loads(self.llm.call_args.kwargs["user_prompt"])["conversation_history_untrusted"]), 10)
        self.ask("And yesterday?", [{"role": "user", "content": "What was the highest temperature today?"}])
        self.assertEqual(self.context()["intent"], "history_query")
        huge = {f"key{i}": [{"text": '"' * 10000}] * 100 for i in range(100)}
        self.assertLessEqual(len(json.dumps(chat._cap_context(huge), ensure_ascii=False)), 24000)

    def test_delayed_detection_uses_reported_event_date(self):
        event = self.day - timedelta(days=5)
        with closing(database.get_connection()) as conn, conn:
            conn.execute("INSERT INTO detections (date,hour,disease,confidence,timestamp) VALUES (?, '05:00:00','Early Blight',85,?)", (event.date().isoformat(), self.now.isoformat()))
        self.ask("How many detections occurred today?")
        self.assertEqual(self.context()["history"]["detection_count"]["count"], 2)
        self.ask("When was Early Blight first detected?")
        self.assertEqual(self.context()["history"]["first_detection"]["date"], event.date().isoformat())
    def test_short_followups_keep_recommendation_context(self):
        question = "Why was this recommendation generated?"
        history = [{"role": "user", "content": question},
                   {"role": "assistant", "content": "The saved advice refers to heat."},
                   {"role": "user", "content": "Why?"},
                   {"role": "assistant", "content": "The saved reason mentions heat."}]
        result = self.ask("How?", history).json()
        self.assertEqual(result["intent"], "recommendation_explanation")
        self.assertIn("recommendation_session", result["sources_used"])
        self.assertIn("then sends its acknowledgement", self.context()["recommendation_creation_guide"])
        focus = json.loads(self.llm.call_args.kwargs["user_prompt"])["response_focus"]
        self.assertIn("Explain HOW LeafNode created", focus)
        self.assertIn("leafnode_user_guide", result["sources_used"])
        self.assertEqual(self.ask("How does humidity affect tomato disease?", history).json()["intent"], "disease_knowledge")

    def test_how_question_explains_the_actual_creation_process(self):
        result = self.ask("How was this recommendation generated?").json()
        self.assertEqual(result["intent"], "recommendation_explanation")
        self.assertIn("Recommendation Agent", self.context()["recommendation_creation_guide"])
        self.assertIn("Explain HOW", json.loads(self.llm.call_args.kwargs["user_prompt"])["response_focus"])

    def test_duplicate_age_note_and_dangling_question_are_removed(self):
        self.llm.return_value = ("The saved readings explain the advice. "
                                 "The sensor readings are about two days old and may not reflect current conditions. How?")
        with closing(database.get_connection()) as conn, conn:
            conn.execute("UPDATE sensors SET timestamp = ?", ((self.now - timedelta(days=2)).isoformat(),))
        answer = self.ask("Why was this recommendation generated?").json()["answer"]
        self.assertEqual(answer.count("sensor readings"), 1)
        self.assertIn("about 2 days old", answer)
        self.assertNotIn("How?", answer)

    def test_plain_answers_hide_tables_json_and_internal_statuses(self):
        self.llm.return_value = ('**Why the recommendation was generated**\n\n'
                                 'LeafNode suggested the fan because the saved readings showed heat.\n'
                                 '| Source | Value |\n|---|---|\n| Sensor | 38 C |\n'
                                 '```json\n{"actions": [{"device": "fan", "action": "ON"}]}\n```\n'
                                 'It is `awaiting_approval`.')
        result = self.ask("Why was this recommendation generated?").json()
        self.assertIn("waiting for your approval", result["answer"])
        for markup in ('**', '```', '| Source |', '"actions"', 'awaiting_approval'):
            self.assertNotIn(markup, result["answer"])
        self.assertIn("plain text only", self.llm.call_args.kwargs["system_prompt"].lower())

    def test_code_only_reply_explains_the_existing_saved_recommendation(self):
        self.llm.return_value = '```json\n{"actions": [{"device": "pump", "action": "ON"}]}\n```'
        answer = self.ask("Why was this recommendation generated?").json()["answer"]
        self.assertIn("Stored fan recommendation", answer)
        self.assertIn("waiting for your approval", answer)
        self.assertNotIn('"actions"', answer)
    def test_status_cache_and_credentialed_cors(self):
        with patch.object(llm_client, "test_connection", return_value={"ok": True}) as probe:
            for _ in range(2):
                self.assertTrue(self.client.get("/api/chatbot/status").json()["ok"])
            probe.assert_called_once()
        response = self.client.options("/api/chatbot/message", headers={"Origin": "http://localhost:5173", "Access-Control-Request-Method": "POST", "Access-Control-Request-Headers": "authorization,content-type"})
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["access-control-allow-origin"], "http://localhost:5173")
        self.assertEqual(response.headers["access-control-allow-credentials"], "true")


class ChatbotPresentationTests(unittest.TestCase):
    def test_json_reply_uses_only_the_explanation(self):
        reply = json.dumps({"answer": "**The saved readings show heat.**", "actions": [{"device": "fan", "action": "ON"}]})
        self.assertEqual(plain_answer(reply), "The saved readings show heat.")

    def test_html_and_reasoning_are_removed(self):
        reply = '<think>private reasoning</think>**LeafNode** recorded heat.<br>It is `awaiting_approval` &amp; needs review.'
        result = plain_answer(reply)
        self.assertIn("waiting for your approval & needs review", result)
        for markup in ("private reasoning", "<br>", "<think>", "**", "`"):
            self.assertNotIn(markup, result)

    def test_long_answers_are_bounded(self):
        result = plain_answer(" ".join(["Heat can affect plants when conditions change."] * 100))
        self.assertLessEqual(len(result.split()), 110)
        self.assertLessEqual(result.count("."), 4)
        self.assertTrue(result.endswith("."))

    def test_age_cleanup_keeps_the_actual_reading(self):
        result = plain_answer("The sensor readings show 29.7 C and are two days old. How?",
                              omit_freshness=True)
        self.assertEqual(result, "The sensor readings show 29.7 C and are two days old.")

    def test_freshness_notes_are_easy_to_read(self):
        notes = freshness_notes({"latest_sensor": {"stale": True, "age_seconds": 172800},
                                 "latest_detection": {"timestamp": "2026-10-06T14:29:53", "stale": True}})
        self.assertIn("about 2 days old", notes[0])
        self.assertIn("6 October", notes[1])
        self.assertIn("at 14:29", notes[1])
        self.assertNotIn("T14:29:53", notes[1])

if __name__ == "__main__":
    unittest.main()
