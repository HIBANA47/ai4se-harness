from __future__ import annotations
from fastapi import APIRouter, WebSocket, WebSocketDisconnect, HTTPException

router = APIRouter()
_state = {"state": "idle", "bug_report": None}
_ws_connections: list[WebSocket] = []

@router.get("/api/status")
async def status():
    return _state

@router.post("/api/run")
async def run(body: dict = None):
    report = body.get("bug_report") if body else None
    if not report:
        raise HTTPException(status_code=400, detail="bug_report required")
    _state["state"] = "running"
    _state["bug_report"] = report
    return {"status": "started", "bug_report": report}

@router.websocket("/ws")
async def websocket(ws: WebSocket):
    await ws.accept()
    _ws_connections.append(ws)
    try:
        while True:
            data = await ws.receive_json()
            if data.get("type") == "hitl_response":
                for conn in _ws_connections:
                    await conn.send_json({"type": "hitl_decision", "decision": data["decision"]})
    except WebSocketDisconnect:
        _ws_connections.remove(ws)