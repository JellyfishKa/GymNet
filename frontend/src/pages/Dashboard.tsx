import { useEffect, useRef, useState } from "react";

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
  const [zoneId, setZoneId] = useState("treadmill_zone_1");
  const [wsConnected, setWsConnected] = useState(false);
  const [sessions, setSessions] = useState<RecentSession[]>([]);
  const [mlStatus, setMlStatus] = useState<MlStatusResponse | null>(null);
  const [lastMessage, setLastMessage] = useState<ZoneResponse>({
    zone: initialZone,
    sadla_phase: "Neutral",
    minutes_to_free: 15,
    supported_exercises: ["ResistanceBand", "PushUps", "Squats", "RunInPlace"],
  });
  const wsRef = useRef<LiveWsClient | null>(null);

  useEffect(() => {
    const client = new LiveWsClient(wsLiveUrl(), {
      onMessage: (message) => {
        setLastMessage(message);
        setWsConnected(true);
      },
      onError: () => setWsConnected(false),
      onClose: () => setWsConnected(false),
    });
    wsRef.current = client;

    return () => {
      client.close();
      wsRef.current = null;
    };
  }, []);

  useEffect(() => {
    const loadData = async () => {
      try {
        const data = await fetchRecentSessions(zoneId);
        setSessions(data);
      } catch {
        // API может быть недоступен сразу после старта контейнеров.
      }
      try {
        const status = await fetchMlStatus();
        setMlStatus(status);
      } catch {
        // ML-статус появится после первого retrain.
      }
    };
    void loadData();
    const timer = window.setInterval(() => {
      void loadData();
    }, 5000);

    return () => {
      window.clearInterval(timer);
    };
  }, [zoneId]);

  const send = (payload: LiveUpdatePayload) => {
    wsRef.current?.send({ ...payload, zone_id: zoneId });
  };

  return (
    <main className="layout">
      <h1>GymNet: панель мониторинга в реальном времени</h1>
      {!wsConnected && (
        <p className="banner-warn">WebSocket отключён — идёт переподключение или backend недоступен.</p>
      )}
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
      <LiveControls zoneId={zoneId} setZoneId={setZoneId} onSend={send} />
      <CameraControls zoneId={zoneId} setZoneId={setZoneId} onLiveEvent={send} />
      <MlStatusCard status={mlStatus} />
      <RecentSessions sessions={sessions} />
    </main>
  );
}
