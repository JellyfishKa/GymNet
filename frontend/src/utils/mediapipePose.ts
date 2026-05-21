import type { Results } from "@mediapipe/pose";

const POSE_PKG_VERSION = "0.5.1675469404";

export type { Results };

export type MediaPipePose = {
  setOptions: (options: Record<string, unknown>) => void;
  onResults: (callback: (results: Results) => void) => void;
  send: (input: { image: HTMLVideoElement }) => Promise<void>;
  close: () => Promise<void>;
};

declare global {
  interface Window {
    Pose?: new (config?: { locateFile?: (file: string) => string }) => MediaPipePose;
  }
}

let loadPromise: Promise<void> | null = null;

/** Загружает UMD-сборку MediaPipe Pose (глобальный window.Pose). */
export function loadMediaPipePose(): Promise<void> {
  if (typeof window.Pose === "function") {
    return Promise.resolve();
  }
  if (loadPromise) {
    return loadPromise;
  }

  loadPromise = new Promise((resolve, reject) => {
    const script = document.createElement("script");
    script.src = `https://cdn.jsdelivr.net/npm/@mediapipe/pose@${POSE_PKG_VERSION}/pose.js`;
    script.crossOrigin = "anonymous";
    script.onload = () => {
      if (typeof window.Pose !== "function") {
        loadPromise = null;
        reject(new Error("MediaPipe Pose не зарегистрировал window.Pose"));
        return;
      }
      resolve();
    };
    script.onerror = () => {
      loadPromise = null;
      reject(new Error("Не удалось загрузить MediaPipe Pose с CDN"));
    };
    document.head.appendChild(script);
  });

  return loadPromise;
}

export async function createPose(): Promise<MediaPipePose> {
  await loadMediaPipePose();
  const PoseCtor = window.Pose;
  if (typeof PoseCtor !== "function") {
    throw new Error("MediaPipe Pose недоступен");
  }
  try {
    return new PoseCtor({
      locateFile: (file) =>
        `https://cdn.jsdelivr.net/npm/@mediapipe/pose@${POSE_PKG_VERSION}/${file}`,
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : String(error);
    throw new Error(`createPose() failed: ${message}`);
  }
}
