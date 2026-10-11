import { DragDropContext, Droppable, DropResult } from "@hello-pangea/dnd";
import { FormEvent, useMemo, useState } from "react";

import type { Card } from "../api/types";
import { useAuth } from "../store/auth";
import { cardsForColumn, selectOrderedColumns, useBoard } from "../store/board";
import { ActivityDrawer } from "./ActivityDrawer";
import { CardModal } from "./CardModal";
import { ColumnView } from "./ColumnView";
import { Presence } from "./Presence";

export function BoardPage() {
  const user = useAuth((s) => s.user);
  const store = useBoard();
  const columns = useMemo(() => selectOrderedColumns(store), [store.columns]); // eslint-disable-line react-hooks/exhaustive-deps
  const [editingTitle, setEditingTitle] = useState<string | null>(null);
  const [newColumn, setNewColumn] = useState("");
  const [openCard, setOpenCard] = useState<Card | null>(null);
  const [showActivity, setShowActivity] = useState(false);

  const isOwner = store.ownerId === user?.id;

  const onDragEnd = (result: DropResult) => {
    const { destination, source, draggableId, type } = result;
    if (!destination) return;
    if (destination.droppableId === source.droppableId && destination.index === source.index) {
      return;
    }

    if (type === "COLUMN") {
      const id = Number(draggableId.replace("col-", ""));
      const rest = columns.filter((c) => c.id !== id);
      const before = rest[destination.index - 1]?.id ?? null;
      const after = rest[destination.index]?.id ?? null;
      void store.moveColumn(id, before, after);
      return;
    }

    const cardId = Number(draggableId.replace("card-", ""));
    const targetColumnId = Number(destination.droppableId.replace("cards-", ""));
    const targetCards = cardsForColumn(store.cards, targetColumnId).filter((c) => c.id !== cardId);
    const before = targetCards[destination.index - 1]?.id ?? null;
    const after = targetCards[destination.index]?.id ?? null;
    void store.moveCard(cardId, targetColumnId, before, after);
  };

  const addColumn = (e: FormEvent) => {
    e.preventDefault();
    if (!newColumn.trim()) return;
    void store.createColumn(newColumn.trim());
    setNewColumn("");
  };

  const invite = () => {
    const email = prompt("Invite a user by email:");
    if (email) void store.inviteMember(email.trim());
  };

  const saveTitle = () => {
    if (editingTitle !== null && editingTitle.trim() && editingTitle !== store.title) {
      void store.renameBoard(editingTitle.trim());
    }
    setEditingTitle(null);
  };

  return (
    <div className="board-page">
      <header className="top-bar">
        <div className="top-bar-left">
          <button className="btn ghost" onClick={() => store.closeBoard()}>
            ← Boards
          </button>
          {editingTitle === null ? (
            <h2 className="board-title" onClick={() => setEditingTitle(store.title)}>
              {store.title}
            </h2>
          ) : (
            <input
              className="board-title-input"
              value={editingTitle}
              autoFocus
              onChange={(e) => setEditingTitle(e.target.value)}
              onBlur={saveTitle}
              onKeyDown={(e) => e.key === "Enter" && saveTitle()}
            />
          )}
          <span className={`status-pill ${store.status}`}>
            {store.status === "live" ? "● Live" : store.status === "offline" ? "○ Reconnecting…" : "○ Connecting…"}
          </span>
        </div>
        <div className="top-bar-right">
          <Presence users={store.presence} />
          {isOwner && (
            <button className="btn ghost" onClick={invite}>
              Invite
            </button>
          )}
          <button
            className="btn ghost"
            onClick={() => {
              setShowActivity(!showActivity);
              if (!showActivity) void store.loadActivity();
            }}
          >
            Activity
          </button>
        </div>
      </header>

      <DragDropContext onDragEnd={onDragEnd}>
        <Droppable droppableId="board" direction="horizontal" type="COLUMN">
          {(provided) => (
            <main className="board-canvas" ref={provided.innerRef} {...provided.droppableProps}>
              {columns.map((col, i) => (
                <ColumnView
                  key={col.id}
                  column={col}
                  index={i}
                  cards={cardsForColumn(store.cards, col.id)}
                  onOpenCard={setOpenCard}
                />
              ))}
              {provided.placeholder}
              <form className="add-column" onSubmit={addColumn}>
                <input
                  placeholder="+ Add column"
                  value={newColumn}
                  onChange={(e) => setNewColumn(e.target.value)}
                  maxLength={120}
                />
                {newColumn.trim() && <button className="btn primary">Add</button>}
              </form>
            </main>
          )}
        </Droppable>
      </DragDropContext>

      {openCard && (
        <CardModal
          card={store.cards[openCard.id] ?? openCard}
          onClose={() => setOpenCard(null)}
        />
      )}
      {showActivity && <ActivityDrawer onClose={() => setShowActivity(false)} />}
    </div>
  );
}
