import { useEffect, useMemo, useState } from "react";

import CameraControls from "../components/CameraControls";
import LiveControls from "../components/LiveControls";
import MlStatusCard from "../components/MlStatusCard";
import RecentSessions from "../components/RecentSessions";
import ZoneCard from "../components/ZoneCard";
import { wsLiveUrl } from "../config/runtime";
import { fetchMlStatus, fetchRecentSessions, type MlStatusResponse, type RecentSession } from "../services/apiClient";
import { LiveWsClient, type LiveUpdatePayload, type ZoneResponse } from "../services/wsClient";
import { exerciseLabel } from "../utils/labels";

const initialZone = {
  zone_id: "treadmill_zone_1",
  status: "Free",
  dwell_seconds: 0,
  current_exercise: null,
  exercise_seconds: 0,
  rep_count: 0,
  total_exercise_seconds: 0,
  total_rep_count: 0,
  form_score: 100,
} as const;

export default function Dashboard() {
  const [sessions, setSessions] = useState<RecentSession[]>([]);
  const [mlStatus, setMlStatus] = useState<MlStatusResponse | null>(null);
  const [lastMessage, setLastMessage] = useState<ZoneResponse>({
    zone: initialZone,
    sadla_phase: "Neutral",
    minutes_to_free: 15,
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
    const loadData = async () => {
      try {
        const data = await fetchRecentSessions(lastMessage.zone.zone_id);
        setSessions(data);
      } catch {
        // Игнорируем кратковременную недоступность API на раннем этапе запуска.
      }
      try {
        const status = await fetchMlStatus();
        setMlStatus(status);
      } catch {
        // ML-статус может быть недоступен до первого retrain.
      }
    };
    void loadData();
    const timer = window.setInterval(() => {
      void loadData();
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
        exerciseSeconds={lastMessage.zone.exercise_seconds}
        reps={lastMessage.zone.rep_count}
        totalExerciseSeconds={lastMessage.zone.total_exercise_seconds}
        totalReps={lastMessage.zone.total_rep_count}
        minutesToFree={lastMessage.minutes_to_free ?? 15}
        formScore={lastMessage.zone.form_score}
        phase={lastMessage.sadla_phase}
      />
      <LiveControls onSend={send} />
      <CameraControls onLiveEvent={send} />
      <MlStatusCard status={mlStatus} />
      <RecentSessions sessions={sessions} />
    </main>
  );
}
