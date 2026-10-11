import { FormEvent, useEffect, useState } from "react";

import { useAuth } from "../store/auth";
import { useBoard } from "../store/board";

export function BoardsPage() {
  const { user, token, logout } = useAuth();
  const { boards, boardsLoaded, loadBoards, createBoard, deleteBoard, openBoard } = useBoard();
  const [title, setTitle] = useState("");

  useEffect(() => {
    void loadBoards();
  }, [loadBoards]);

  const submit = (e: FormEvent) => {
    e.preventDefault();
    if (!title.trim()) return;
    void createBoard(title.trim());
    setTitle("");
  };

  return (
    <div className="boards-page">
      <header className="top-bar">
        <h1 className="logo">
          Drift<span>board</span>
        </h1>
        <div className="top-bar-right">
          <span className="muted">{user?.username}</span>
          <button className="btn ghost" onClick={logout}>
            Sign out
          </button>
        </div>
      </header>

      <main className="boards-main">
        <form className="board-composer" onSubmit={submit}>
          <input
            placeholder="Start a new board…"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={120}
          />
          <button className="btn primary" disabled={!title.trim()}>
            Create
          </button>
        </form>

        {boardsLoaded && boards.length === 0 && (
          <p className="empty-state">No boards yet — create your first one above.</p>
        )}

        <div className="board-grid">
          {boards.map((b) => (
            <div
              key={b.id}
              className="board-tile"
              onClick={() => token && void openBoard(b.id, token)}
            >
              <h3>{b.title}</h3>
              <span className="muted">
                created {new Date(b.created_at + "Z").toLocaleDateString()}
              </span>
              {b.owner_id === user?.id && (
                <button
                  className="tile-delete"
                  title="Delete board"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (confirm(`Delete "${b.title}"? This cannot be undone.`)) {
                      void deleteBoard(b.id);
                    }
                  }}
                >
                  ×
                </button>
              )}
            </div>
          ))}
        </div>
      </main>
    </div>
  );
}
