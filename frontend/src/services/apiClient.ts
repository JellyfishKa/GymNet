import { apiPath } from "../config/runtime";

export type RecentSession = {
  id: number;
  exercise: string;
  dwell_seconds: number;
  rep_count: number;
  form_score: number;
  created_at: string;
};

export type SessionResponse = {
  recent_sessions: RecentSession[];
};

export type MlStatusResponse = {
  autotrain: Record<string, unknown>;
  live_train_samples: number;
  model_exists: boolean;
  model_path: string;
  evaluated_at?: string | null;
  synthetic_macro_f1?: number | null;
  real_macro_f1?: number | null;
};

export async function fetchMlStatus(): Promise<MlStatusResponse> {
  const response = await fetch(apiPath("/api/ml/status"));
  if (!response.ok) {
    throw new Error(`Не удалось загрузить ML-статус: ${response.status}`);
  }
  return (await response.json()) as MlStatusResponse;
}

export async function fetchRecentSessions(zoneId: string): Promise<RecentSession[]> {
  const response = await fetch(apiPath(`/api/sessions/${zoneId}`));
  if (!response.ok) {
    throw new Error(`Не удалось загрузить сессии: ${response.status}`);
  }
  const payload = (await response.json()) as SessionResponse;
  return payload.recent_sessions ?? [];
}
