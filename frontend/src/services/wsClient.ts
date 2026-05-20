export type LiveUpdatePayload = {
  zone_id: string;
  is_present: boolean;
  exercise?: "ResistanceBand" | "PushUps" | "Squats" | "RunInPlace";
  phase?: "Neutral" | "TransitionDown" | "Bottom" | "TransitionUp" | "Standing";
  form_penalty?: number;
};

export type ZoneResponse = {
  zone: {
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
  sadla_phase: string;
  minutes_to_free?: number;
  supported_exercises: string[];
};

export class LiveWsClient {
  private socket: WebSocket;

  constructor(url: string, onMessage: (message: ZoneResponse) => void) {
    this.socket = new WebSocket(url);
    this.socket.onmessage = (event) => {
      onMessage(JSON.parse(event.data) as ZoneResponse);
    };
  }

  send(payload: LiveUpdatePayload): void {
    if (this.socket.readyState === WebSocket.OPEN) {
      this.socket.send(JSON.stringify(payload));
    }
  }
}
