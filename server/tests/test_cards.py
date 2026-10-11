from app.services.ordering import STEP, midpoint, needs_rebalance

from .conftest import make_card


def titles_in_column(client, headers, board_id, column_id):
    board = client.get(f"/api/boards/{board_id}", headers=headers).json()
    col = next(c for c in board["columns"] if c["id"] == column_id)
    return [c["title"] for c in col["cards"]]


def test_cards_append_in_order(client, alice, board, column):
    for title in ("a", "b", "c"):
        make_card(client, alice["headers"], column["id"], title)
    assert titles_in_column(client, alice["headers"], board["id"], column["id"]) == ["a", "b", "c"]


def test_move_within_column(client, alice, board, column):
    a = make_card(client, alice["headers"], column["id"], "a")
    b = make_card(client, alice["headers"], column["id"], "b")
    c = make_card(client, alice["headers"], column["id"], "c")
    # move c between a and b
    res = client.post(
        f"/api/cards/{c['id']}/move",
        json={"column_id": column["id"], "before_id": a["id"], "after_id": b["id"]},
        headers=alice["headers"],
    )
    assert res.status_code == 200
    assert titles_in_column(client, alice["headers"], board["id"], column["id"]) == ["a", "c", "b"]


def test_move_across_columns(client, alice, board, column):
    other = client.post(
        f"/api/boards/{board['id']}/columns", json={"title": "Done"}, headers=alice["headers"]
    ).json()
    a = make_card(client, alice["headers"], column["id"], "a")
    res = client.post(
        f"/api/cards/{a['id']}/move",
        json={"column_id": other["id"], "before_id": None, "after_id": None},
        headers=alice["headers"],
    )
    assert res.status_code == 200
    assert titles_in_column(client, alice["headers"], board["id"], column["id"]) == []
    assert titles_in_column(client, alice["headers"], board["id"], other["id"]) == ["a"]


def test_move_rejects_neighbours_from_wrong_column(client, alice, board, column):
    other = client.post(
        f"/api/boards/{board['id']}/columns", json={"title": "Done"}, headers=alice["headers"]
    ).json()
    a = make_card(client, alice["headers"], column["id"], "a")
    stranger = make_card(client, alice["headers"], other["id"], "stranger")
    res = client.post(
        f"/api/cards/{a['id']}/move",
        json={"column_id": column["id"], "before_id": stranger["id"], "after_id": None},
        headers=alice["headers"],
    )
    assert res.status_code == 422


def test_patch_card_fields(client, alice, board, column):
    a = make_card(client, alice["headers"], column["id"], "a")
    res = client.patch(
        f"/api/cards/{a['id']}",
        json={"description": "details", "labels": ["bug", "urgent"]},
        headers=alice["headers"],
    )
    assert res.status_code == 200
    assert res.json()["labels"] == ["bug", "urgent"]
    assert res.json()["title"] == "a"  # unset fields untouched


def test_delete_card(client, alice, board, column):
    a = make_card(client, alice["headers"], column["id"], "a")
    assert client.delete(f"/api/cards/{a['id']}", headers=alice["headers"]).status_code == 204
    assert titles_in_column(client, alice["headers"], board["id"], column["id"]) == []


def test_non_member_cannot_touch_cards(client, alice, bob, board, column):
    a = make_card(client, alice["headers"], column["id"], "a")
    res = client.patch(f"/api/cards/{a['id']}", json={"title": "x"}, headers=bob["headers"])
    assert res.status_code == 404


def test_repeated_top_insertion_triggers_rebalance(client, alice, board, column):
    """Squeeze positions until the midpoint gap underflows, forcing a rebalance."""
    make_card(client, alice["headers"], column["id"], "anchor")
    cards = [make_card(client, alice["headers"], column["id"], f"c{i}") for i in range(60)]
    # repeatedly move each card to the very top: gap halves every time
    for card in cards:
        board_state = client.get(f"/api/boards/{board['id']}", headers=alice["headers"]).json()
        col = next(c for c in board_state["columns"] if c["id"] == column["id"])
        top = col["cards"][0]
        res = client.post(
            f"/api/cards/{card['id']}/move",
            json={"column_id": column["id"], "before_id": None, "after_id": top["id"]},
            headers=alice["headers"],
        )
        assert res.status_code == 200, res.text
    titles = titles_in_column(client, alice["headers"], board["id"], column["id"])
    assert len(titles) == 61
    assert titles[0] == "c59"  # last one moved ends up on top
    # positions must all be distinct and strictly increasing
    board_state = client.get(f"/api/boards/{board['id']}", headers=alice["headers"]).json()
    col = next(c for c in board_state["columns"] if c["id"] == column["id"])
    positions = [c["position"] for c in col["cards"]]
    assert positions == sorted(positions)
    assert len(set(positions)) == len(positions)
    # a rebalance must have kept gaps healthy; without one the gap would be ~1e-15
    assert all(b - a > 1e-9 for a, b in zip(positions, positions[1:]))


def test_ordering_unit():
    assert midpoint(None, None) == STEP
    assert midpoint(None, 10.0) == 5.0
    assert midpoint(10.0, None) == 10.0 + STEP
    assert midpoint(1.0, 2.0) == 1.5
    assert not needs_rebalance(None, 5.0)
    assert not needs_rebalance(5.0, None)
    assert needs_rebalance(1.0, 1.0 + 1e-12)
    assert needs_rebalance(None, 1e-12)
