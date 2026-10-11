from contextlib import asynccontextmanager

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy import select

from .auth import decode_token
from .config import Settings, get_settings
from .database import Base, build_engine
from .models import BoardMember, User
from .routers import auth, boards, cards, columns
from .ws import ConnectionManager


def create_app(settings: Settings | None = None) -> FastAPI:
    settings = settings or get_settings()

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        engine, sessionmaker = build_engine(settings.database_url)
        async with engine.begin() as conn:
            await conn.run_sync(Base.metadata.create_all)
        app.state.sessionmaker = sessionmaker
        yield
        await engine.dispose()

    app = FastAPI(title=settings.app_name, lifespan=lifespan)
    app.state.settings = settings
    app.state.ws = ConnectionManager()

    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    for router in (auth.router, boards.router, columns.router, cards.router):
        app.include_router(router, prefix="/api")

    @app.get("/api/health")
    async def health():
        return {"status": "ok"}

    @app.websocket("/ws/boards/{board_id}")
    async def board_ws(websocket: WebSocket, board_id: int):
        manager: ConnectionManager = websocket.app.state.ws
        await websocket.accept()

        user_id = decode_token(websocket.query_params.get("token", ""), settings)
        if user_id is None:
            await websocket.close(code=4401, reason="Invalid token")
            return
        async with websocket.app.state.sessionmaker() as session:
            user = await session.get(User, user_id)
            member = await session.scalar(
                select(BoardMember).where(
                    BoardMember.board_id == board_id, BoardMember.user_id == user_id
                )
            )
        if user is None or member is None:
            await websocket.close(code=4403, reason="Not a board member")
            return

        await manager.connect(board_id, websocket, user.id, user.username)
        await manager.broadcast_presence(board_id)
        try:
            while True:
                # Clients only send heartbeats; all mutations go through REST.
                if await websocket.receive_text() == "ping":
                    await websocket.send_text("pong")
        except WebSocketDisconnect:
            pass
        finally:
            manager.disconnect(board_id, websocket)
            await manager.broadcast_presence(board_id)

    return app


app = create_app()
