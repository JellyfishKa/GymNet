import { useEffect, useRef, useState } from "react";

import { apiPath } from "../config/runtime";
import type { PoseIngestResponse } from "../services/ingestTypes";
import { createPose, type MediaPipePose, type Results } from "../utils/mediapipePose";

type CameraControlsProps = {
  zoneId: string;
  setZoneId: (value: string) => void;
  onZoneUpdate: (response: PoseIngestResponse) => void;
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

const DEFAULT_ROI = { x_min: 0.25, y_min: 0.2, x_max: 0.75, y_max: 0.95 };

export default function CameraControls({ zoneId, setZoneId, onZoneUpdate }: CameraControlsProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const poseRef = useRef<MediaPipePose | null>(null);
  const rafRef = useRef<number | null>(null);
  const processingRef = useRef(false);
  const lastSentRef = useRef(0);
  const sendInFlightRef = useRef(false);

  const [enabled, setEnabled] = useState(false);
  const [status, setStatus] = useState("Камера выключена");
  const [debugLog, setDebugLog] = useState<string[]>([]);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");

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

  const pushDebug = (entry: string) => {
    const line = `[${new Date().toLocaleTimeString("ru-RU")}] ${entry}`;
    // eslint-disable-next-line no-console
    console.info("[CameraControls]", line);
    setDebugLog((prev) => [...prev.slice(-7), line]);
  };

  const extractErrorMessage = (error: unknown): string => {
    if (error instanceof Error) {
      return `${error.message}${error.stack ? `\n${error.stack}` : ""}`;
    }
    return String(error);
  };

  const loadVideoDevices = async () => {
    const all = await navigator.mediaDevices.enumerateDevices();
    const videoInputs = all.filter((d) => d.kind === "videoinput");
    setDevices(videoInputs);
    if (!selectedDeviceId && videoInputs.length > 0) {
      setSelectedDeviceId(videoInputs[0].deviceId);
    }
  };

  const waitVideoReady = (video: HTMLVideoElement): Promise<void> => {
    if (video.readyState >= 2) {
      return Promise.resolve();
    }
    return new Promise((resolve, reject) => {
      let timeoutId: number | null = null;

      const cleanup = () => {
        if (timeoutId !== null) {
          window.clearTimeout(timeoutId);
        }
        video.removeEventListener("loadeddata", onReady);
      };

      timeoutId = window.setTimeout(() => {
        cleanup();
        reject(new Error("Камера не успела подготовить видеопоток"));
      }, 5000);

      const onReady = () => {
        cleanup();
        resolve();
      };

      video.addEventListener("loadeddata", onReady);
    });
  };

  const onResults = async (results: Results) => {
    const now = Date.now();
    if (now - lastSentRef.current < 200 || sendInFlightRef.current) {
      scheduleNextFrame();
      return;
    }
    lastSentRef.current = now;
    sendInFlightRef.current = true;

    const landmarks = results.poseLandmarks ?? [];
    const ingestPayload = {
      zone_id: zoneId,
      roi: DEFAULT_ROI,
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
        scheduleNextFrame();
        return;
      }
      const event = (await response.json()) as PoseIngestResponse;
      onZoneUpdate(event);
      const label = event.zone?.current_exercise ?? event.exercise;
      if (event.is_present) {
        setStatus(`В зоне: ${label ?? "—"} (${event.classification_source ?? "—"})`);
      } else if (event.in_roi && event.activity_rejected === "idle") {
        setStatus("В кадре, но без упражнения (стоит) — не засчитываем");
      } else if (event.in_roi && event.activity_rejected === "passing") {
        setStatus("Проходит мимо — не засчитываем");
      } else if (event.in_roi && event.activity_rejected === "warming_up") {
        setStatus("В кадре — ожидаем движение упражнения");
      } else if (event.in_roi) {
        setStatus("В кадре — не засчитываем");
      } else {
        setStatus("Камера активна: зона свободна");
      }
    } catch {
      setStatus("Ошибка отправки данных камеры");
    } finally {
      sendInFlightRef.current = false;
      scheduleNextFrame();
    }
  };

  const scheduleNextFrame = () => {
    if (streamRef.current && poseRef.current) {
      rafRef.current = window.requestAnimationFrame(() => {
        void processFrame();
      });
    }
  };

  const processFrame = async () => {
    if (!videoRef.current || !poseRef.current) {
      return;
    }
    if (processingRef.current || sendInFlightRef.current) {
      scheduleNextFrame();
      return;
    }

    processingRef.current = true;
    try {
      await poseRef.current.send({ image: videoRef.current });
    } catch (error) {
      const details = extractErrorMessage(error);
      pushDebug(`Ошибка в pose.send(): ${details}`);
      setStatus(`Ошибка обработки кадра: ${details}`);
      stopCamera(false);
      return;
    } finally {
      processingRef.current = false;
    }
  };

  const startCamera = async () => {
    if (enabled) {
      return;
    }
    try {
      pushDebug("Старт камеры: запрашиваю getUserMedia");
      setStatus("Запрашиваю доступ к камере...");
      const stream = await navigator.mediaDevices.getUserMedia({
        video: {
          width: { ideal: 1280 },
          height: { ideal: 720 },
          ...(selectedDeviceId ? { deviceId: { exact: selectedDeviceId } } : {}),
        },
        audio: false,
      });
      pushDebug(`getUserMedia OK, треков: ${stream.getTracks().length}`);
      streamRef.current = stream;
      if (!videoRef.current) {
        throw new Error("Видеоэлемент не найден");
      }
      videoRef.current.srcObject = stream;
      pushDebug("Ожидаю готовность видеопотока");
      await waitVideoReady(videoRef.current);
      try {
        await videoRef.current.play();
        pushDebug("video.play() выполнен");
      } catch {
        pushDebug("video.play() rejected, продолжаю");
      }

      pushDebug("Создаю MediaPipe Pose");
      const pose = await createPose();
      pushDebug("Pose создан, применяю setOptions");
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
      setStatus("Камера включена — настройте кадр так, чтобы человек был в рамке ROI");
      pushDebug("Камера активна, запускаю цикл кадров");
      await loadVideoDevices();
      scheduleNextFrame();
    } catch (error) {
      const message = extractErrorMessage(error);
      // eslint-disable-next-line no-console
      console.error("[CameraControls] startCamera error", error);
      pushDebug(`Падение startCamera(): ${message}`);
      setStatus(`Ошибка камеры: ${message}`);
      stopCamera(false);
    }
  };

  useEffect(() => {
    const initDevices = async () => {
      try {
        await loadVideoDevices();
      } catch {
        // Список устройств может быть пуст до первого getUserMedia.
      }
    };
    void initDevices();

    const onWindowError = (event: ErrorEvent) => {
      pushDebug(`window.onerror: ${event.message}`);
    };
    const onUnhandledRejection = (event: PromiseRejectionEvent) => {
      pushDebug(`unhandledrejection: ${extractErrorMessage(event.reason)}`);
    };
    window.addEventListener("error", onWindowError);
    window.addEventListener("unhandledrejection", onUnhandledRejection);

    return () => {
      window.removeEventListener("error", onWindowError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
      stopCamera();
    };
  }, []);

  return (
    <section className="card">
      <h2>Камера</h2>
      <p className="hint">Данные зоны обновляются только через ingest (без ручного WebSocket).</p>
      <label>
        Идентификатор зоны камеры
        <input value={zoneId} onChange={(event) => setZoneId(event.target.value)} />
      </label>
      <label>
        Устройство камеры
        <select value={selectedDeviceId} onChange={(event) => setSelectedDeviceId(event.target.value)} disabled={enabled}>
          {devices.length === 0 ? (
            <option value="">Камера не найдена</option>
          ) : (
            devices.map((device, idx) => (
              <option key={device.deviceId} value={device.deviceId}>
                {device.label || `Камера ${idx + 1}`}
              </option>
            ))
          )}
        </select>
      </label>
      <div className="camera-actions">
        <button onClick={startCamera} disabled={enabled}>
          Включить камеру
        </button>
        <button onClick={() => stopCamera()} disabled={!enabled}>
          Выключить камеру
        </button>
        <button onClick={() => void loadVideoDevices()} disabled={enabled}>
          Обновить список
        </button>
      </div>
      <p>{status}</p>
      {debugLog.length > 0 && (
        <details>
          <summary>Логи камеры</summary>
          <pre>{debugLog.join("\n")}</pre>
        </details>
      )}
      <video ref={videoRef} className="camera-preview" playsInline muted autoPlay />
    </section>
  );
}
