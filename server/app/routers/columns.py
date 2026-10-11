from fastapi import APIRouter, HTTPException, status
from sqlalchemy import func, select

from ..deps import CurrentUser, ManagerDep, SessionDep, require_board_member
from ..models import BoardColumn
from ..schemas import ColumnCreateIn, ColumnPatchIn, ColumnSlimOut, MoveIn
from ..services import activity
from ..services.ordering import STEP, midpoint, needs_rebalance
from ..ws import event

router = APIRouter(tags=["columns"])


async def _get_column(session, column_id: int, user) -> BoardColumn:
    column = await session.get(BoardColumn, column_id)
    if column is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Column not found")
    await require_board_member(session, column.board_id, user)
    return column


@router.post(
    "/boards/{board_id}/columns", response_model=ColumnSlimOut, status_code=status.HTTP_201_CREATED
)
async def create_column(
    board_id: int, body: ColumnCreateIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    await require_board_member(session, board_id, user)
    max_pos = await session.scalar(
        select(func.max(BoardColumn.position)).where(BoardColumn.board_id == board_id)
    )
    column = BoardColumn(board_id=board_id, title=body.title, position=(max_pos or 0) + STEP)
    session.add(column)
    await session.flush()
    act = await activity.record(session, board_id, user, "column.created", {"title": column.title})
    await session.commit()
    payload = ColumnSlimOut.model_validate(column).model_dump(mode="json")
    await manager.broadcast(board_id, event("column.created", payload, user.id))
    await manager.broadcast(board_id, event("activity.created", act, user.id))
    return column


@router.patch("/columns/{column_id}", response_model=ColumnSlimOut)
async def update_column(
    column_id: int, body: ColumnPatchIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    column = await _get_column(session, column_id, user)
    if body.title is not None:
        column.title = body.title
    await session.commit()
    await manager.broadcast(
        column.board_id,
        event("column.updated", {"id": column.id, "title": column.title}, user.id),
    )
    return column


@router.post("/columns/{column_id}/move", response_model=ColumnSlimOut)
async def move_column(
    column_id: int, body: MoveIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    column = await _get_column(session, column_id, user)

    async def neighbour(cid: int | None) -> float | None:
        if cid is None:
            return None
        other = await session.get(BoardColumn, cid)
        if other is None or other.board_id != column.board_id:
            raise HTTPException(422, "Invalid neighbour column")
        return other.position

    before, after = await neighbour(body.before_id), await neighbour(body.after_id)
    positions: dict[int, float] | None = None
    if needs_rebalance(before, after):
        columns = (
            await session.scalars(
                select(BoardColumn)
                .where(BoardColumn.board_id == column.board_id)
                .order_by(BoardColumn.position, BoardColumn.id)
            )
        ).all()
        positions = {}
        for i, col in enumerate(columns):
            col.position = (i + 1) * STEP
            positions[col.id] = col.position
        before, after = await neighbour(body.before_id), await neighbour(body.after_id)
    column.position = midpoint(before, after)
    if positions is not None:
        positions[column.id] = column.position
    await session.commit()
    await manager.broadcast(
        column.board_id,
        event(
            "column.moved",
            {"id": column.id, "position": column.position, "rebalanced": positions},
            user.id,
        ),
    )
    return column


@router.delete("/columns/{column_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_column(
    column_id: int, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    column = await _get_column(session, column_id, user)
    board_id, title = column.board_id, column.title
    await session.delete(column)
    act = await activity.record(session, board_id, user, "column.deleted", {"title": title})
    await session.commit()
    await manager.broadcast(board_id, event("column.deleted", {"id": column_id}, user.id))
    await manager.broadcast(board_id, event("activity.created", act, user.id))
