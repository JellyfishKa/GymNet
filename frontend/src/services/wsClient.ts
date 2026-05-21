export type LiveUpdatePayload = {
  zone_id: string;
  is_present: boolean;
  exercise?: "ResistanceBand" | "PushUps" | "Squats" | "RunInPlace";
  phase?: "Neutral" | "TransitionDown" | "Bottom" | "TransitionUp" | "Standing";
  form_penalty?: number;
};

export type ZoneStatePayload = {
  zone_id: string;
  status: "Free" | "Busy" | "Crowded";
  dwell_seconds: number;
  current_exercise: string | null;
  exercise_seconds: number;
  rep_count: number;
  total_exercise_seconds: number;
  total_rep_count: number;
  form_score: number;
};

export type ZoneResponse = {
  zone: ZoneStatePayload;
  sadla_phase: "Neutral" | "TransitionDown" | "Bottom" | "TransitionUp" | "Standing" | string;
  minutes_to_free?: number;
  supported_exercises: string[];
};

type WsClientOptions = {
  onMessage: (message: ZoneResponse) => void;
  onError?: (event: Event) => void;
  onClose?: (event: CloseEvent) => void;
  reconnect?: boolean;
  maxReconnectDelayMs?: number;
};

export class LiveWsClient {
  private url: string;
  private onMessage: (message: ZoneResponse) => void;
  private onError?: (event: Event) => void;
  private onClose?: (event: CloseEvent) => void;
  private reconnectEnabled: boolean;
  private maxReconnectDelayMs: number;

  private socket: WebSocket | null = null;
  private reconnectAttempt = 0;
  private reconnectTimer: number | null = null;
  private closedByUser = false;
  private sendQueue: string[] = [];

  constructor(url: string, options: WsClientOptions) {
    this.url = url;
    this.onMessage = options.onMessage;
    this.onError = options.onError;
    this.onClose = options.onClose;
    this.reconnectEnabled = options.reconnect ?? true;
    this.maxReconnectDelayMs = options.maxReconnectDelayMs ?? 15000;
    this.connect();
  }

  private connect(): void {
    this.socket = new WebSocket(this.url);

    this.socket.onopen = () => {
      this.reconnectAttempt = 0;
      this.flushQueue();
    };

    this.socket.onmessage = (event) => {
      try {
        const parsed = JSON.parse(String(event.data)) as ZoneResponse;
        this.onMessage(parsed);
      } catch {
        // Пропускаем битые сообщения, чтобы не ронять UI.
      }
    };

    this.socket.onerror = (event) => {
      this.onError?.(event);
    };

    this.socket.onclose = (event) => {
      this.onClose?.(event);
      if (!this.closedByUser && this.reconnectEnabled) {
        this.scheduleReconnect();
      }
    };
  }

  private scheduleReconnect(): void {
    if (this.reconnectTimer !== null) {
      return;
    }
    const delay = Math.min(1000 * 2 ** this.reconnectAttempt, this.maxReconnectDelayMs);
    this.reconnectAttempt += 1;
    this.reconnectTimer = window.setTimeout(() => {
      this.reconnectTimer = null;
      this.connect();
    }, delay);
  }

  private flushQueue(): void {
    if (!this.socket || this.socket.readyState !== WebSocket.OPEN) {
      return;
    }
    while (this.sendQueue.length > 0) {
      const payload = this.sendQueue.shift();
      if (payload) {
        this.socket.send(payload);
      }
    }
  }

  send(payload: LiveUpdatePayload): boolean {
    const body = JSON.stringify(payload);
    if (this.socket?.readyState === WebSocket.OPEN) {
      this.socket.send(body);
      return true;
    }
    this.sendQueue.push(body);
    return false;
  }

  close(): void {
    this.closedByUser = true;
    if (this.reconnectTimer !== null) {
      window.clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
    this.socket?.close();
    this.socket = null;
  }
}
