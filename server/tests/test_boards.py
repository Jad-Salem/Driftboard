def test_create_and_list_boards(client, alice, board):
    res = client.get("/api/boards", headers=alice["headers"])
    assert res.status_code == 200
    assert [b["title"] for b in res.json()] == ["Launch plan"]


def test_board_detail_includes_columns_and_members(client, alice, board, column):
    res = client.get(f"/api/boards/{board['id']}", headers=alice["headers"])
    assert res.status_code == 200
    body = res.json()
    assert body["columns"][0]["title"] == "Todo"
    assert body["members"][0]["user"]["username"] == "alice"
    assert body["members"][0]["role"] == "owner"


def test_non_member_gets_404_not_403(client, bob, board):
    """Board existence should not leak to non-members."""
    res = client.get(f"/api/boards/{board['id']}", headers=bob["headers"])
    assert res.status_code == 404


def test_member_invite_flow(client, alice, bob, board):
    res = client.post(
        f"/api/boards/{board['id']}/members",
        json={"email": "bob@example.com"},
        headers=alice["headers"],
    )
    assert res.status_code == 201
    assert res.json()["user"]["username"] == "bob"

    # bob can now see the board
    res = client.get(f"/api/boards/{board['id']}", headers=bob["headers"])
    assert res.status_code == 200

    # duplicate invite conflicts
    res = client.post(
        f"/api/boards/{board['id']}/members",
        json={"email": "bob@example.com"},
        headers=alice["headers"],
    )
    assert res.status_code == 409


def test_only_owner_can_invite_or_delete(client, alice, bob, board):
    client.post(
        f"/api/boards/{board['id']}/members",
        json={"email": "bob@example.com"},
        headers=alice["headers"],
    )
    res = client.post(
        f"/api/boards/{board['id']}/members",
        json={"email": "alice@example.com"},
        headers=bob["headers"],
    )
    assert res.status_code == 403
    assert client.delete(f"/api/boards/{board['id']}", headers=bob["headers"]).status_code == 403
    assert client.delete(f"/api/boards/{board['id']}", headers=alice["headers"]).status_code == 204


def test_activity_feed_records_mutations(client, alice, board, column):
    res = client.get(f"/api/boards/{board['id']}/activity", headers=alice["headers"])
    assert res.status_code == 200
    verbs = [a["verb"] for a in res.json()]
    assert "board.created" in verbs
    assert "column.created" in verbs
