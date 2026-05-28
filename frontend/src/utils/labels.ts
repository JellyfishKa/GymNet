const STATUS_LABELS: Record<string, string> = {
  Free: "Свободно",
  Busy: "Занято",
  Crowded: "Перегружено",
};

const EXERCISE_LABELS: Record<string, string> = {
  PushUps: "Отжимания",
  Squats: "Приседания",
  RunInPlace: "Бег на месте",
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

const MUSCLE_GROUP_LABELS: Record<string, string> = {
  chest: "Грудь",
  triceps: "Трицепсы",
  shoulders: "Плечи",
  quadriceps: "Квадрицепсы",
  glutes: "Ягодицы",
  hamstrings: "Бицепсы бёдер",
  cardio: "Кардио",
  calves: "Икры",
  core: "Корпус",
};

export function muscleGroupLabel(value: string): string {
  return MUSCLE_GROUP_LABELS[value] ?? value;
}
