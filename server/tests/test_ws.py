from .conftest import make_card


def recv_until(ws, type_, limit=20):
    for _ in range(limit):
        msg = ws.receive_json()
        if msg["type"] == type_:
            return msg
    raise AssertionError(f"never received {type_}")


def test_ws_rejects_bad_token(client, board):
    with client.websocket_connect(f"/ws/boards/{board['id']}?token=junk") as ws:
        # server accepts the handshake, then closes with an app-level code
        import starlette.websockets

        try:
            ws.receive_json()
            raise AssertionError("expected close")
        except starlette.websockets.WebSocketDisconnect as exc:
            assert exc.code == 4401


def test_ws_rejects_non_member(client, bob, board):
    import starlette.websockets

    with client.websocket_connect(f"/ws/boards/{board['id']}?token={bob['token']}") as ws:
        try:
            ws.receive_json()
            raise AssertionError("expected close")
        except starlette.websockets.WebSocketDisconnect as exc:
            assert exc.code == 4403


def test_presence_broadcast_on_join(client, alice, board):
    with client.websocket_connect(f"/ws/boards/{board['id']}?token={alice['token']}") as ws:
        msg = recv_until(ws, "presence")
        assert [u["username"] for u in msg["data"]["users"]] == ["alice"]


def test_card_events_fan_out_to_room(client, alice, board, column):
    with client.websocket_connect(f"/ws/boards/{board['id']}?token={alice['token']}") as ws:
        recv_until(ws, "presence")
        card = make_card(client, alice["headers"], column["id"], "hello")

        created = recv_until(ws, "card.created")
        assert created["data"]["title"] == "hello"
        assert created["actor_id"] == alice["user"]["id"]

        act = recv_until(ws, "activity.created")
        assert act["data"]["verb"] == "card.created"

        client.post(
            f"/api/cards/{card['id']}/move",
            json={"column_id": column["id"], "before_id": None, "after_id": None},
            headers=alice["headers"],
        )
        moved = recv_until(ws, "card.moved")
        assert moved["data"]["card"]["id"] == card["id"]

        client.delete(f"/api/cards/{card['id']}", headers=alice["headers"])
        deleted = recv_until(ws, "card.deleted")
        assert deleted["data"]["id"] == card["id"]


def test_two_clients_see_each_other(client, alice, bob, board):
    client.post(
        f"/api/boards/{board['id']}/members",
        json={"email": "bob@example.com"},
        headers=alice["headers"],
    )
    with client.websocket_connect(f"/ws/boards/{board['id']}?token={alice['token']}") as ws_a:
        recv_until(ws_a, "presence")
        with client.websocket_connect(f"/ws/boards/{board['id']}?token={bob['token']}") as ws_b:
            joined = recv_until(ws_a, "presence")
            users = sorted(u["username"] for u in joined["data"]["users"])
            assert users == ["alice", "bob"]
            recv_until(ws_b, "presence")
        left = recv_until(ws_a, "presence")
        assert [u["username"] for u in left["data"]["users"]] == ["alice"]


def test_heartbeat(client, alice, board):
    with client.websocket_connect(f"/ws/boards/{board['id']}?token={alice['token']}") as ws:
        recv_until(ws, "presence")
        ws.send_text("ping")
        assert ws.receive_text() == "pong"
