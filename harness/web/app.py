from __future__ import annotations
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from harness.web.api import router

def create_app(config=None) -> FastAPI:
    app = FastAPI(title="Coding Agent Harness")
    app.state.config = config
    app.include_router(router)

    @app.get("/", response_class=HTMLResponse)
    async def index():
        return """<!DOCTYPE html>
<html>
<head><title>Coding Agent Harness</title><script src="https://unpkg.com/htmx.org@2.0"></script></head>
<body>
<h1>Coding Agent Harness</h1>
<form hx-post="/api/run" hx-target="#result">
<textarea name="bug_report" placeholder="Describe the bug..." rows="5" cols="60"></textarea>
<br><button type="submit">Fix Bug</button>
</form>
<div id="result"></div>
<div id="hitl-modal" style="display:none;">
<h3>Approval Required</h3>
<p id="hitl-reason"></p>
<button onclick="respondHitl('approve')">Approve</button>
<button onclick="respondHitl('reject')">Reject</button>
</div>
<script>
const ws = new WebSocket('ws://' + location.host + '/ws');
ws.onmessage = (e) => {
const data = JSON.parse(e.data);
if (data.type === 'approval_request') {
document.getElementById('hitl-modal').style.display = 'block';
document.getElementById('hitl-reason').textContent = data.reason;
}
if (data.type === 'tool_executed' || data.type === 'feedback') {
document.getElementById('result').innerHTML += '<p>' + JSON.stringify(data) + '</p>';
}
};
function respondHitl(decision) {
ws.send(JSON.stringify({type: 'hitl_response', decision: decision}));
document.getElementById('hitl-modal').style.display = 'none';
}
</script>
</body>
</html>"""

    return app