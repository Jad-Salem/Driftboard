import type { User } from "../api/types";
import { hueFor } from "../lib/colors";

export function Presence({ users }: { users: User[] }) {
  if (users.length === 0) return null;
  return (
    <div className="presence" title={users.map((u) => u.username).join(", ")}>
      {users.slice(0, 5).map((u) => (
        <span
          key={u.id}
          className="avatar"
          style={{ backgroundColor: `hsl(${hueFor(u.username)} 55% 40%)` }}
        >
          {u.username.slice(0, 2).toUpperCase()}
        </span>
      ))}
      {users.length > 5 && <span className="avatar overflow">+{users.length - 5}</span>}
    </div>
  );
}
