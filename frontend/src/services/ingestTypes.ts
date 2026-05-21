export type ZoneSnapshot = {
  zone_id: string;
  status: "Free" | "Busy" | "Crowded" | string;
  dwell_seconds: number;
  current_exercise: string | null;
  exercise_seconds: number;
  rep_count: number;
  rep_tempo_seconds?: number | null;
  total_exercise_seconds: number;
  total_rep_count: number;
  total_rep_tempo_seconds?: number | null;
  tracks_rep_and_time?: boolean;
  form_score: number;
};

export type PoseIngestResponse = {
  zone_id: string;
  is_present: boolean;
  in_roi?: boolean;
  activity_rejected?: string | null;
  exercise: string;
  phase: string;
  form_penalty: number;
  minutes_to_free?: number;
  sadla_phase?: string;
  zone?: ZoneSnapshot;
  classification_source?: string | null;
  detected_exercise_confidence?: number | null;
  classification_scores?: Record<string, number> | null;
  body_orientation?: string | null;
  pose_debug?: Record<string, number | null> | null;
  supported_exercises?: string[];
};
