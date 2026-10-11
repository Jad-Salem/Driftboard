from fastapi import APIRouter, HTTPException, status
from sqlalchemy import select

from ..auth import create_token, hash_password, verify_password
from ..deps import CurrentUser, SessionDep, SettingsDep
from ..models import User
from ..schemas import LoginIn, RegisterIn, TokenOut, UserOut

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/register", response_model=TokenOut, status_code=status.HTTP_201_CREATED)
async def register(body: RegisterIn, session: SessionDep, settings: SettingsDep):
    email = body.email.lower()
    existing = await session.scalar(
        select(User).where((User.email == email) | (User.username == body.username))
    )
    if existing is not None:
        field = "email" if existing.email == email else "username"
        raise HTTPException(status.HTTP_409_CONFLICT, f"That {field} is already taken")
    user = User(email=email, username=body.username, password_hash=hash_password(body.password))
    session.add(user)
    await session.commit()
    return TokenOut(access_token=create_token(user.id, settings), user=UserOut.model_validate(user))


@router.post("/login", response_model=TokenOut)
async def login(body: LoginIn, session: SessionDep, settings: SettingsDep):
    user = await session.scalar(select(User).where(User.email == body.email.lower()))
    if user is None or not verify_password(body.password, user.password_hash):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Incorrect email or password")
    return TokenOut(access_token=create_token(user.id, settings), user=UserOut.model_validate(user))


@router.get("/me", response_model=UserOut)
async def me(user: CurrentUser):
    return user
