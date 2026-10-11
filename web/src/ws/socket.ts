import type { ConnectionStatus, WsEvent } from "../api/types";

interface Handlers {
  onEvent: (event: WsEvent) => void;
  onStatus: (status: ConnectionStatus) => void;
  /** Fired on every successful (re)connect after the first, so the caller can reconcile missed state. */
  onReconnect: () => void;
}

const PING_INTERVAL_MS = 25_000;
const MAX_BACKOFF_MS = 8_000;

export class BoardSocket {
  private ws: WebSocket | null = null;
  private attempts = 0;
  private everConnected = false;
  private closed = false;
  private pingTimer: number | undefined;
  private retryTimer: number | undefined;

  constructor(
    private boardId: number,
    private token: string,
    private handlers: Handlers,
  ) {}

  connect() {
    if (this.closed) return;
    this.handlers.onStatus(this.everConnected ? "offline" : "connecting");
    const proto = location.protocol === "https:" ? "wss" : "ws";
    const url = `${proto}://${location.host}/ws/boards/${this.boardId}?token=${encodeURIComponent(this.token)}`;
    const ws = new WebSocket(url);
    this.ws = ws;

    ws.onopen = () => {
      this.attempts = 0;
      this.handlers.onStatus("live");
      if (this.everConnected) this.handlers.onReconnect();
      this.everConnected = true;
      this.pingTimer = window.setInterval(() => ws.send("ping"), PING_INTERVAL_MS);
    };

    ws.onmessage = (msg) => {
      if (msg.data === "pong") return;
      this.handlers.onEvent(JSON.parse(msg.data));
    };

    ws.onclose = (ev) => {
      window.clearInterval(this.pingTimer);
      if (this.closed) return;
      // application-level rejections (bad token / not a member) are permanent
      if (ev.code === 4401 || ev.code === 4403) {
        this.handlers.onStatus("offline");
        return;
      }
      this.handlers.onStatus("offline");
      const backoff = Math.min(MAX_BACKOFF_MS, 500 * 2 ** this.attempts);
      this.attempts += 1;
      this.retryTimer = window.setTimeout(() => this.connect(), backoff + Math.random() * 250);
    };
  }

  close() {
    this.closed = true;
    window.clearInterval(this.pingTimer);
    window.clearTimeout(this.retryTimer);
    this.ws?.close();
  }
}
