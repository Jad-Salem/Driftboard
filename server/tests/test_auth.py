def test_register_and_me(client, alice):
    res = client.get("/api/auth/me", headers=alice["headers"])
    assert res.status_code == 200
    assert res.json()["username"] == "alice"


def test_register_duplicate_email(client, alice):
    res = client.post(
        "/api/auth/register",
        json={"email": "alice@example.com", "username": "other", "password": "hunter2hunter2"},
    )
    assert res.status_code == 409
    assert "email" in res.json()["detail"]


def test_register_rejects_weak_password(client):
    res = client.post(
        "/api/auth/register",
        json={"email": "x@example.com", "username": "x1", "password": "short"},
    )
    assert res.status_code == 422


def test_login_roundtrip(client, alice):
    res = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "hunter2hunter2"}
    )
    assert res.status_code == 200
    assert res.json()["user"]["username"] == "alice"


def test_login_wrong_password(client, alice):
    res = client.post(
        "/api/auth/login", json={"email": "alice@example.com", "password": "wrong-password"}
    )
    assert res.status_code == 401


def test_requests_require_token(client):
    assert client.get("/api/boards").status_code == 401
    assert client.get("/api/auth/me", headers={"Authorization": "Bearer junk"}).status_code == 401
