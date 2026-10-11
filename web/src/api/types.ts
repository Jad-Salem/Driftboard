export interface User {
  id: number;
  email: string;
  username: string;
}

export interface AuthResponse {
  access_token: string;
  token_type: string;
  user: User;
}

export interface Board {
  id: number;
  title: string;
  owner_id: number;
  created_at: string;
}

export interface Member {
  user: User;
  role: "owner" | "member";
}

export interface Card {
  id: number;
  column_id: number;
  board_id: number;
  title: string;
  description: string;
  labels: string[];
  position: number;
  created_by: number;
  updated_at: string;
}

export interface Column {
  id: number;
  board_id: number;
  title: string;
  position: number;
}

export interface BoardDetail extends Board {
  columns: (Column & { cards: Card[] })[];
  members: Member[];
}

export interface Activity {
  id: number;
  verb: string;
  detail: Record<string, unknown>;
  created_at: string;
  user: User;
}

export interface WsEvent {
  type: string;
  data: any;
  actor_id: number | null;
  ts: string;
}

export type ConnectionStatus = "connecting" | "live" | "offline";
