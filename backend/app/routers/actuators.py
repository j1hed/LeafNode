
import logging
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException

from app.database import get_connection
from app.models import ManualCommandRequest, AckCommandRequest
from app import config
from app.routers.auth import get_current_user

logger = logging.getLogger("actuators_router")
router = APIRouter(prefix="/api/commands", tags=["actuators"])


@router.get("/pending")
def get_pending_commands(device: str = None):
    conn = get_connection()
    if device:
        rows = conn.execute(
            "SELECT * FROM commands WHERE status = 'pending' AND device = ? ORDER BY id ASC",
            (device,),
        ).fetchall()
    else:
        rows = conn.execute(
            "SELECT * FROM commands WHERE status = 'pending' ORDER BY id ASC"
        ).fetchall()
    conn.close()

    return {"count": len(rows), "commands": [dict(r) for r in rows]}


@router.post("/{command_id}/ack")
def ack_command(command_id: int, payload: AckCommandRequest):
    """ESP32 calls this after it has actually toggled the relay."""
    now = datetime.now().isoformat(timespec="seconds")
    status = "executed" if payload.success else "failed"

    conn = get_connection()
    row = conn.execute("SELECT * FROM commands WHERE id = ?", (command_id,)).fetchone()
    if row is None:
        conn.close()
        raise HTTPException(404, f"Command {command_id} not found")

    conn.execute(
        "UPDATE commands SET status = ?, acked_at = ? WHERE id = ?",
        (status, now, command_id),
    )
    conn.commit()
    conn.close()

    logger.info(f"Command #{command_id} acked: {status} ({payload.note or ''})")
    return {"status": status, "command_id": command_id}


@router.post("/manual", dependencies=[Depends(get_current_user)])
def manual_command(payload: ManualCommandRequest):
    """Dashboard override - queue a command directly, no recommendation session involved."""
    device = payload.device.lower()
    action = payload.action.upper()

    if device not in config.KNOWN_DEVICES:
        raise HTTPException(400, f"Unknown device '{device}'. Known devices: {sorted(config.KNOWN_DEVICES)}")
    if action not in ("ON", "OFF"):
        raise HTTPException(400, "action must be 'ON' or 'OFF'")

    now = datetime.now().isoformat(timespec="seconds")
    conn = get_connection()
    cursor = conn.execute(
        """
        INSERT INTO commands (session_id, device, action, duration_minutes, reason, status, created_at)
        VALUES (NULL, ?, ?, ?, ?, 'pending', ?)
        """,
        (device, action, payload.duration_minutes, payload.reason, now),
    )
    command_id = cursor.lastrowid
    conn.commit()
    conn.close()

    return {"status": "queued", "command_id": command_id}


@router.get("", dependencies=[Depends(get_current_user)])
def list_commands(limit: int = 100):
    limit = max(1, min(limit, 1000))
    conn = get_connection()
    rows = conn.execute(
        "SELECT * FROM commands ORDER BY id DESC LIMIT ?", (limit,)
    ).fetchall()
    conn.close()
    return {"count": len(rows), "commands": [dict(r) for r in rows]}
