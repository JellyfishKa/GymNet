import type { PoseIngestResponse } from "../services/ingestTypes";
import { exerciseLabel } from "./labels";

export type NormalizedLandmark = { x: number; y: number; visibility?: number };
export type RoiRect = { x_min: number; y_min: number; x_max: number; y_max: number };

export const DEFAULT_ROI: RoiRect = { x_min: 0.25, y_min: 0.2, x_max: 0.75, y_max: 0.95 };

export const PRESENCE_KEYPOINTS = ["nose", "left_hip", "right_hip"] as const;

/** Индексы MediaPipe Pose (совпадают с CameraControls). */
export const POSE_CONNECTIONS: [number, number][] = [
  [11, 12],
  [11, 13],
  [13, 15],
  [12, 14],
  [14, 16],
  [11, 23],
  [12, 24],
  [23, 24],
  [23, 25],
  [25, 27],
  [24, 26],
  [26, 28],
];

const ANGLE_CHAINS: { label: string; indices: [number, number, number]; color: string }[] = [
  { label: "локоть L", indices: [11, 13, 15], color: "#22d3ee" },
  { label: "локоть R", indices: [12, 14, 16], color: "#22d3ee" },
  { label: "колено L", indices: [23, 25, 27], color: "#fb923c" },
  { label: "колено R", indices: [24, 26, 28], color: "#fb923c" },
];

const PRESENCE_INDICES: Record<string, number> = {
  nose: 0,
  left_hip: 23,
  right_hip: 24,
};

const EXERCISE_COLORS: Record<string, string> = {
  PushUps: "#22d3ee",
  Squats: "#fb923c",
  RunInPlace: "#a78bfa",
};

export type OverlayLayers = {
  roi: boolean;
  skeleton: boolean;
  angles: boolean;
  scores: boolean;
};

export type OverlayFrame = {
  landmarks: NormalizedLandmark[];
  roi: RoiRect;
  ingest: PoseIngestResponse | null;
};

function toCanvas(
  lm: NormalizedLandmark,
  width: number,
  height: number,
): { x: number; y: number } {
  return { x: lm.x * width, y: lm.y * height };
}

export function jointAngleDeg(a: NormalizedLandmark, b: NormalizedLandmark, c: NormalizedLandmark): number {
  const ba = { x: a.x - b.x, y: a.y - b.y };
  const bc = { x: c.x - b.x, y: c.y - b.y };
  const dot = ba.x * bc.x + ba.y * bc.y;
  const normBa = Math.hypot(ba.x, ba.y) || 1e-6;
  const normBc = Math.hypot(bc.x, bc.y) || 1e-6;
  const cos = Math.max(-1, Math.min(1, dot / (normBa * normBc)));
  return (Math.acos(cos) * 180) / Math.PI;
}

function drawAngleArc(
  ctx: CanvasRenderingContext2D,
  a: NormalizedLandmark,
  b: NormalizedLandmark,
  c: NormalizedLandmark,
  width: number,
  height: number,
  color: string,
  label: string,
) {
  const pa = toCanvas(a, width, height);
  const pb = toCanvas(b, width, height);
  const pc = toCanvas(c, width, height);
  const angleA = Math.atan2(pa.y - pb.y, pa.x - pb.x);
  const angleC = Math.atan2(pc.y - pb.y, pc.x - pb.x);
  const radius = 22;
  const deg = jointAngleDeg(a, b, c);
  ctx.save();
  ctx.strokeStyle = color;
  ctx.fillStyle = color;
  ctx.lineWidth = 2;
  ctx.beginPath();
  ctx.arc(pb.x, pb.y, radius, angleA, angleC, false);
  ctx.stroke();
  const mid = (angleA + angleC) / 2;
  ctx.font = "11px Arial, sans-serif";
  ctx.fillText(`${label} ${deg.toFixed(0)}°`, pb.x + Math.cos(mid) * (radius + 10) - 18, pb.y + Math.sin(mid) * (radius + 10));
  ctx.restore();
}

