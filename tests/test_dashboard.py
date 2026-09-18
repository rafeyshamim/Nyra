import pytest
import asyncio
from fastapi.testclient import TestClient
from app.main import app
from app.database.session import init_db


@pytest.fixture(autouse=True)
def setup_test_db():
    asyncio.run(init_db())


client = TestClient(app)


def test_serve_dashboard_ui():
    response = client.get("/")
    assert response.status_code == 200
    assert "Nyra AI" in response.text
    assert "Personal Receptionist Dashboard" in response.text


def test_dashboard_stats_api():
    response = client.get("/api/dashboard/stats")
    assert response.status_code == 200
    data = response.json()
    assert "total_calls" in data
    assert "high_priority_calls" in data
    assert "callbacks_requested" in data
    assert "spam_calls" in data


def test_dashboard_calls_list_api():
    response = client.get("/api/dashboard/calls")
    assert response.status_code == 200
    data = response.json()
    assert "calls" in data
    assert isinstance(data["calls"], list)
