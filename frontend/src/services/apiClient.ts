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

export async function fetchRecentSessions(zoneId: string): Promise<RecentSession[]> {
  const response = await fetch(apiPath(`/api/sessions/${zoneId}`));
  if (!response.ok) {
    throw new Error(`Не удалось загрузить сессии: ${response.status}`);
  }
  const payload = (await response.json()) as SessionResponse;
  return payload.recent_sessions ?? [];
}
