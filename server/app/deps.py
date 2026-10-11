from typing import Annotated, AsyncIterator

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from .auth import decode_token
from .config import Settings
from .models import Board, BoardMember, User
from .ws import ConnectionManager

bearer = HTTPBearer(auto_error=False)


def get_manager(request: Request) -> ConnectionManager:
    return request.app.state.ws


ManagerDep = Annotated[ConnectionManager, Depends(get_manager)]


def get_app_settings(request: Request) -> Settings:
    # read from app.state (not the process-wide cache) so each app instance —
    # including test apps — is self-consistent
    return request.app.state.settings


async def get_session(request: Request) -> AsyncIterator[AsyncSession]:
    async with request.app.state.sessionmaker() as session:
        yield session


SessionDep = Annotated[AsyncSession, Depends(get_session)]
SettingsDep = Annotated[Settings, Depends(get_app_settings)]


async def get_current_user(
    session: SessionDep,
    settings: SettingsDep,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)] = None,
) -> User:
    if credentials is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    user_id = decode_token(credentials.credentials, settings)
    if user_id is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid or expired token")
    user = await session.get(User, user_id)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Unknown user")
    return user


CurrentUser = Annotated[User, Depends(get_current_user)]


async def require_board_member(session: AsyncSession, board_id: int, user: User) -> Board:
    """404 for non-members: don't leak which boards exist."""
    board = await session.get(Board, board_id)
    if board is not None:
        membership = await session.scalar(
            select(BoardMember).where(
                BoardMember.board_id == board_id, BoardMember.user_id == user.id
            )
        )
        if membership is not None:
            return board
    raise HTTPException(status.HTTP_404_NOT_FOUND, "Board not found")
