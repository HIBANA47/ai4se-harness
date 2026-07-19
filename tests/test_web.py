import pytest
from httpx import ASGITransport, AsyncClient


@pytest.fixture
def app():
    from harness.web.app import create_app
    return create_app(config=None)


@pytest.fixture
async def client(app):
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.mark.asyncio
async def test_index_page(client):
    resp = await client.get("/")
    assert resp.status_code == 200


@pytest.mark.asyncio
async def test_status_endpoint(client):
    resp = await client.get("/api/status")
    assert resp.status_code == 200
    data = resp.json()
    assert "state" in data


@pytest.mark.asyncio
async def test_run_endpoint_requires_bug_report(client):
    resp = await client.post("/api/run", json={})
    assert resp.status_code in (400, 422)