from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from ..deps import CurrentUser, ManagerDep, SessionDep, require_board_member
from ..models import BoardColumn, Card
from ..schemas import CardCreateIn, CardOut, CardPatchIn, MoveIn
from ..services import activity
from ..services.ordering import (
    STEP,
    midpoint,
    needs_rebalance,
    rebalance_column,
    resolve_neighbour_positions,
)
from ..ws import event

router = APIRouter(tags=["cards"])


async def _get_card(session, card_id: int, user) -> Card:
    card = await session.get(Card, card_id)
    if card is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Card not found")
    await require_board_member(session, card.board_id, user)
    return card


@router.post(
    "/columns/{column_id}/cards", response_model=CardOut, status_code=status.HTTP_201_CREATED
)
async def create_card(
    column_id: int, body: CardCreateIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    column = await session.get(BoardColumn, column_id)
    if column is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
    await require_board_member(session, column.board_id, user)
    max_pos = await session.scalar(
        select(func.max(Card.position)).where(Card.column_id == column_id)
    )
    card = Card(
        column_id=column_id,
        board_id=column.board_id,
        title=body.title,
        description=body.description,
        position=(max_pos or 0) + STEP,
        created_by=user.id,
    )
    session.add(card)
    await session.flush()
    act = await activity.record(
        session, card.board_id, user, "card.created",
        {"title": card.title, "column": column.title},
    )
    await session.commit()
    payload = CardOut.model_validate(card).model_dump(mode="json")
    await manager.broadcast(card.board_id, event("card.created", payload, user.id))
    await manager.broadcast(card.board_id, event("activity.created", act, user.id))
    return card


@router.patch("/cards/{card_id}", response_model=CardOut)
async def update_card(
    card_id: int, body: CardPatchIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    card = await _get_card(session, card_id, user)
    changed = body.model_dump(exclude_unset=True)
    for field, value in changed.items():
        setattr(card, field, value)
    act = await activity.record(
        session, card.board_id, user, "card.updated",
        {"title": card.title, "fields": sorted(changed)},
    )
    await session.commit()
    payload = CardOut.model_validate(card).model_dump(mode="json")
    await manager.broadcast(card.board_id, event("card.updated", payload, user.id))
    await manager.broadcast(card.board_id, event("activity.created", act, user.id))
    return card


@router.post("/cards/{card_id}/move", response_model=CardOut)
async def move_card(
    card_id: int, body: MoveIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    card = await _get_card(session, card_id, user)
    target = await session.get(BoardColumn, body.column_id)
    if target is None or target.board_id != card.board_id:
        raise HTTPException(422, "Invalid target column")
    from_column_id = card.column_id
    source_title = (await session.get(BoardColumn, from_column_id)).title

    try:
        before, after = await resolve_neighbour_positions(
            session, target.id, body.before_id, body.after_id
        )
        rebalanced: dict[int, float] | None = None
        if needs_rebalance(before, after):
            rebalanced = await rebalance_column(session, target.id)
            before, after = await resolve_neighbour_positions(
                session, target.id, body.before_id, body.after_id
            )
    except ValueError as exc:
        raise HTTPException(422, str(exc))

    card.column_id = target.id
    card.position = midpoint(before, after)
    act = None
    if from_column_id != target.id:
        act = await activity.record(
            session, card.board_id, user, "card.moved",
            {"title": card.title, "from": source_title, "to": target.title},
        )
    await session.commit()
    payload = CardOut.model_validate(card).model_dump(mode="json")
    await manager.broadcast(
        card.board_id,
        event(
            "card.moved",
            {"card": payload, "from_column_id": from_column_id, "rebalanced": rebalanced},
            user.id,
        ),
    )
    if act is not None:
        await manager.broadcast(card.board_id, event("activity.created", act, user.id))
    return card


@router.delete("/cards/{card_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_card(card_id: int, session: SessionDep, user: CurrentUser, manager: ManagerDep):
    card = await _get_card(session, card_id, user)
    board_id, column_id, title = card.board_id, card.column_id, card.title
    await session.delete(card)
    act = await activity.record(session, board_id, user, "card.deleted", {"title": title})
    await session.commit()
    await manager.broadcast(
        board_id, event("card.deleted", {"id": card_id, "column_id": column_id}, user.id)
    )
    await manager.broadcast(board_id, event("activity.created", act, user.id))
