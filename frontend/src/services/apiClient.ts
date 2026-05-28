import { apiPath } from "../config/runtime";

async function fetchWithTimeout(url: string, timeoutMs = 8000): Promise<Response> {
  const controller = new AbortController();
  const id = window.setTimeout(() => controller.abort(), timeoutMs);
  try {
    return await fetch(url, { signal: controller.signal });
  } finally {
    window.clearTimeout(id);
  }
}

export type RecentSession = {
  id: number;
  exercise: string;
  dwell_seconds: number;
  exercise_seconds: number;
  rep_count: number;
  form_score: number;
  created_at: string;
};

export type SessionResponse = {
  recent_sessions: RecentSession[];
};

export type AutotrainStatus = {
  last_result?: string;
  last_retrain_at?: string | null;
  runs?: number;
  runs_success?: number;
  runs_failed?: number;
  pending_train_samples?: number;
  pending_sessions?: number;
  last_error?: string;
  last_details?: string;
};

export type MlStatusResponse = {
  autotrain: AutotrainStatus;
  autotrain_last_error?: string | null;
  live_train_samples: number;
  live_classification?: "ml" | "heuristic";
  ml_unavailable_reason?: string | null;
  model_exists: boolean;
  evaluated_at?: string | null;
  synthetic_macro_f1?: number | null;
  real_macro_f1?: number | null;
};

export async function fetchMlStatus(): Promise<MlStatusResponse> {
  const response = await fetchWithTimeout(apiPath("/api/ml/status"));
  if (!response.ok) {
    throw new Error(`Не удалось загрузить ML-статус: ${response.status}`);
  }
  return (await response.json()) as MlStatusResponse;
}

export async function fetchRecentSessions(zoneId: string): Promise<RecentSession[]> {
  const response = await fetchWithTimeout(apiPath(`/api/sessions/${zoneId}`));
  if (!response.ok) {
    throw new Error(`Не удалось загрузить сессии: ${response.status}`);
  }
  const payload = (await response.json()) as SessionResponse;
  return payload.recent_sessions ?? [];
}

export type OccupancyForecast = {
  zone_id: string;
  hour: number;
  day_of_week: number;
  peak_factor: number;
  wait_probability: number;
  wait_minutes: number;
  busyness_level: "low" | "medium" | "high";
};

export async function fetchOccupancyForecast(zoneId: string): Promise<OccupancyForecast> {
  const response = await fetchWithTimeout(
    apiPath(`/api/ml/occupancy-forecast?zone_id=${encodeURIComponent(zoneId)}`)
  );
  if (!response.ok) {
    throw new Error(`Не удалось загрузить прогноз загруженности: ${response.status}`);
  }
  return (await response.json()) as OccupancyForecast;
}
