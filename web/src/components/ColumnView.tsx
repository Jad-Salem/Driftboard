import { Draggable, Droppable } from "@hello-pangea/dnd";
import { FormEvent, useState } from "react";

import type { Card, Column } from "../api/types";
import { useBoard } from "../store/board";
import { CardItem } from "./CardItem";

interface Props {
  column: Column;
  index: number;
  cards: Card[];
  onOpenCard: (card: Card) => void;
}

export function ColumnView({ column, index, cards, onOpenCard }: Props) {
  const { renameColumn, deleteColumn, createCard } = useBoard();
  const [editing, setEditing] = useState<string | null>(null);
  const [composing, setComposing] = useState(false);
  const [newCard, setNewCard] = useState("");

  const saveTitle = () => {
    if (editing !== null && editing.trim() && editing !== column.title) {
      void renameColumn(column.id, editing.trim());
    }
    setEditing(null);
  };

  const addCard = (e: FormEvent) => {
    e.preventDefault();
    if (!newCard.trim()) return;
    void createCard(column.id, newCard.trim());
    setNewCard("");
  };

  return (
    <Draggable draggableId={`col-${column.id}`} index={index}>
      {(provided, snapshot) => (
        <section
          className={`column ${snapshot.isDragging ? "dragging" : ""}`}
          ref={provided.innerRef}
          {...provided.draggableProps}
        >
          <header className="column-header" {...provided.dragHandleProps}>
            {editing === null ? (
              <h3 onClick={() => setEditing(column.title)}>{column.title}</h3>
            ) : (
              <input
                value={editing}
                autoFocus
                onChange={(e) => setEditing(e.target.value)}
                onBlur={saveTitle}
                onKeyDown={(e) => e.key === "Enter" && saveTitle()}
              />
            )}
            <span className="card-count">{cards.length}</span>
            <button
              className="column-delete"
              title="Delete column"
              onClick={() => {
                if (cards.length === 0 || confirm(`Delete "${column.title}" and its cards?`)) {
                  void deleteColumn(column.id);
                }
              }}
            >
              ×
            </button>
          </header>

          <Droppable droppableId={`cards-${column.id}`} type="CARD">
            {(dropProvided, dropSnapshot) => (
              <div
                className={`card-list ${dropSnapshot.isDraggingOver ? "drag-over" : ""}`}
                ref={dropProvided.innerRef}
                {...dropProvided.droppableProps}
              >
                {cards.map((card, i) => (
                  <CardItem key={card.id} card={card} index={i} onOpen={onOpenCard} />
                ))}
                {dropProvided.placeholder}
              </div>
            )}
          </Droppable>

          {composing ? (
            <form className="card-composer" onSubmit={addCard}>
              <textarea
                placeholder="Card title…"
                value={newCard}
                autoFocus
                rows={2}
                onChange={(e) => setNewCard(e.target.value)}
                onKeyDown={(e) => {
                  if (e.key === "Enter" && !e.shiftKey) {
                    e.preventDefault();
                    addCard(e);
                  }
                  if (e.key === "Escape") setComposing(false);
                }}
              />
              <div className="composer-actions">
                <button className="btn primary" type="submit">
                  Add card
                </button>
                <button className="btn ghost" type="button" onClick={() => setComposing(false)}>
                  Cancel
                </button>
              </div>
            </form>
          ) : (
            <button className="add-card" onClick={() => setComposing(true)}>
              + Add card
            </button>
          )}
        </section>
      )}
    </Draggable>
  );
}
