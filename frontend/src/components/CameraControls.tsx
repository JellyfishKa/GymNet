import { useEffect, useRef, useState } from "react";

import { apiPath } from "../config/runtime";
import { createPose, type MediaPipePose, type Results } from "../utils/mediapipePose";
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
  const poseRef = useRef<MediaPipePose | null>(null);
  const rafRef = useRef<number | null>(null);
  const processingRef = useRef(false);
  const lastSentRef = useRef(0);

  const [enabled, setEnabled] = useState(false);
  const [zoneId, setZoneId] = useState("treadmill_zone_1");
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
    } catch (error) {
      const details = extractErrorMessage(error);
      pushDebug(`Ошибка в pose.send(): ${details}`);
      setStatus(`Ошибка обработки кадра: ${details}`);
      stopCamera(false);
      return;
    } finally {
      processingRef.current = false;
      if (streamRef.current && poseRef.current) {
        rafRef.current = window.requestAnimationFrame(() => {
          void processFrame();
        });
      }
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
        // Для некоторых браузеров play может вернуть reject,
        // но поток при этом уже доступен и кадры читаются.
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
      setStatus("Камера включена");
      pushDebug("Камера активна, запускаю цикл кадров");
      await loadVideoDevices();
      rafRef.current = window.requestAnimationFrame(() => {
        void processFrame();
      });
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
        // Игнорируем ошибки на этапе первичного чтения списка устройств.
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
