import { exerciseLabel, phaseLabel, statusLabel } from "../utils/labels";

const REP_EXERCISES = new Set(["PushUps", "Squats"]);

type ZoneCardProps = {
  zoneId: string;
  status: string;
  dwellSeconds: number;
  exercise: string | null;
  exerciseSeconds: number;
  reps: number;
  repTempoSeconds?: number | null;
  totalExerciseSeconds: number;
  totalReps: number;
  totalRepTempoSeconds?: number | null;
  tracksRepAndTime?: boolean;
  minutesToFree: number;
  formScore: number;
  phase: string;
  classificationSource?: string | null;
  exerciseConfidence?: number | null;
  classificationScores?: Record<string, number> | null;
  poseDebug?: Record<string, number | null> | null;
};

export default function ZoneCard(props: ZoneCardProps) {
  const isRepExercise = props.exercise != null && REP_EXERCISES.has(props.exercise);
  const confidenceText =
    props.exerciseConfidence != null ? `${(props.exerciseConfidence * 100).toFixed(0)}%` : "—";
  const sourceLabel =
    props.classificationSource === "ml"
      ? "ML"
      : props.classificationSource === "heuristic"
        ? "эвристики"
        : "—";

  return (
    <section className="card">
      <h2>Зона: {props.zoneId}</h2>
      <p>Статус: {statusLabel(props.status)}</p>
      <p>Упражнение: {exerciseLabel(props.exercise)}</p>
      <p>
        Распознавание: {sourceLabel}
        {props.classificationSource ? ` (уверенность ${confidenceText})` : ""}
      </p>
      <p>Время в зоне: {props.dwellSeconds} сек</p>
      {isRepExercise ? (
        <>
          <p className="hint">
            Для отжиманий и приседаний учитываются и повторы, и время: у разных людей разный темп.
          </p>
          <p>Время текущего упражнения: {props.exerciseSeconds} сек</p>
          <p>Повторения текущего упражнения: {props.reps}</p>
          <p>
            Темп:{" "}
            {props.repTempoSeconds != null ? `${props.repTempoSeconds} сек/повтор` : "— (ждём первый повтор)"}
          </p>
          <p>Суммарное время упражнений в сессии: {props.totalExerciseSeconds} сек</p>
          <p>Суммарные повторения в сессии: {props.totalReps}</p>
          <p>
            Средний темп за сессию:{" "}
            {props.totalRepTempoSeconds != null
              ? `${props.totalRepTempoSeconds} сек/повтор`
              : "—"}
          </p>
        </>
      ) : (
        <>
          <p>Время текущего упражнения: {props.exerciseSeconds} сек</p>
          <p>Повторения текущего упражнения: {props.reps}</p>
          <p>Суммарное время упражнений в сессии: {props.totalExerciseSeconds} сек</p>
          <p>Суммарные повторения в сессии: {props.totalReps}</p>
        </>
      )}
      <p>Прогноз до освобождения: {props.minutesToFree} мин</p>
      <p>Оценка техники: {props.formScore}</p>
      <p>Фаза SADLA: {phaseLabel(props.phase)}</p>
      {(props.classificationScores || props.poseDebug) && (
        <details>
          <summary>Отладка распознавания (для настройки)</summary>
          {props.classificationScores && (
            <p>
              Оценки классов:{" "}
              {Object.entries(props.classificationScores)
                .map(([k, v]) => `${k}=${v.toFixed(2)}`)
                .join(", ")}
            </p>
          )}
          {props.poseDebug && (
            <ul className="debug-list">
              {props.poseDebug.torso_vertical_span != null && (
                <li>
                  Вертикаль корпуса (меньше → отжимания): {props.poseDebug.torso_vertical_span}
                </li>
              )}
              {props.poseDebug.elbow_angle != null && (
                <li>Угол локтя: {props.poseDebug.elbow_angle}°</li>
              )}
              {props.poseDebug.elbow_drop != null && (
                <li>Опуск локтя (отжимания): {props.poseDebug.elbow_drop}</li>
              )}
              {props.poseDebug.knee_angle != null && (
                <li>Угол колена: {props.poseDebug.knee_angle}°</li>
              )}
            </ul>
          )}
        </details>
      )}
    </section>
  );
}
