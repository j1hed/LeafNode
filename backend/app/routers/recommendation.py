

import json
import logging

from fastapi import APIRouter, HTTPException

from app.models import StartSessionRequest, DecisionRequest
from app.services import agent

logger = logging.getLogger("recommendation_router")
router = APIRouter(prefix="/api/recommendation", tags=["recommendation"])


def _serialize(session: dict) -> dict:
    out = dict(session)
    for field in ("sensor_snapshot", "detection_snapshot", "weather_snapshot",
                  "disease_context", "growth_context", "recommendation_json"):
        if out.get(field):
            try:
                out[field] = json.loads(out[field])
            except (json.JSONDecodeError, TypeError):
                pass
    return out


@router.post("/sessions")
def start_session(payload: StartSessionRequest):
    """Step 1: user tells us the plant type. We gather sensor + weather + disease + growth context."""
    if not payload.plant_type.strip():
        raise HTTPException(400, "plant_type is required")

    session_id = agent.create_session(payload.plant_type.strip())
    return _serialize(agent.get_session(session_id))


@router.post("/sessions/{session_id}/generate")
def generate(session_id: int):
    """Step 2: run the LLM over the gathered context and produce a structured recommendation."""
    try:
        agent.generate_recommendation(session_id)
        return _serialize(agent.get_session(session_id))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/sessions/{session_id}")
def get_session(session_id: int):
    try:
        return _serialize(agent.get_session(session_id))
    except ValueError as e:
        raise HTTPException(404, str(e))


@router.get("/sessions")
def list_sessions(limit: int = 50):
    return {"count": limit, "sessions": [_serialize(s) for s in agent.list_sessions(limit)]}


@router.post("/sessions/{session_id}/approve")
def approve(session_id: int, payload: DecisionRequest = None):
    """Step 3: user approves. Any pump/fan actions become pending commands for the ESP32."""
    try:
        command_ids = agent.approve_session(session_id)
        return {
            "status": "approved",
            "session": _serialize(agent.get_session(session_id)),
            "queued_command_ids": command_ids,
        }
    except ValueError as e:
        raise HTTPException(400, str(e))


@router.post("/sessions/{session_id}/reject")
def reject(session_id: int, payload: DecisionRequest = None):
    try:
        agent.reject_session(session_id)
        return {"status": "rejected", "session": _serialize(agent.get_session(session_id))}
    except ValueError as e:
        raise HTTPException(404, str(e))
