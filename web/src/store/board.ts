import { create } from "zustand";

import { api, ApiError } from "../api/client";
import type {
  Activity,
  Board,
  BoardDetail,
  Card,
  Column,
  ConnectionStatus,
  Member,
  User,
  WsEvent,
} from "../api/types";
import { BoardSocket } from "../ws/socket";

/** Mirror of the server's fractional-ordering scheme, used for optimistic placement. */
const STEP = 1024;
function midpoint(before: number | null, after: number | null): number {
  if (before === null && after === null) return STEP;
  if (before === null) return (after as number) / 2;
  if (after === null) return before + STEP;
  return (before + after) / 2;
}

interface BoardState {
  boards: Board[];
  boardsLoaded: boolean;

  currentId: number | null;
  title: string;
  ownerId: number | null;
  members: Member[];
  columns: Record<number, Column>;
  cards: Record<number, Card>;
  presence: User[];
  activities: Activity[];
  status: ConnectionStatus;
  error: string | null;

  loadBoards: () => Promise<void>;
  createBoard: (title: string) => Promise<void>;
  deleteBoard: (id: number) => Promise<void>;
  openBoard: (id: number, token: string) => Promise<void>;
  closeBoard: () => void;

  renameBoard: (title: string) => Promise<void>;
  inviteMember: (email: string) => Promise<void>;
  loadActivity: () => Promise<void>;

  createColumn: (title: string) => Promise<void>;
  renameColumn: (id: number, title: string) => Promise<void>;
  deleteColumn: (id: number) => Promise<void>;
  moveColumn: (id: number, beforeId: number | null, afterId: number | null) => Promise<void>;

  createCard: (columnId: number, title: string) => Promise<void>;
  updateCard: (id: number, patch: Partial<Pick<Card, "title" | "description" | "labels">>) => Promise<void>;
  deleteCard: (id: number) => Promise<void>;
  moveCard: (
    id: number,
    columnId: number,
    beforeId: number | null,
    afterId: number | null,
  ) => Promise<void>;
}

let socket: BoardSocket | null = null;

