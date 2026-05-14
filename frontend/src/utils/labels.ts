const STATUS_LABELS: Record<string, string> = {
  Free: "Свободно",
  Busy: "Занято",
  Crowded: "Перегружено",
};

const EXERCISE_LABELS: Record<string, string> = {
  ResistanceBand: "Упражнение с резиной",
  PushUps: "Отжимания",
  Squats: "Приседания",
  RunInPlace: "Бег на месте (зона дорожки)",
};

const PHASE_LABELS: Record<string, string> = {
  Neutral: "Нейтральная",
  TransitionDown: "Переход вниз",
  Bottom: "Нижняя точка",
  TransitionUp: "Переход вверх",
  Standing: "Исходное положение",
};

export function statusLabel(value: string): string {
  return STATUS_LABELS[value] ?? value;
}

export function exerciseLabel(value: string | null): string {
  if (!value) {
    return "—";
  }
  return EXERCISE_LABELS[value] ?? value;
}

export function phaseLabel(value: string): string {
  return PHASE_LABELS[value] ?? value;
}