function drawScoreBars(
  ctx: CanvasRenderingContext2D,
  x: number,
  y: number,
  title: string,
  scores: Record<string, number> | null | undefined,
  accent: string,
  winner: string | null,
) {
  if (!scores) return;
  const entries = Object.entries(scores);
  const maxVal = Math.max(...entries.map(([, v]) => v), 0.01);
  ctx.save();
  ctx.fillStyle = "rgba(15, 23, 42, 0.82)";
  ctx.fillRect(x, y, 168, 14 + entries.length * 16);
  ctx.fillStyle = "#e2e8f0";
  ctx.font = "bold 11px Arial, sans-serif";
  ctx.fillText(title, x + 6, y + 12);
  entries.forEach(([name, value], idx) => {
    const rowY = y + 18 + idx * 16;
    const w = (value / maxVal) * 100;
    ctx.fillStyle = name === winner ? accent : "#475569";
    ctx.fillRect(x + 6, rowY, 100, 8);
    ctx.fillStyle = name === winner ? accent : "#64748b";
    ctx.fillRect(x + 6, rowY, w, 8);
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "10px Arial, sans-serif";
    ctx.fillText(`${exerciseLabel(name)} ${value.toFixed(2)}`, x + 112, rowY + 7);
  });
  ctx.restore();
}

function dominantExercise(ingest: PoseIngestResponse | null): string | null {
  return ingest?.exercise ?? null;
}

