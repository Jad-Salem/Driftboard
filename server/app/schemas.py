from datetime import datetime

from pydantic import BaseModel, ConfigDict, EmailStr, Field


class ORMModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


# ---- auth ----
class RegisterIn(BaseModel):
    email: EmailStr
    username: str = Field(min_length=2, max_length=50, pattern=r"^[a-zA-Z0-9_.-]+$")
    password: str = Field(min_length=8, max_length=128)


class LoginIn(BaseModel):
    email: EmailStr
    password: str


class UserOut(ORMModel):
    id: int
    email: EmailStr
    username: str


class TokenOut(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserOut


# ---- boards ----
class BoardCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class BoardPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class MemberOut(ORMModel):
    user: UserOut
    role: str


class BoardOut(ORMModel):
    id: int
    title: str
    owner_id: int
    created_at: datetime


class CardOut(ORMModel):
    id: int
    column_id: int
    board_id: int
    title: str
    description: str
    labels: list[str]
    position: float
    created_by: int
    updated_at: datetime


class ColumnSlimOut(ORMModel):
    """Column without its cards; safe to serialize without eager loading."""

    id: int
    board_id: int
    title: str
    position: float


class ColumnOut(ColumnSlimOut):
    cards: list[CardOut] = []


class BoardDetailOut(BoardOut):
    columns: list[ColumnOut] = []
    members: list[MemberOut] = []


# ---- columns / cards ----
class ColumnCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=120)


class ColumnPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=120)


class CardCreateIn(BaseModel):
    title: str = Field(min_length=1, max_length=300)
    description: str = ""


class CardPatchIn(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=300)
    description: str | None = None
    labels: list[str] | None = Field(default=None, max_length=8)


class MoveIn(BaseModel):
    """Place a card in `column_id` strictly between `before_id` and `after_id`."""

    column_id: int
    before_id: int | None = None  # card that ends up immediately above, if any
    after_id: int | None = None  # card that ends up immediately below, if any


class MemberAddIn(BaseModel):
    email: EmailStr


# ---- activity ----
class ActivityOut(ORMModel):
    id: int
    verb: str
    detail: dict
    created_at: datetime
    user: UserOut
