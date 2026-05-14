import { useEffect, useMemo, useState } from "react";

import LiveControls from "../components/LiveControls";
import ZoneCard from "../components/ZoneCard";
import { LiveWsClient, type LiveUpdatePayload, type ZoneResponse } from "../services/wsClient";

const initialZone = {
  zone_id: "treadmill_zone_1",
  status: "Free",
  dwell_seconds: 0,
  current_exercise: null,
  rep_count: 0,
  form_score: 100,
} as const;

export default function Dashboard() {
  const [lastMessage, setLastMessage] = useState<ZoneResponse>({
    zone: initialZone,
    sadla_phase: "Neutral",
    supported_exercises: ["ResistanceBand", "PushUps", "Squats", "RunInPlace"],
  });

  const ws = useMemo(
    () =>
      new LiveWsClient("ws://localhost:8000/ws/live", (message) => {
        setLastMessage(message);
      }),
    [],
  );

  useEffect(() => {
    return () => {
      // browser auto-closes socket, explicit close not required for this simple MVP
    };
  }, []);

  const send = (payload: LiveUpdatePayload) => {
    ws.send(payload);
  };

  return (
    <main className="layout">
      <h1>GymNet Live Dashboard</h1>
      <p>Сценарии: ResistanceBand, PushUps, Squats, RunInPlace (treadmill ROI)</p>
      <ZoneCard
        zoneId={lastMessage.zone.zone_id}
        status={lastMessage.zone.status}
        dwellSeconds={lastMessage.zone.dwell_seconds}
        exercise={lastMessage.zone.current_exercise}
        reps={lastMessage.zone.rep_count}
        formScore={lastMessage.zone.form_score}
        phase={lastMessage.sadla_phase}
      />
      <LiveControls onSend={send} />
    </main>
  );
}
