import pytest
from fastapi.testclient import TestClient

from app.config import Settings
from app.main import create_app


@pytest.fixture()
def client(tmp_path):
    settings = Settings(
        database_url=f"sqlite+aiosqlite:///{tmp_path}/test.db",
        jwt_secret="test-secret-at-least-32-bytes-long",
    )
    app = create_app(settings)
    with TestClient(app) as client:
        yield client


@pytest.fixture()
def make_user(client):
    counter = iter(range(1, 1000))

    def _make(username: str | None = None):
        n = next(counter)
        username = username or f"user{n}"
        res = client.post(
            "/api/auth/register",
            json={
                "email": f"{username}@example.com",
                "username": username,
                "password": "hunter2hunter2",
            },
        )
        assert res.status_code == 201, res.text
        body = res.json()
        return {
            "user": body["user"],
            "token": body["access_token"],
            "headers": {"Authorization": f"Bearer {body['access_token']}"},
        }

    return _make


@pytest.fixture()
def alice(make_user):
    return make_user("alice")


@pytest.fixture()
def bob(make_user):
    return make_user("bob")


@pytest.fixture()
def board(client, alice):
    res = client.post("/api/boards", json={"title": "Launch plan"}, headers=alice["headers"])
    assert res.status_code == 201, res.text
    return res.json()


@pytest.fixture()
def column(client, alice, board):
    res = client.post(
        f"/api/boards/{board['id']}/columns", json={"title": "Todo"}, headers=alice["headers"]
    )
    assert res.status_code == 201, res.text
    return res.json()


def make_card(client, headers, column_id, title):
    res = client.post(f"/api/columns/{column_id}/cards", json={"title": title}, headers=headers)
    assert res.status_code == 201, res.text
    return res.json()
