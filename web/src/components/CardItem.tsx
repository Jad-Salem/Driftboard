import { Draggable } from "@hello-pangea/dnd";

import type { Card } from "../api/types";
import { hueFor } from "../lib/colors";

interface Props {
  card: Card;
  index: number;
  onOpen: (card: Card) => void;
}

export function CardItem({ card, index, onOpen }: Props) {
  return (
    <Draggable draggableId={`card-${card.id}`} index={index}>
      {(provided, snapshot) => (
        <article
          className={`card ${snapshot.isDragging ? "dragging" : ""}`}
          ref={provided.innerRef}
          {...provided.draggableProps}
          {...provided.dragHandleProps}
          onClick={() => onOpen(card)}
        >
          {card.labels.length > 0 && (
            <div className="label-row">
              {card.labels.map((label) => (
                <span
                  key={label}
                  className="label"
                  style={{ backgroundColor: `hsl(${hueFor(label)} 60% 38%)` }}
                >
                  {label}
                </span>
              ))}
            </div>
          )}
          <p>{card.title}</p>
          {card.description && <span className="has-description">≡</span>}
        </article>
      )}
    </Draggable>
  );
}
