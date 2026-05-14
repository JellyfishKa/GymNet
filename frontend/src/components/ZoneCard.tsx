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
      <p>Статус: {props.status}</p>
      <p>Упражнение: {props.exercise ?? "—"}</p>
      <p>Dwell Time: {props.dwellSeconds} сек</p>
      <p>Повторения: {props.reps}</p>
      <p>Form Score: {props.formScore}</p>
      <p>SADLA фаза: {props.phase}</p>
    </section>
  );
}
