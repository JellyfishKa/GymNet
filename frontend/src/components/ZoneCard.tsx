import { type OccupancyForecast } from "../services/apiClient";
import { exerciseLabel, muscleGroupLabel, phaseLabel, statusLabel } from "../utils/labels";

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
  detectedExercise?: string | null;
  isPresent?: boolean;
  inRoi?: boolean;
  activityRejected?: string | null;
  classificationScores?: Record<string, number> | null;
  bodyOrientation?: string | null;
  poseDebug?: Record<string, number | null> | null;
  estimatedCalories?: number | null;
  muscleGroups?: string[] | null;
  occupancyForecast?: OccupancyForecast | null;
};

const ORIENTATION_LABELS: Record<string, string> = {
  frontal: "в лицо",
  left_profile: "боком (левый профиль)",
  right_profile: "боком (правый профиль)",
};

export default function ZoneCard(props: ZoneCardProps) {
  const displayExercise = props.exercise ?? props.detectedExercise ?? null;
  const isRepExercise = displayExercise != null && REP_EXERCISES.has(displayExercise);
  const confidenceText =
    props.exerciseConfidence != null ? `${(props.exerciseConfidence * 100).toFixed(0)}%` : "—";
  const sourceLabel =
    props.classificationSource === "ml"
      ? "ML"
      : props.classificationSource === "heuristic" || props.classificationSource === "heuristic_override"
        ? "эвристики"
        : props.classificationSource ?? "—";
  const presenceHint = (() => {
    if (props.isPresent) return null;
    if (props.inRoi && props.activityRejected === "warming_up") {
      return "В ROI — накопление кадров (~2 с), затем засчитаем занятость";
    }
    if (props.inRoi && props.activityRejected === "idle") {
      return "В ROI, но движение слабое — сделайте повторы отжиманий/приседаний";
    }
    if (props.inRoi && props.activityRejected === "passing") {
      return "В ROI, но проход мимо — остановитесь в зоне";
    }
    if (props.inRoi) return "В ROI — ожидаем активность";
    return "Человек вне рамки ROI — встаньте в зелёную зону на видео";
  })();

  return (
    <section className="card">
      <h2>Зона: {props.zoneId}</h2>
      <p>Статус: {statusLabel(props.status)}</p>
      {presenceHint && <p className="banner-warn">{presenceHint}</p>}
      <p>
        Упражнение: {exerciseLabel(displayExercise)}
        {!props.exercise && props.detectedExercise ? " (по кадру, зона ещё не занята)" : ""}
      </p>
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
      {props.estimatedCalories != null && (
        <p className="calorie-display">~{props.estimatedCalories} ккал за сессию</p>
      )}
      {props.muscleGroups && props.muscleGroups.length > 0 && (
        <div className="muscle-badge-row">
          {props.muscleGroups.map((m) => (
            <span key={m} className="muscle-badge">{muscleGroupLabel(m)}</span>
          ))}
        </div>
      )}
      {props.occupancyForecast && (
        <p className={`occupancy-level ${props.occupancyForecast.busyness_level}`}>
          Загруженность зала:{" "}
          {props.occupancyForecast.busyness_level === "high"
            ? "Высокая"
            : props.occupancyForecast.busyness_level === "medium"
              ? "Средняя"
              : "Низкая"}
          {" "}({Math.round(props.occupancyForecast.wait_probability * 100)}% ждать &gt;5 мин)
        </p>
      )}
      <p>Прогноз до освобождения: {props.minutesToFree} мин</p>
      <p>Оценка техники: {props.formScore}</p>
      <p>Фаза SADLA: {phaseLabel(props.phase)}</p>
      {(props.classificationScores || props.poseDebug) && (
        <details>
          <summary>Отладка распознавания (для настройки)</summary>
          {props.bodyOrientation && (
            <p>Ракурс: {ORIENTATION_LABELS[props.bodyOrientation] ?? props.bodyOrientation}</p>
          )}
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
                <li>Вертикаль корпуса (приседания): {props.poseDebug.torso_vertical_span}</li>
              )}
              {props.poseDebug.torso_horizontal_span != null && (
                <li>Горизонталь корпуса (отжимания): {props.poseDebug.torso_horizontal_span}</li>
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
