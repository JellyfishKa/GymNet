import { useEffect, useMemo, useState } from "react";

import LiveControls from "../components/LiveControls";
import RecentSessions from "../components/RecentSessions";
import ZoneCard from "../components/ZoneCard";
import { wsLiveUrl } from "../config/runtime";
import { fetchRecentSessions, type RecentSession } from "../services/apiClient";
import { LiveWsClient, type LiveUpdatePayload, type ZoneResponse } from "../services/wsClient";
import { exerciseLabel } from "../utils/labels";

const initialZone = {
  zone_id: "treadmill_zone_1",
  status: "Free",
  dwell_seconds: 0,
  current_exercise: null,
  rep_count: 0,
  form_score: 100,
} as const;

export default function Dashboard() {
  const [sessions, setSessions] = useState<RecentSession[]>([]);
  const [lastMessage, setLastMessage] = useState<ZoneResponse>({
    zone: initialZone,
    sadla_phase: "Neutral",
    supported_exercises: ["ResistanceBand", "PushUps", "Squats", "RunInPlace"],
  });

  const ws = useMemo(
    () =>
      new LiveWsClient(wsLiveUrl(), (message) => {
        setLastMessage(message);
      }),
    [],
  );

  useEffect(() => {
    const loadSessions = async () => {
      try {
        const data = await fetchRecentSessions(lastMessage.zone.zone_id);
        setSessions(data);
      } catch {
        // Игнорируем кратковременную недоступность API на раннем этапе запуска.
      }
    };
    void loadSessions();
    const timer = window.setInterval(() => {
      void loadSessions();
    }, 5000);

    return () => {
      // Браузер сам закрывает сокет при размонтировании.
      // Явное закрытие здесь не требуется для текущего MVP.
      window.clearInterval(timer);
    };
  }, [lastMessage.zone.zone_id]);

  const send = (payload: LiveUpdatePayload) => {
    ws.send(payload);
  };

  return (
    <main className="layout">
      <h1>GymNet: панель мониторинга в реальном времени</h1>
      <p>
        Сценарии: {exerciseLabel("ResistanceBand")}, {exerciseLabel("PushUps")}, {exerciseLabel("Squats")},{" "}
        {exerciseLabel("RunInPlace")}
      </p>
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
      <RecentSessions sessions={sessions} />
    </main>
  );
}
