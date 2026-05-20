import { exerciseLabel, phaseLabel, statusLabel } from "../utils/labels";

type ZoneCardProps = {
  zoneId: string;
  status: string;
  dwellSeconds: number;
  exercise: string | null;
  exerciseSeconds: number;
  reps: number;
  totalExerciseSeconds: number;
  totalReps: number;
  minutesToFree: number;
  formScore: number;
  phase: string;
};

export default function ZoneCard(props: ZoneCardProps) {
  return (
    <section className="card">
      <h2>Зона: {props.zoneId}</h2>
      <p>Статус: {statusLabel(props.status)}</p>
      <p>Упражнение: {exerciseLabel(props.exercise)}</p>
      <p>Время в зоне: {props.dwellSeconds} сек</p>
      <p>Время текущего упражнения: {props.exerciseSeconds} сек</p>
      <p>Повторения текущего упражнения: {props.reps}</p>
      <p>Суммарное время упражнений в сессии: {props.totalExerciseSeconds} сек</p>
      <p>Суммарные повторения в сессии: {props.totalReps}</p>
      <p>Прогноз до освобождения: {props.minutesToFree} мин</p>
      <p>Оценка техники: {props.formScore}</p>
      <p>Фаза SADLA: {phaseLabel(props.phase)}</p>
    </section>
  );
}