export function drawPoseOverlay(
  ctx: CanvasRenderingContext2D,
  width: number,
  height: number,
  frame: OverlayFrame,
  layers: OverlayLayers,
) {
  ctx.clearRect(0, 0, width, height);
  const { landmarks, roi, ingest } = frame;
  if (landmarks.length === 0) return;

  const winner = dominantExercise(ingest);
  const accent = (winner && EXERCISE_COLORS[winner]) || "#94a3b8";

  if (layers.roi) {
    const x0 = roi.x_min * width;
    const y0 = roi.y_min * height;
    const rw = (roi.x_max - roi.x_min) * width;
    const rh = (roi.y_max - roi.y_min) * height;
    let stroke = "#64748b";
    if (ingest?.is_present) stroke = "#22c55e";
    else if (ingest?.in_roi) stroke = "#f59e0b";
    ctx.save();
    ctx.strokeStyle = stroke;
    ctx.lineWidth = 2;
    ctx.setLineDash([8, 6]);
    ctx.strokeRect(x0, y0, rw, rh);
    ctx.setLineDash([]);
    ctx.fillStyle = "rgba(15, 23, 42, 0.55)";
    ctx.font = "12px Arial, sans-serif";
    const roiLabel = ingest?.is_present
      ? "ROI: в зоне, активность"
      : ingest?.in_roi
        ? `ROI: в кадре (${ingest.activity_rejected ?? "ожидание"})`
        : "ROI: вне зоны";
    ctx.fillText(roiLabel, x0 + 6, y0 + 16);
    const hits = (ingest?.roi_debug?.presence_hits as string[] | undefined) ?? [];
    PRESENCE_KEYPOINTS.forEach((name, idx) => {
      const lmIdx = PRESENCE_INDICES[name];
      if (lmIdx === undefined || !landmarks[lmIdx]) return;
      const p = toCanvas(landmarks[lmIdx], width, height);
      const inside = hits.includes(name);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 7, 0, Math.PI * 2);
      ctx.fillStyle = inside ? "#22c55e" : "#ef4444";
      ctx.fill();
      ctx.strokeStyle = "#0f172a";
      ctx.lineWidth = 1;
      ctx.stroke();
      ctx.fillStyle = "#e2e8f0";
      ctx.fillText(name === "nose" ? "нос" : name.includes("left") ? "бедро L" : "бедро R", p.x + 8, p.y - 4 - idx * 2);
    });
    ctx.restore();
  }

  if (layers.skeleton) {
    ctx.save();
    ctx.lineWidth = 3;
    for (const [i, j] of POSE_CONNECTIONS) {
      const a = landmarks[i];
      const b = landmarks[j];
      if (!a || !b) continue;
      const pa = toCanvas(a, width, height);
      const pb = toCanvas(b, width, height);
      let color = "#94a3b8";
      if (winner === "PushUps" && ([11, 12, 13, 14, 15, 16].includes(i) || [11, 12, 13, 14, 15, 16].includes(j))) {
        color = EXERCISE_COLORS.PushUps;
      }
      if (winner === "Squats" && ([23, 24, 25, 26, 27, 28].includes(i) || [23, 24, 25, 26, 27, 28].includes(j))) {
        color = EXERCISE_COLORS.Squats;
      }
      if (winner === "RunInPlace" && ([23, 24, 25, 26, 27, 28].includes(i) || [23, 24, 25, 26, 27, 28].includes(j))) {
        color = EXERCISE_COLORS.RunInPlace;
      }
      ctx.strokeStyle = color;
      ctx.beginPath();
      ctx.moveTo(pa.x, pa.y);
      ctx.lineTo(pb.x, pb.y);
      ctx.stroke();
    }
    landmarks.forEach((lm, idx) => {
      const p = toCanvas(lm, width, height);
      ctx.beginPath();
      ctx.arc(p.x, p.y, 4, 0, Math.PI * 2);
      ctx.fillStyle = accent;
      ctx.fill();
    });
    const dbg = ingest?.pose_debug;
    if (dbg) {
      const ls = landmarks[11];
      const lh = landmarks[23];
      const rs = landmarks[12];
      const rh = landmarks[24];
      if (ls && lh && rs && rh) {
        ctx.setLineDash([4, 4]);
        ctx.strokeStyle = "#22d3ee";
        ctx.lineWidth = 1.5;
        const pl = toCanvas(ls, width, height);
        const ph = toCanvas(lh, width, height);
        ctx.beginPath();
        ctx.moveTo(pl.x, pl.y);
        ctx.lineTo(ph.x, ph.y);
        ctx.stroke();
        const pr = toCanvas(rs, width, height);
        const prh = toCanvas(rh, width, height);
        ctx.beginPath();
        ctx.moveTo(pr.x, pr.y);
        ctx.lineTo(prh.x, prh.y);
        ctx.stroke();
        ctx.setLineDash([]);
        ctx.fillStyle = "#22d3ee";
        ctx.font = "10px Arial, sans-serif";
        const hSpan = dbg.torso_horizontal_span;
        const vSpan = dbg.torso_vertical_span;
        if (hSpan != null) ctx.fillText(`корпус гориз. ${hSpan.toFixed(2)}`, pl.x + 4, pl.y - 6);
        if (vSpan != null) ctx.fillText(`корпус верт. ${vSpan.toFixed(2)}`, pr.x + 4, pr.y + 14);
      }
    }
    ctx.restore();
  }

  if (layers.angles) {
    for (const chain of ANGLE_CHAINS) {
      const [ia, ib, ic] = chain.indices;
      const a = landmarks[ia];
      const b = landmarks[ib];
      const c = landmarks[ic];
      if (!a || !b || !c) continue;
      drawAngleArc(ctx, a, b, c, width, height, chain.color, chain.label);
    }
    const dbg = ingest?.pose_debug;
    if (dbg) {
      ctx.save();
      ctx.fillStyle = "rgba(15, 23, 42, 0.75)";
      ctx.fillRect(8, height - 72, width - 16, 64);
      ctx.fillStyle = "#cbd5e1";
      ctx.font = "10px Arial, sans-serif";
      const lines = [
        dbg.elbow_range_window != null ? `амплитуда локтя (окно): ${dbg.elbow_range_window.toFixed(0)}°` : null,
        dbg.knee_range_window != null ? `амплитуда колена (окно): ${dbg.knee_range_window.toFixed(0)}°` : null,
        dbg.ankle_y_std_window != null ? `шаг стоп (σy): ${dbg.ankle_y_std_window.toFixed(3)}` : null,
        ingest?.body_orientation ? `ракурс: ${ingest.body_orientation}` : null,
      ].filter(Boolean) as string[];
      lines.forEach((line, i) => ctx.fillText(line, 12, height - 56 + i * 14));
      ctx.restore();
    }
  }

  if (layers.scores && ingest) {
    drawScoreBars(ctx, 8, 8, "Эвристика", ingest.heuristic_scores, "#4ade80", winner);
    drawScoreBars(ctx, 8, 92, "ML", ingest.ml_probs, "#60a5fa", winner);
    ctx.save();
    ctx.fillStyle = "rgba(15, 23, 42, 0.82)";
    ctx.fillRect(width - 178, 8, 170, 52);
    ctx.fillStyle = "#e2e8f0";
    ctx.font = "bold 11px Arial, sans-serif";
    ctx.fillText(`Итог: ${exerciseLabel(ingest.exercise)}`, width - 172, 22);
    ctx.font="10px Arial, sans-serif";
    ctx.fillText(`источник: ${ingest.classification_source ?? "—"}`, width - 172, 36);
    if (ingest.detected_exercise_confidence != null) {
      ctx.fillText(`уверенность: ${(ingest.detected_exercise_confidence * 100).toFixed(0)}%`, width - 172, 50);
    }
    ctx.restore();
  }
}

export function syncCanvasToVideo(canvas: HTMLCanvasElement, video: HTMLVideoElement) {
  const w = video.clientWidth;
  const h = video.clientHeight;
  if (w <= 0 || h <= 0) return;
  if (canvas.width !== w || canvas.height !== h) {
    canvas.width = w;
    canvas.height = h;
  }
}
