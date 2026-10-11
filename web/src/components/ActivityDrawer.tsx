import type { Activity } from "../api/types";
import { useBoard } from "../store/board";

function describe(a: Activity): string {
  const d = a.detail as Record<string, string>;
  switch (a.verb) {
    case "board.created":
      return `created the board`;
    case "board.renamed":
      return `renamed the board to “${d.title}”`;
    case "member.added":
      return `invited ${d.username}`;
    case "column.created":
      return `added column “${d.title}”`;
    case "column.deleted":
      return `deleted column “${d.title}”`;
    case "card.created":
      return `added “${d.title}” to ${d.column}`;
    case "card.updated":
      return `updated “${d.title}”`;
    case "card.moved":
      return `moved “${d.title}” from ${d.from} to ${d.to}`;
    case "card.deleted":
      return `deleted “${d.title}”`;
    default:
      return a.verb;
  }
}

function timeAgo(iso: string): string {
  const seconds = Math.max(0, (Date.now() - new Date(iso + "Z").getTime()) / 1000);
  if (seconds < 60) return "just now";
  if (seconds < 3600) return `${Math.floor(seconds / 60)}m ago`;
  if (seconds < 86400) return `${Math.floor(seconds / 3600)}h ago`;
  return `${Math.floor(seconds / 86400)}d ago`;
}

export function ActivityDrawer({ onClose }: { onClose: () => void }) {
  const activities = useBoard((s) => s.activities);
  return (
    <aside className="activity-drawer">
      <header>
        <h3>Activity</h3>
        <button className="btn ghost" onClick={onClose}>
          ✕
        </button>
      </header>
      <ul>
        {activities.length === 0 && <li className="muted">Nothing yet.</li>}
        {activities.map((a) => (
          <li key={a.id}>
            <strong>{a.user.username}</strong> {describe(a)}
            <span className="muted"> · {timeAgo(a.created_at)}</span>
          </li>
        ))}
      </ul>
    </aside>
  );
}
