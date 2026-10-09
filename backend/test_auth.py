"""Isolated authentication tests; never use the application's real database."""
import hashlib
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

from fastapi import Depends, FastAPI
from fastapi.testclient import TestClient

from app import database
from app.routers import auth, actuators


class AuthTests(unittest.TestCase):
    def setUp(self):
        self.directory = tempfile.TemporaryDirectory()
        self.addCleanup(self.directory.cleanup)
        db_patch = patch.object(database, "DB_FILE", str(Path(self.directory.name) / "test.db"))
        db_patch.start()
        self.addCleanup(db_patch.stop)
        database.init_database()
        app = FastAPI()
        app.include_router(auth.router)
        app.include_router(actuators.router)

        @app.get("/protected", dependencies=[Depends(auth.get_current_user)])
        def protected():
            return {"ok": True}

        self.client = TestClient(app)
        self.addCleanup(self.client.close)
        self.credentials = {"username": "gardener", "password": "a-long-test-password"}

    def register(self):
        response = self.client.post("/api/auth/register", json=self.credentials)
        self.assertEqual(response.status_code, 201)
        self.assertNotIn("password_hash", response.json())

    def login(self):
        response = self.client.post("/api/auth/login", json=self.credentials)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.headers["cache-control"], "no-store")
        return response.json()["access_token"]

    def test_session_lifecycle_and_storage(self):
        self.register()
        token = self.login()
        headers = {"Authorization": f"Bearer {token}"}
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).json()["username"], "gardener")
        self.assertEqual(self.client.get("/protected", headers=headers).status_code, 200)
        conn = database.get_connection()
        try:
            user = conn.execute("SELECT * FROM users").fetchone()
            session = conn.execute("SELECT * FROM user_sessions").fetchone()
            self.assertNotIn(self.credentials["password"], user["password_hash"])
            self.assertEqual(session["token_hash"], hashlib.sha256(token.encode()).hexdigest())
        finally:
            conn.close()
        self.assertEqual(self.client.post("/api/auth/logout", headers=headers).status_code, 204)
        self.assertEqual(self.client.get("/protected", headers=headers).status_code, 401)

    def test_duplicate_and_validation(self):
        self.register()
        duplicate = dict(self.credentials, username=" Gardener ")
        self.assertEqual(self.client.post("/api/auth/register", json=duplicate).status_code, 409)
        for changes in ({"password": "short"}, {"username": "bad user"}, {"password": "x" * 129}):
            self.assertEqual(self.client.post("/api/auth/register", json=dict(self.credentials, **changes)).status_code, 422)

    def test_invalid_credentials(self):
        self.register()
        for changes in ({"password": "wrong-long-password"}, {"username": "unknown"}):
            response = self.client.post("/api/auth/login", json=dict(self.credentials, **changes))
            self.assertEqual(response.status_code, 401)
            self.assertEqual(response.headers["www-authenticate"], "Bearer")
        for headers in ({}, {"Authorization": "Bearer invalid"}, {"Authorization": "Basic abc"}):
            self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)
        self.assertEqual(self.client.post("/api/commands/manual", json={"device": "pump", "action": "ON"}).status_code, 401)
        self.assertEqual(self.client.get("/api/commands").status_code, 401)
        self.assertEqual(self.client.get("/api/commands/pending").status_code, 200)

    def test_expiry_and_independent_sessions(self):
        self.register()
        first, second = self.login(), self.login()
        headers = {"Authorization": f"Bearer {first}"}
        self.client.post("/api/auth/logout", headers=headers)
        headers = {"Authorization": f"Bearer {second}"}
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 200)
        conn = database.get_connection()
        try:
            conn.execute("UPDATE user_sessions SET expires_at = 0")
            conn.commit()
        finally:
            conn.close()
        self.assertEqual(self.client.get("/api/auth/me", headers=headers).status_code, 401)


if __name__ == "__main__":
    unittest.main()
