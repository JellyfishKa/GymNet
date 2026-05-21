import { useEffect, useState } from "react";

import CameraControls from "../components/CameraControls";
import MlStatusCard from "../components/MlStatusCard";
import RecentSessions from "../components/RecentSessions";
import ZoneCard from "../components/ZoneCard";
import { fetchMlStatus, fetchRecentSessions, type MlStatusResponse, type RecentSession } from "../services/apiClient";
import type { PoseIngestResponse } from "../services/ingestTypes";
import { exerciseLabel } from "../utils/labels";

const initialZone: PoseIngestResponse["zone"] = {
  zone_id: "treadmill_zone_1",
  status: "Free",
  dwell_seconds: 0,
  current_exercise: null,
  exercise_seconds: 0,
  rep_count: 0,
  total_exercise_seconds: 0,
  total_rep_count: 0,
  form_score: 100,
};

export default function Dashboard() {
  const [zoneId, setZoneId] = useState("treadmill_zone_1");
  const [cameraActive, setCameraActive] = useState(false);
  const [sessions, setSessions] = useState<RecentSession[]>([]);
  const [mlStatus, setMlStatus] = useState<MlStatusResponse | null>(null);
  const [lastMessage, setLastMessage] = useState<PoseIngestResponse>({
    zone_id: "treadmill_zone_1",
    is_present: false,
    exercise: "RunInPlace",
    phase: "Neutral",
    form_penalty: 0,
    minutes_to_free: 15,
    sadla_phase: "Neutral",
    zone: initialZone,
    supported_exercises: ["PushUps", "Squats", "RunInPlace"],
  });

  const handleZoneUpdate = (response: PoseIngestResponse) => {
    setLastMessage(response);
    setCameraActive(true);
  };

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

  const zone = (lastMessage.zone ?? initialZone) as NonNullable<PoseIngestResponse["zone"]>;

  return (
    <main className="layout">
      <h1>GymNet: панель мониторинга в реальном времени</h1>
      {!cameraActive && (
        <p className="banner-warn">Камера не активна — включите камеру, чтобы обновлять зону с ingest.</p>
      )}
      <p>
        Сценарии: {exerciseLabel("PushUps")}, {exerciseLabel("Squats")}, {exerciseLabel("RunInPlace")}
      </p>
      <ZoneCard
        zoneId={zone.zone_id}
        status={zone.status}
        dwellSeconds={zone.dwell_seconds}
        exercise={zone.current_exercise}
        exerciseSeconds={zone.exercise_seconds}
        reps={zone.rep_count}
        repTempoSeconds={zone.rep_tempo_seconds}
        totalExerciseSeconds={zone.total_exercise_seconds}
        totalReps={zone.total_rep_count}
        totalRepTempoSeconds={zone.total_rep_tempo_seconds}
        tracksRepAndTime={zone.tracks_rep_and_time}
        minutesToFree={lastMessage.minutes_to_free ?? 15}
        formScore={zone.form_score}
        phase={lastMessage.sadla_phase ?? "Neutral"}
        classificationSource={lastMessage.classification_source}
        exerciseConfidence={lastMessage.detected_exercise_confidence}
        classificationScores={lastMessage.classification_scores}
        poseDebug={lastMessage.pose_debug}
      />
      <CameraControls zoneId={zoneId} setZoneId={setZoneId} onZoneUpdate={handleZoneUpdate} />
      <MlStatusCard status={mlStatus} />
      <RecentSessions sessions={sessions} />
    </main>
  );
}
