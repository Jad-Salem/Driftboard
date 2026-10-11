from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import selectinload

from ..deps import CurrentUser, ManagerDep, SessionDep, require_board_member
from ..models import Activity, Board, BoardColumn, BoardMember, User
from ..schemas import (
    ActivityOut,
    BoardCreateIn,
    BoardDetailOut,
    BoardOut,
    BoardPatchIn,
    MemberAddIn,
    MemberOut,
)
from ..services import activity
from ..ws import event

router = APIRouter(prefix="/boards", tags=["boards"])


@router.get("", response_model=list[BoardOut])
async def list_boards(session: SessionDep, user: CurrentUser):
    boards = await session.scalars(
        select(Board)
        .join(BoardMember, BoardMember.board_id == Board.id)
        .where(BoardMember.user_id == user.id)
        .order_by(Board.created_at.desc())
    )
    return boards.all()


@router.post("", response_model=BoardOut, status_code=status.HTTP_201_CREATED)
async def create_board(body: BoardCreateIn, session: SessionDep, user: CurrentUser):
    board = Board(title=body.title, owner_id=user.id)
    board.members.append(BoardMember(user_id=user.id, role="owner"))
    session.add(board)
    await session.flush()
    await activity.record(session, board.id, user, "board.created", {"title": board.title})
    await session.commit()
    return board


@router.get("/{board_id}", response_model=BoardDetailOut)
async def get_board(board_id: int, session: SessionDep, user: CurrentUser):
    await require_board_member(session, board_id, user)
    board = await session.scalar(
        select(Board)
        .options(
            selectinload(Board.columns).selectinload(BoardColumn.cards),
            selectinload(Board.members).selectinload(BoardMember.user),
        )
        .where(Board.id == board_id)
    )
    return board


@router.patch("/{board_id}", response_model=BoardOut)
async def update_board(
    board_id: int, body: BoardPatchIn, session: SessionDep, user: CurrentUser, manager: ManagerDep
):
    board = await require_board_member(session, board_id, user)
    if body.title is not None:
        board.title = body.title
    act = await activity.record(session, board.id, user, "board.renamed", {"title": board.title})
    await session.commit()
    await manager.broadcast(
        board.id, event("board.updated", {"id": board.id, "title": board.title}, user.id)
    )
    await manager.broadcast(board.id, event("activity.created", act, user.id))
    return board


@router.delete("/{board_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_board(board_id: int, session: SessionDep, user: CurrentUser, manager: ManagerDep):
    board = await require_board_member(session, board_id, user)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can delete a board")
    await session.delete(board)
    await session.commit()
    await manager.broadcast(board_id, event("board.deleted", {"id": board_id}, user.id))


@router.post("/{board_id}/members", response_model=MemberOut, status_code=status.HTTP_201_CREATED)
async def add_member(
    board_id: int,
    body: MemberAddIn,
    session: SessionDep,
    user: CurrentUser,
    manager: ManagerDep,
):
    board = await require_board_member(session, board_id, user)
    if board.owner_id != user.id:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Only the owner can invite members")
    invitee = await session.scalar(select(User).where(User.email == body.email.lower()))
    if invitee is None:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "No user with that email")
    duplicate = await session.scalar(
        select(BoardMember).where(
            BoardMember.board_id == board_id, BoardMember.user_id == invitee.id
        )
    )
    if duplicate is not None:
        raise HTTPException(status.HTTP_409_CONFLICT, "Already a member")
    member = BoardMember(board_id=board_id, user_id=invitee.id, role="member")
    member.user = invitee
    session.add(member)
    act = await activity.record(
        session, board_id, user, "member.added", {"username": invitee.username}
    )
    await session.commit()
    payload = MemberOut.model_validate(member).model_dump(mode="json")
    await manager.broadcast(board_id, event("member.added", payload, user.id))
    await manager.broadcast(board_id, event("activity.created", act, user.id))
    return member


@router.get("/{board_id}/activity", response_model=list[ActivityOut])
async def list_activity(
    board_id: int, session: SessionDep, user: CurrentUser, limit: int = 50
):
    await require_board_member(session, board_id, user)
    rows = await session.scalars(
        select(Activity)
        .options(selectinload(Activity.user))
        .where(Activity.board_id == board_id)
        .order_by(Activity.created_at.desc(), Activity.id.desc())
        .limit(min(limit, 200))
    )
    return rows.all()
