import type { MlStatusResponse } from "../services/apiClient";

type MlStatusCardProps = {
  status: MlStatusResponse | null;
};

export default function MlStatusCard({ status }: MlStatusCardProps) {
  if (!status) {
    return (
      <section className="card">
        <h2>ML: автообучение</h2>
        <p>Статус недоступен.</p>
      </section>
    );
  }

  const autotrain = status.autotrain ?? {};
  const pendingTrain = Number(autotrain.pending_train_samples ?? 0);
  const lastResult = String(autotrain.last_result ?? "ожидание");
  const runs = Number(autotrain.runs ?? 0);

  return (
    <section className="card">
      <h2>ML: автообучение</h2>
      <p>Live-образцов для дообучения: {status.live_train_samples}</p>
      <p>Новых образцов до retrain: {pendingTrain}</p>
      <p>Запусков retrain: {runs}</p>
      <p>Последний результат: {lastResult}</p>
      <p>Модель доступна: {status.model_exists ? "да" : "нет"}</p>
      <p>
        Метрика synthetic macro-F1:{" "}
        {status.synthetic_macro_f1 !== null && status.synthetic_macro_f1 !== undefined
          ? status.synthetic_macro_f1.toFixed(3)
          : "—"}
      </p>
      <p>
        Метрика real macro-F1:{" "}
        {status.real_macro_f1 !== null && status.real_macro_f1 !== undefined
          ? status.real_macro_f1.toFixed(3)
          : "—"}
      </p>
      <p>Последняя оценка: {status.evaluated_at ?? "—"}</p>
    </section>
  );
}
