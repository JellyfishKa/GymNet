import { useEffect, useRef, useState } from "react";
import { Pose, type Results } from "@mediapipe/pose";

import { apiPath } from "../config/runtime";
import type { LiveUpdatePayload } from "../services/wsClient";

type CameraControlsProps = {
  onLiveEvent: (payload: LiveUpdatePayload) => void;
};

const LANDMARK_NAMES = [
  "nose",
  "left_eye_inner",
  "left_eye",
  "left_eye_outer",
  "right_eye_inner",
  "right_eye",
  "right_eye_outer",
  "left_ear",
  "right_ear",
  "mouth_left",
  "mouth_right",
  "left_shoulder",
  "right_shoulder",
  "left_elbow",
  "right_elbow",
  "left_wrist",
  "right_wrist",
  "left_pinky",
  "right_pinky",
  "left_index",
  "right_index",
  "left_thumb",
  "right_thumb",
  "left_hip",
  "right_hip",
  "left_knee",
  "right_knee",
  "left_ankle",
  "right_ankle",
  "left_heel",
  "right_heel",
  "left_foot_index",
  "right_foot_index",
] as const;

export default function CameraControls({ onLiveEvent }: CameraControlsProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const poseRef = useRef<Pose | null>(null);
  const rafRef = useRef<number | null>(null);
  const processingRef = useRef(false);
  const lastSentRef = useRef(0);

  const [enabled, setEnabled] = useState(false);
  const [zoneId, setZoneId] = useState("treadmill_zone_1");
  const [status, setStatus] = useState("Камера выключена");

  const stopCamera = (resetStatus = true) => {
    setEnabled(false);
    if (resetStatus) {
      setStatus("Камера выключена");
    }

    if (rafRef.current !== null) {
      window.cancelAnimationFrame(rafRef.current);
      rafRef.current = null;
    }
    if (poseRef.current) {
      void poseRef.current.close();
      poseRef.current = null;
    }
    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop());
      streamRef.current = null;
    }
    if (videoRef.current) {
      videoRef.current.srcObject = null;
    }
  };

  const waitVideoReady = (video: HTMLVideoElement): Promise<void> => {
    if (video.readyState >= 2) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      const timeout = window.setTimeout(() => {
        reject(new Error("Камера не успела подготовить видеопоток"));
      }, 5000);

      const onReady = () => {
        window.clearTimeout(timeout);
        video.removeEventListener("loadeddata", onReady);
        resolve();
      };

      video.addEventListener("loadeddata", onReady);
    });
  };

  const onResults = async (results: Results) => {
    const now = Date.now();
    if (now - lastSentRef.current < 200) {
      return;
    }
    lastSentRef.current = now;

    const landmarks = results.poseLandmarks ?? [];
    const ingestPayload = {
      zone_id: zoneId,
      treadmill_zone: true,
      roi: { x_min: 0.25, y_min: 0.2, x_max: 0.75, y_max: 0.95 },
      landmarks: landmarks.map((lm, idx) => ({
        name: LANDMARK_NAMES[idx] ?? `point_${idx}`,
        x: lm.x,
        y: lm.y,
      })),
    };

    try {
      const response = await fetch(apiPath("/api/live/ingest"), {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(ingestPayload),
      });
      if (!response.ok) {
        return;
      }
      const event = (await response.json()) as LiveUpdatePayload;
      onLiveEvent(event);
      setStatus(event.is_present ? "Камера активна: человек в зоне" : "Камера активна: зона свободна");
    } catch {
      setStatus("Ошибка отправки данных камеры");
    }
  };

  const processFrame = async () => {
    if (!videoRef.current || !poseRef.current) {
      return;
    }
    if (processingRef.current) {
      rafRef.current = window.requestAnimationFrame(() => {
        void processFrame();
      });
      return;
    }

    processingRef.current = true;
    try {
      await poseRef.current.send({ image: videoRef.current });
    } finally {
      processingRef.current = false;
      rafRef.current = window.requestAnimationFrame(() => {
        void processFrame();
      });
    }
  };

  const startCamera = async () => {
    if (enabled) {
      return;
    }
    try {
      setStatus("Запрашиваю доступ к камере...");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: { width: { ideal: 1280 }, height: { ideal: 720 } },
        audio: false,
      });
      streamRef.current = stream;
      if (!videoRef.current) {
        throw new Error("Видеоэлемент не найден");
      }
      videoRef.current.srcObject = stream;
      await waitVideoReady(videoRef.current);
      try {
        await videoRef.current.play();
      } catch {
        // Для некоторых браузеров play может вернуть reject,
        // но поток при этом уже доступен и кадры читаются.
      }

      const pose = new Pose({
        locateFile: (file) => `https://cdn.jsdelivr.net/npm/@mediapipe/pose/${file}`,
      });
      pose.setOptions({
        modelComplexity: 1,
        smoothLandmarks: true,
        minDetectionConfidence: 0.5,
        minTrackingConfidence: 0.5,
      });
      pose.onResults((results) => {
        void onResults(results);
      });
      poseRef.current = pose;

      setEnabled(true);
      setStatus("Камера включена");
      rafRef.current = window.requestAnimationFrame(() => {
        void processFrame();
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : "Неизвестная ошибка камеры";
      setStatus(`Ошибка камеры: ${message}`);
      stopCamera(false);
    }
  };

  useEffect(() => {
    return () => {
      stopCamera();
    };
  }, []);

  return (
    <section className="card">
      <h2>Камера</h2>
      <label>
        Идентификатор зоны камеры
        <input value={zoneId} onChange={(event) => setZoneId(event.target.value)} />
      </label>
      <div className="camera-actions">
        <button onClick={startCamera} disabled={enabled}>
          Включить камеру
        </button>
        <button onClick={() => stopCamera()} disabled={!enabled}>
          Выключить камеру
        </button>
      </div>
      <p>{status}</p>
      <video ref={videoRef} className="camera-preview" playsInline muted autoPlay />
    </section>
  );
}