export const useBoard = create<BoardState>((set, get) => {
  const showError = (err: unknown) => {
    const message = err instanceof ApiError ? err.message : "Request failed";
    set({ error: message });
    window.setTimeout(() => {
      if (get().error === message) set({ error: null });
    }, 4000);
  };

  /** Re-fetch the open board; used after reconnects and failed optimistic updates. */
  const refetch = async () => {
    const id = get().currentId;
    if (id === null) return;
    try {
      applyDetail(await api.get<BoardDetail>(`/api/boards/${id}`));
    } catch (err) {
      showError(err);
    }
  };

  const applyDetail = (detail: BoardDetail) => {
    const columns: Record<number, Column> = {};
    const cards: Record<number, Card> = {};
    for (const col of detail.columns) {
      const { cards: colCards, ...slim } = col;
      columns[slim.id] = slim;
      for (const card of colCards) cards[card.id] = card;
    }
    set({
      currentId: detail.id,
      title: detail.title,
      ownerId: detail.owner_id,
      members: detail.members,
      columns,
      cards,
    });
  };

  const applyEvent = (ev: WsEvent) => {
    const s = get();
    switch (ev.type) {
      case "presence":
        set({ presence: ev.data.users });
        break;
      case "board.updated":
        set({ title: ev.data.title });
        break;
      case "board.deleted":
        get().closeBoard();
        break;
      case "member.added":
        set({ members: [...s.members, ev.data] });
        break;
      case "column.created":
      case "column.updated": {
        const existing = s.columns[ev.data.id];
        set({ columns: { ...s.columns, [ev.data.id]: { ...existing, ...ev.data } } });
        break;
      }
      case "column.moved": {
        const columns = { ...s.columns };
        if (ev.data.rebalanced) {
          for (const [id, position] of Object.entries(ev.data.rebalanced)) {
            const col = columns[Number(id)];
            if (col) columns[Number(id)] = { ...col, position: position as number };
          }
        }
        const moved = columns[ev.data.id];
        if (moved) columns[ev.data.id] = { ...moved, position: ev.data.position };
        set({ columns });
        break;
      }
      case "column.deleted": {
        const columns = { ...s.columns };
        delete columns[ev.data.id];
        const cards = Object.fromEntries(
          Object.entries(s.cards).filter(([, c]) => c.column_id !== ev.data.id),
        );
        set({ columns, cards });
        break;
      }
      case "card.created":
      case "card.updated":
        set({ cards: { ...s.cards, [ev.data.id]: ev.data } });
        break;
      case "card.moved": {
        const cards = { ...s.cards };
        if (ev.data.rebalanced) {
          for (const [id, position] of Object.entries(ev.data.rebalanced)) {
            const card = cards[Number(id)];
            if (card) cards[Number(id)] = { ...card, position: position as number };
          }
        }
        cards[ev.data.card.id] = ev.data.card;
        set({ cards });
        break;
      }
      case "card.deleted": {
        const cards = { ...s.cards };
        delete cards[ev.data.id];
        set({ cards });
        break;
      }
      case "activity.created":
        set({ activities: [ev.data, ...s.activities].slice(0, 100) });
        break;
    }
  };

  return {
    boards: [],
    boardsLoaded: false,
    currentId: null,
    title: "",
    ownerId: null,
    members: [],
    columns: {},
    cards: {},
    presence: [],
    activities: [],
    status: "connecting",
    error: null,

    async loadBoards() {
      try {
        set({ boards: await api.get<Board[]>("/api/boards"), boardsLoaded: true });
      } catch (err) {
        showError(err);
      }
    },

    async createBoard(title) {
      try {
        const board = await api.post<Board>("/api/boards", { title });
        set({ boards: [board, ...get().boards] });
      } catch (err) {
        showError(err);
      }
    },

    async deleteBoard(id) {
      try {
        await api.delete(`/api/boards/${id}`);
        set({ boards: get().boards.filter((b) => b.id !== id) });
      } catch (err) {
        showError(err);
      }
    },

    async openBoard(id, token) {
      set({ currentId: id, activities: [], presence: [], status: "connecting" });
      try {
        applyDetail(await api.get<BoardDetail>(`/api/boards/${id}`));
      } catch (err) {
        showError(err);
        set({ currentId: null });
        return;
      }
      socket?.close();
      socket = new BoardSocket(id, token, {
        onEvent: applyEvent,
        onStatus: (status) => set({ status }),
        onReconnect: refetch,
      });
      socket.connect();
    },

    closeBoard() {
      socket?.close();
      socket = null;
      set({ currentId: null, columns: {}, cards: {}, presence: [], activities: [] });
      void get().loadBoards();
    },

    async renameBoard(title) {
      const id = get().currentId;
      if (id === null || !title.trim()) return;
      set({ title }); // optimistic
      try {
        await api.patch(`/api/boards/${id}`, { title });
      } catch (err) {
        showError(err);
        await refetch();
      }
    },

    async inviteMember(email) {
      const id = get().currentId;
      if (id === null) return;
      try {
        const member = await api.post<Member>(`/api/boards/${id}/members`, { email });
        if (!get().members.some((m) => m.user.id === member.user.id)) {
          set({ members: [...get().members, member] });
        }
      } catch (err) {
        showError(err);
      }
    },

    async loadActivity() {
      const id = get().currentId;
      if (id === null) return;
      try {
        set({ activities: await api.get<Activity[]>(`/api/boards/${id}/activity`) });
      } catch (err) {
        showError(err);
      }
    },

    async createColumn(title) {
      const id = get().currentId;
      if (id === null) return;
      try {
        const column = await api.post<Column>(`/api/boards/${id}/columns`, { title });
        set({ columns: { ...get().columns, [column.id]: column } });
      } catch (err) {
        showError(err);
      }
    },

    async renameColumn(id, title) {
      const col = get().columns[id];
      if (!col || !title.trim()) return;
      set({ columns: { ...get().columns, [id]: { ...col, title } } });
      try {
        await api.patch(`/api/columns/${id}`, { title });
      } catch (err) {
        showError(err);
        await refetch();
      }
    },

    async deleteColumn(id) {
      const { columns, cards } = get();
      const next = { ...columns };
      delete next[id];
      set({
        columns: next,
        cards: Object.fromEntries(Object.entries(cards).filter(([, c]) => c.column_id !== id)),
      });
      try {
        await api.delete(`/api/columns/${id}`);
      } catch (err) {
        showError(err);
        await refetch();
      }
    },

    async moveColumn(id, beforeId, afterId) {
      const { columns } = get();
      const col = columns[id];
      if (!col) return;
      const position = midpoint(
        beforeId !== null ? columns[beforeId]?.position ?? null : null,
        afterId !== null ? columns[afterId]?.position ?? null : null,
      );
      set({ columns: { ...columns, [id]: { ...col, position } } });
      try {
        await api.post(`/api/columns/${id}/move`, {
          column_id: id,
          before_id: beforeId,
          after_id: afterId,
        });
      } catch (err) {
        showError(err);
        await refetch();
      }
    },

    async createCard(columnId, title) {
      try {
        const card = await api.post<Card>(`/api/columns/${columnId}/cards`, { title });
        set({ cards: { ...get().cards, [card.id]: card } });
      } catch (err) {
        showError(err);
      }
    },

    async updateCard(id, patch) {
      const card = get().cards[id];
      if (!card) return;
      set({ cards: { ...get().cards, [id]: { ...card, ...patch } } });
      try {
        await api.patch(`/api/cards/${id}`, patch);
      } catch (err) {
        showError(err);
        await refetch();
      }
    },

    async deleteCard(id) {
      const cards = { ...get().cards };
      delete cards[id];
      set({ cards });
      try {
        await api.delete(`/api/cards/${id}`);
      } catch (err) {
        showError(err);
        await refetch();
      }
    },

    async moveCard(id, columnId, beforeId, afterId) {
      const { cards } = get();
      const card = cards[id];
      if (!card) return;
      const position = midpoint(
        beforeId !== null ? cards[beforeId]?.position ?? null : null,
        afterId !== null ? cards[afterId]?.position ?? null : null,
      );
      // optimistic: place immediately, server event will confirm/correct
      set({ cards: { ...cards, [id]: { ...card, column_id: columnId, position } } });
      try {
        await api.post(`/api/cards/${id}/move`, {
          column_id: columnId,
          before_id: beforeId,
          after_id: afterId,
        });
      } catch (err) {
        showError(err);
        await refetch();
      }
    },
  };
});

/** Columns of the open board, in display order. */
export function selectOrderedColumns(s: BoardState): Column[] {
  return Object.values(s.columns).sort((a, b) => a.position - b.position || a.id - b.id);
}

/** Cards of one column, in display order. */
export function cardsForColumn(cards: Record<number, Card>, columnId: number): Card[] {
  return Object.values(cards)
    .filter((c) => c.column_id === columnId)
    .sort((a, b) => a.position - b.position || a.id - b.id);
}
