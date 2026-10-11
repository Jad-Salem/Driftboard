"""Seed demo data: `python -m app.seed`

Creates two demo accounts and a populated board so the app has something to
show on first run. Idempotent: skips if the demo user already exists.

Demo logins:  Jad.Salem.Official@gmail.com / demopassword
              maya@example.com / demopassword
"""

import asyncio

from sqlalchemy import select

from .auth import hash_password
from .config import get_settings
from .database import Base, build_engine
from .models import Board, BoardColumn, BoardMember, Card, User
from .services.ordering import STEP

COLUMNS: list[tuple[str, list[tuple[str, list[str]]]]] = [
    ("Backlog", [
        ("Design onboarding flow", ["design"]),
        ("Spike: evaluate CRDTs for offline mode", ["research"]),
        ("Add card due dates", []),
    ]),
    ("In progress", [
        ("Rate-limit auth endpoints", ["backend", "security"]),
        ("Board switcher keyboard shortcuts", ["frontend"]),
    ]),
    ("Review", [
        ("WebSocket reconnect with backoff", ["frontend", "realtime"]),
    ]),
    ("Done", [
        ("Fractional ordering for drag & drop", ["backend"]),
        ("Presence avatars", ["frontend", "realtime"]),
        ("JWT auth", ["backend", "security"]),
    ]),
]


async def seed() -> None:
    settings = get_settings()
    engine, sessionmaker = build_engine(settings.database_url)
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)

    async with sessionmaker() as session:
        if await session.scalar(select(User).where(User.username == "demo")):
            print("Demo data already present, nothing to do.")
            return
        demo = User(
            # stored lowercase: login lowercases the submitted email before lookup
            email="jad.salem.official@gmail.com", username="demo",
            password_hash=hash_password("demopassword"),
        )
        maya = User(
            email="maya@example.com", username="maya",
            password_hash=hash_password("demopassword"),
        )
        session.add_all([demo, maya])
        await session.flush()

        board = Board(title="Product launch", owner_id=demo.id)
        board.members.append(BoardMember(user_id=demo.id, role="owner"))
        board.members.append(BoardMember(user_id=maya.id, role="member"))
        session.add(board)
        await session.flush()

        for ci, (col_title, cards) in enumerate(COLUMNS):
            column = BoardColumn(board_id=board.id, title=col_title, position=(ci + 1) * STEP)
            session.add(column)
            await session.flush()
            for i, (title, labels) in enumerate(cards):
                session.add(Card(
                    column_id=column.id, board_id=board.id, title=title,
                    labels=labels, position=(i + 1) * STEP, created_by=demo.id,
                ))
        await session.commit()
        print("Seeded demo board. Log in with Jad.Salem.Official@gmail.com / demopassword")

    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(seed())
