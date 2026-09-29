import type { PoseIngestResponse } from "./ingestTypes";

export type PoseIngestPayload = {
  zone_id: string;
  roi: { x_min: number; y_min: number; x_max: number; y_max: number };
  landmarks: { name: string; x: number; y: number }[];
};

type LiveIngestWsOptions = {
  onResponse: (response: PoseIngestResponse) => void;
  onError?: (message: string) => void;
  onOpen?: () => void;
};

/**
 * WebSocket ingest: не блокирует MediaPipe; на wire — latest-wins.
 */
export class LiveIngestWsClient {
  private url: string;
  private onResponse: (response: PoseIngestResponse) => void;
  private onError?: (message: string) => void;
  private onOpen?: () => void;

  private socket: WebSocket | null = null;
  private inFlight = false;
  private pending: string | null = null;
  private closedByUser = false;
  private generation = 0;

  constructor(url: string, options: LiveIngestWsOptions) {
    this.url = url;
    this.onResponse = options.onResponse;
    this.onError = options.onError;
    this.onOpen = options.onOpen;
    this.connect();
  }

  private connect(): void {
    this.generation += 1;
    const gen = this.generation;
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      if (gen !== this.generation) {
        return;
      }
      this.onOpen?.();
      this.flushPending();
    };

    this.socket.onmessage = (event) => {
      if (gen !== this.generation) {
        return;
      }
      try {
        const parsed = JSON.parse(String(event.data)) as PoseIngestResponse & { error?: string };
        if (parsed.error) {
          if (parsed.error === "busy") {
            this.inFlight = false;
            window.setTimeout(() => this.flushPending(), 200);
            return;
          }
          this.onError?.(parsed.error);
          this.inFlight = false;
          this.flushPending();
          return;
        }
        this.onResponse(parsed);
      } catch {
        this.onError?.("bad_json");
      } finally {
        this.inFlight = false;
        this.flushPending();
      }
    };

    this.socket.onerror = () => {
      if (gen === this.generation) {
        this.onError?.("ws_error");
      }
    };

    this.socket.onclose = () => {
      if (gen !== this.generation) {
        return;
      }
      this.inFlight = false;
      if (!this.closedByUser) {
        this.onError?.("ws_closed");
      }
    };
  }

  private flushPending(): void {
    if (this.inFlight || !this.pending || this.socket?.readyState !== WebSocket.OPEN) {
      return;
    }
    const body = this.pending;
    this.pending = null;
    this.inFlight = true;
    this.socket.send(body);
  }

  /** true = кадр принят (отправлен или в очереди). */
  submit(payload: PoseIngestPayload): boolean {
    const body = JSON.stringify(payload);
    if (this.inFlight) {
      this.pending = body;
      return true;
    }
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.inFlight = true;
      this.socket.send(body);
      return true;
    }
    if (this.socket?.readyState === WebSocket.CONNECTING) {
      this.pending = body;
      return true;
    }
    return false;
  }

  isOpen(): boolean {
    return this.socket?.readyState === WebSocket.OPEN;
  }

  close(): void {
    this.closedByUser = true;
    this.generation += 1;
    this.pending = null;
    this.inFlight = false;
    this.socket?.close();
    this.socket = null;
  }
}
