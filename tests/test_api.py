import pytest
from fastapi.testclient import TestClient

from mechabellum_replay_parser.api.app import app


@pytest.fixture(scope="module")
def client():
    with TestClient(app) as c:
        yield c


def test_health_returns_200(client):
    response = client.get("/health")
    assert response.status_code == 200


def test_health_body(client):
    response = client.get("/health")
    assert response.json() == {"status": "ok"}


def test_supply_response_accepted(client):
    response = client.post(
        "/ui/supply-response",
        json={"recommendation_id": "rec_test123", "supply": 500, "cancelled": False},
    )
    assert response.status_code == 204


def test_supply_response_cancelled(client):
    response = client.post(
        "/ui/supply-response",
        json={"recommendation_id": "rec_test456", "supply": None, "cancelled": True},
    )
    assert response.status_code == 204


def test_supply_response_missing_field(client):
    response = client.post(
        "/ui/supply-response",
        json={"supply": 100},
    )
    assert response.status_code == 422
