import { useState } from "react";

import type { Card } from "../api/types";
import { hueFor } from "../lib/colors";
import { useBoard } from "../store/board";

interface Props {
  card: Card;
  onClose: () => void;
}

export function CardModal({ card, onClose }: Props) {
  const { updateCard, deleteCard, columns } = useBoard();
  const [title, setTitle] = useState(card.title);
  const [description, setDescription] = useState(card.description);
  const [labels, setLabels] = useState<string[]>(card.labels);
  const [labelInput, setLabelInput] = useState("");

  const column = columns[card.column_id];

  const addLabel = () => {
    const label = labelInput.trim().toLowerCase();
    if (label && !labels.includes(label) && labels.length < 8) {
      setLabels([...labels, label]);
    }
    setLabelInput("");
  };

  const save = () => {
    void updateCard(card.id, {
      title: title.trim() || card.title,
      description,
      labels,
    });
    onClose();
  };

  return (
    <div className="modal-backdrop" onClick={onClose}>
      <div className="modal" onClick={(e) => e.stopPropagation()}>
        <header className="modal-header">
          <input
            className="modal-title"
            value={title}
            onChange={(e) => setTitle(e.target.value)}
            maxLength={300}
          />
          <button className="btn ghost" onClick={onClose}>
            ✕
          </button>
        </header>
        {column && <p className="muted">in {column.title}</p>}

        <label className="modal-label">Description</label>
        <textarea
          rows={5}
          placeholder="Add more detail…"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
        />

        <label className="modal-label">Labels</label>
        <div className="label-row">
          {labels.map((label) => (
            <button
              key={label}
              className="label removable"
              style={{ backgroundColor: `hsl(${hueFor(label)} 60% 38%)` }}
              title="Remove label"
              onClick={() => setLabels(labels.filter((l) => l !== label))}
            >
              {label} ×
            </button>
          ))}
          <input
            className="label-input"
            placeholder="+ label"
            value={labelInput}
            onChange={(e) => setLabelInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === "Enter") {
                e.preventDefault();
                addLabel();
              }
            }}
            onBlur={addLabel}
          />
        </div>

        <footer className="modal-actions">
          <button
            className="btn danger"
            onClick={() => {
              if (confirm("Delete this card?")) {
                void deleteCard(card.id);
                onClose();
              }
            }}
          >
            Delete
          </button>
          <button className="btn primary" onClick={save}>
            Save
          </button>
        </footer>
      </div>
    </div>
  );
}
