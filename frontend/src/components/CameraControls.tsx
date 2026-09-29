import { useEffect, useRef, useState } from "react";

import { apiPath, wsLiveIngestUrl } from "../config/runtime";
import type { PoseIngestResponse } from "../services/ingestTypes";
import { LiveIngestWsClient } from "../services/liveIngestWs";
import { createPose, type MediaPipePose, type Results } from "../utils/mediapipePose";
import {
  DEFAULT_ROI,
  drawPoseOverlay,
  syncCanvasToVideo,
  type OverlayFrame,
  type OverlayLayers,
} from "../utils/poseOverlay";

type CameraControlsProps = {
  zoneId: string;
  setZoneId: (value: string) => void;
  onZoneUpdate: (response: PoseIngestResponse) => void;
  onCameraStop?: () => void;
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

const INGEST_MIN_INTERVAL_MS = 500;
const INGEST_TIMEOUT_BACKOFF_MS = 3_000;
const INGEST_HTTP_TIMEOUT_MS = 28_000;
/** Фоновая вкладка: rAF почти не тикает — дёргаем processFrame по таймеру. */
const HIDDEN_TAB_FRAME_MS = 500;
const WATCHDOG_MS = 2_000;

const RECOVER_DEBOUNCE_MS = 5_000;

export default function CameraControls({
  zoneId,
  setZoneId,
  onZoneUpdate,
  onCameraStop,
}: CameraControlsProps) {
  const videoRef = useRef<HTMLVideoElement | null>(null);
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const overlayFrameRef = useRef<OverlayFrame>({ landmarks: [], roi: DEFAULT_ROI, ingest: null });
  const resizeObserverRef = useRef<ResizeObserver | null>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const poseRef = useRef<MediaPipePose | null>(null);
  const rafRef = useRef<number | null>(null);
  const processingRef = useRef(false);
  const lastSentRef = useRef(0);
  const ingestBackoffUntilRef = useRef(0);
  const ingestWsRef = useRef<LiveIngestWsClient | null>(null);
  const ingestSessionRef = useRef(0);
  const zoneIdRef = useRef(zoneId);
  const cameraStartedAtRef = useRef(0);
  const lastFrameAtRef = useRef(0);
  const cameraEnabledRef = useRef(false);
  const selectedDeviceIdRef = useRef("");
  const recoverInFlightRef = useRef(false);
  const mountedRef = useRef(true);
  const overlayRedrawTimerRef = useRef<number | null>(null);

  const [enabled, setEnabled] = useState(false);
  const [status, setStatus] = useState("Камера выключена");
  const [debugLog, setDebugLog] = useState<string[]>([]);
  const [devices, setDevices] = useState<MediaDeviceInfo[]>([]);
  const [selectedDeviceId, setSelectedDeviceId] = useState("");
  const [overlayLayers, setOverlayLayers] = useState<OverlayLayers>({
    roi: true,
    skeleton: true,
    angles: true,
    scores: true,
  });

  const deferredRedraw = () => {
    if (overlayRedrawTimerRef.current !== null) {
      window.clearTimeout(overlayRedrawTimerRef.current);
    }
    overlayRedrawTimerRef.current = window.setTimeout(redrawOverlay, 0);
  };

  const redrawOverlay = () => {
    const video = videoRef.current;
    const canvas = canvasRef.current;
    if (!video || !canvas) return;
    syncCanvasToVideo(canvas, video);
    const ctx = canvas.getContext("2d");
    if (!ctx) return;
    drawPoseOverlay(ctx, canvas.width, canvas.height, overlayFrameRef.current, overlayLayers);
  };

  const bindStreamTracks = (stream: MediaStream) => {
    for (const track of stream.getVideoTracks()) {
      track.onended = () => {
        if (!cameraEnabledRef.current) return;
        pushDebug("Видеотрек ended — восстанавливаем поток");
        void recoverCameraPipeline("track-ended");
      };
      track.onmute = () => {
        if (!cameraEnabledRef.current) return;
        pushDebug("Видеотрек mute — пробуем play()");
        void videoRef.current?.play().catch(() => undefined);
      };
    }
  };

  const applyIngestResponse = (event: PoseIngestResponse) => {
    overlayFrameRef.current = {
      ...overlayFrameRef.current,
      ingest: event,
    };
    redrawOverlay();
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
  };

  const submitIngestHttpFallback = (ingestPayload: {
    zone_id: string;
    roi: typeof DEFAULT_ROI;
    landmarks: { name: string; x: number; y: number }[];
  }) => {
    const controller = new AbortController();
    const fetchTimeout = window.setTimeout(() => controller.abort(), INGEST_HTTP_TIMEOUT_MS);
    void fetch(apiPath("/api/live/ingest"), {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(ingestPayload),
      signal: controller.signal,
    })
      .then(async (response) => {
        if (!response.ok) {
          const detail = await response.text().catch(() => "");
          pushDebug(`Ingest HTTP ${response.status}: ${detail.slice(0, 80)}`);
          return;
        }
        const event = (await response.json()) as PoseIngestResponse;
        if (mountedRef.current) {
          applyIngestResponse(event);
        }
      })
      .catch((error: unknown) => {
        const isAbort =
          (error instanceof DOMException && error.name === "AbortError") ||
          (error instanceof Error && error.name === "AbortError");
        pushDebug(isAbort ? "Ingest HTTP таймаут (fallback)" : `Ingest HTTP: ${extractErrorMessage(error)}`);
      })
      .finally(() => window.clearTimeout(fetchTimeout));
  };

  const recoverCameraPipeline = async (reason: string) => {
    if (!cameraEnabledRef.current || recoverInFlightRef.current) {
      return;
    }
    if (Date.now() - cameraStartedAtRef.current < RECOVER_DEBOUNCE_MS) {
      return;
    }
    recoverInFlightRef.current = true;
    try {
      pushDebug(`Восстановление (${reason})`);
      ingestBackoffUntilRef.current = 0;
      processingRef.current = false;

      const video = videoRef.current;
      const track = streamRef.current?.getVideoTracks()[0];
      if (!video || !poseRef.current) {
        return;
      }

      if (!track || track.readyState === "ended") {
        await restartCameraStream();
        return;
      }

      try {
        await video.play();
      } catch {
        // ignore
      }
      if (video.readyState < 2) {
        await waitVideoReady(video).catch(() => undefined);
      }
      setStatus("Камера: возобновление после паузы вкладки/потока");
      scheduleNextFrame();
    } finally {
      recoverInFlightRef.current = false;
    }
  };

  const restartCameraStream = async () => {
    const video = videoRef.current;
    if (!video || !cameraEnabledRef.current) {
      return;
    }
    streamRef.current?.getTracks().forEach((t) => t.stop());
    const stream = await navigator.mediaDevices.getUserMedia({
      video: {
        width: { ideal: 1280 },
        height: { ideal: 720 },
        ...(selectedDeviceIdRef.current
          ? { deviceId: { exact: selectedDeviceIdRef.current } }
          : {}),
      },
      audio: false,
    });
    streamRef.current = stream;
    bindStreamTracks(stream);
    video.srcObject = stream;
    await waitVideoReady(video);
    await video.play().catch(() => undefined);
    scheduleNextFrame();
    pushDebug("Поток камеры переподключён");
  };

  const resetCameraSessionRefs = () => {
    ingestSessionRef.current += 1;
    lastSentRef.current = 0;
    ingestBackoffUntilRef.current = 0;
    lastFrameAtRef.current = 0;
  };

  const resetBackendTracking = async (id: string) => {
    await fetch(apiPath(`/api/live/reset-tracking?zone_id=${encodeURIComponent(id)}`), {
      method: "POST",
    }).catch(() => undefined);
  };

  const stopCamera = (resetStatus = true) => {
    void resetBackendTracking(zoneIdRef.current);
    onCameraStop?.();
    ingestWsRef.current?.close();
    ingestWsRef.current = null;
    resetCameraSessionRefs();
    cameraEnabledRef.current = false;
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
    resizeObserverRef.current?.disconnect();
    resizeObserverRef.current = null;
    if (overlayRedrawTimerRef.current !== null) {
      window.clearTimeout(overlayRedrawTimerRef.current);
      overlayRedrawTimerRef.current = null;
    }
    overlayFrameRef.current = { landmarks: [], roi: DEFAULT_ROI, ingest: null };
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

  const onResults = (results: Results) => {
    lastFrameAtRef.current = Date.now();
    const landmarks = results.poseLandmarks ?? [];
    overlayFrameRef.current = {
      landmarks: landmarks.map((lm) => ({ x: lm.x, y: lm.y, visibility: lm.visibility })),
      roi: DEFAULT_ROI,
      ingest: overlayFrameRef.current.ingest,
    };
    redrawOverlay();

    const now = Date.now();
    if (now < ingestBackoffUntilRef.current) {
      scheduleNextFrame();
      return;
    }
    if (now - lastSentRef.current < INGEST_MIN_INTERVAL_MS) {
      scheduleNextFrame();
      return;
    }
    lastSentRef.current = now;

    const ingestPayload = {
      zone_id: zoneIdRef.current,
      roi: DEFAULT_ROI,
      landmarks: landmarks.map((lm, idx) => ({
        name: LANDMARK_NAMES[idx] ?? `point_${idx}`,
        x: lm.x,
        y: lm.y,
      })),
    };

    const ws = ingestWsRef.current;
    if (ws) {
      ws.submit(ingestPayload);
    }
    scheduleNextFrame();
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
    lastFrameAtRef.current = Date.now();
    if (processingRef.current) {
      scheduleNextFrame();
      return;
    }

    processingRef.current = true;
    try {
      await poseRef.current.send({ image: videoRef.current });
    } catch (error) {
      const details = extractErrorMessage(error);
      pushDebug(`Ошибка в pose.send(): ${details}`);
      setStatus(`Ошибка кадра — пробуем восстановить…`);
      void recoverCameraPipeline("pose-send");
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
      bindStreamTracks(stream);
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
      pose.onResults(onResults);
      poseRef.current = pose;

      resetCameraSessionRefs();
      await resetBackendTracking(zoneId);

      const session = ingestSessionRef.current;
      ingestWsRef.current?.close();
      ingestWsRef.current = new LiveIngestWsClient(wsLiveIngestUrl(), {
        onOpen: () => {
          pushDebug("ingest WebSocket подключён");
          scheduleNextFrame();
        },
        onError: (msg) => {
          if (msg === "busy") {
            return;
          }
          pushDebug(`ingest WS: ${msg}`);
          if (msg === "timeout") {
            ingestBackoffUntilRef.current = Date.now() + INGEST_TIMEOUT_BACKOFF_MS;
          }
          if (mountedRef.current) {
            setStatus(
              msg === "timeout"
                ? "Ingest timeout — снижаю частоту кадров…"
                : `ingest WS: ${msg}`,
            );
          }
        },
        onResponse: (event) => {
          if (session !== ingestSessionRef.current || !mountedRef.current) {
            return;
          }
          pushDebug(
            `ingest OK: present=${event.is_present} roi=${event.in_roi} rej=${event.activity_rejected ?? "—"}`,
          );
          applyIngestResponse(event);
        },
      });

      cameraEnabledRef.current = true;
      cameraStartedAtRef.current = Date.now();
      setEnabled(true);
      lastFrameAtRef.current = Date.now();
      setStatus("Камера включена — встаньте в зелёную ROI");
      pushDebug("Камера активна, жду WebSocket ingest");
      await loadVideoDevices();
      resizeObserverRef.current?.disconnect();
      resizeObserverRef.current = new ResizeObserver(() => redrawOverlay());
      if (videoRef.current) {
        resizeObserverRef.current.observe(videoRef.current);
      }
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
    selectedDeviceIdRef.current = selectedDeviceId;
    zoneIdRef.current = zoneId;
  }, [selectedDeviceId, zoneId]);

  useEffect(() => {
    redrawOverlay();
  }, [overlayLayers]);

  useEffect(() => {
    if (!enabled) {
      return;
    }

    const onVisible = () => {
      if (document.visibilityState === "visible") {
        void recoverCameraPipeline("visibility");
      }
    };
    const onFocus = () => {
      void recoverCameraPipeline("focus");
    };

    document.addEventListener("visibilitychange", onVisible);
    window.addEventListener("focus", onFocus);
    window.addEventListener("pageshow", onFocus);

    const hiddenTick = window.setInterval(() => {
      if (!cameraEnabledRef.current || !document.hidden) {
        return;
      }
      void processFrame();
    }, HIDDEN_TAB_FRAME_MS);

    const watchdog = window.setInterval(() => {
      if (!cameraEnabledRef.current) {
        return;
      }
      const stalled = Date.now() - lastFrameAtRef.current > WATCHDOG_MS * 3;
      if (stalled) {
        void recoverCameraPipeline("watchdog-stall");
      }
    }, WATCHDOG_MS);

    return () => {
      document.removeEventListener("visibilitychange", onVisible);
      window.removeEventListener("focus", onFocus);
      window.removeEventListener("pageshow", onFocus);
      window.clearInterval(hiddenTick);
      window.clearInterval(watchdog);
    };
  }, [enabled]);

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
      mountedRef.current = false;
      window.removeEventListener("error", onWindowError);
      window.removeEventListener("unhandledrejection", onUnhandledRejection);
      stopCamera();
    };
  }, []);

  return (
    <section className="card">
      <h2>Камера</h2>
      <p className="hint">Зона обновляется по WebSocket ingest (кадры не блокируют MediaPipe).</p>
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
      <div className="overlay-toggles">
        <label>
          <input
            type="checkbox"
            checked={overlayLayers.roi}
            onChange={(e) => {
              setOverlayLayers((prev) => ({ ...prev, roi: e.target.checked }));
              deferredRedraw();
            }}
          />
          Рабочая зона (ROI)
        </label>
        <label>
          <input
            type="checkbox"
            checked={overlayLayers.skeleton}
            onChange={(e) => {
              setOverlayLayers((prev) => ({ ...prev, skeleton: e.target.checked }));
              deferredRedraw();
            }}
          />
          Скелет и корпус
        </label>
        <label>
          <input
            type="checkbox"
            checked={overlayLayers.angles}
            onChange={(e) => {
              setOverlayLayers((prev) => ({ ...prev, angles: e.target.checked }));
              deferredRedraw();
            }}
          />
          Углы сгиба
        </label>
        <label>
          <input
            type="checkbox"
            checked={overlayLayers.scores}
            onChange={(e) => {
              setOverlayLayers((prev) => ({ ...prev, scores: e.target.checked }));
              deferredRedraw();
            }}
          />
          Оценки ML / эвристика
        </label>
      </div>
      <p className="hint">
        Зелёная рамка ROI — зона учёта; точки нос/бёдра — попадание в ROI. Цвет скелета — выбранное упражнение.
        Голубые дуги — локти, оранжевые — колена.
      </p>
      {debugLog.length > 0 && (
        <details>
          <summary>Логи камеры</summary>
          <pre>{debugLog.join("\n")}</pre>
        </details>
      )}
      <div className="camera-stack">
        <video ref={videoRef} className="camera-preview" playsInline muted autoPlay />
        <canvas ref={canvasRef} className="camera-overlay" />
      </div>
    </section>
  );
}
