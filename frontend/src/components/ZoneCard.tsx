import { exerciseLabel, phaseLabel, statusLabel } from "../utils/labels";

type ZoneCardProps = {
  zoneId: string;
  status: string;
  dwellSeconds: number;
  exercise: string | null;
  reps: number;
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
      <p>Повторения: {props.reps}</p>
      <p>Оценка техники: {props.formScore}</p>
      <p>Фаза SADLA: {phaseLabel(props.phase)}</p>
    </section>
  );
}
