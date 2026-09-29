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
  const runsSuccess = Number(autotrain.runs_success ?? autotrain.runs ?? 0);
  const runsFailed = Number(autotrain.runs_failed ?? 0);

  return (
    <section className="card">
      <h2>ML: автообучение</h2>
      <p>Live-образцов для дообучения: {status.live_train_samples}</p>
      <p>Новых образцов до retrain: {pendingTrain}</p>
      <p>Успешных retrain: {runsSuccess}</p>
      <p>Неудачных retrain: {runsFailed}</p>
      <p>Последний результат: {lastResult}</p>
      {lastResult === "failed" && status.autotrain_last_error ? (
        <p className="hint">
          Ошибка retrain: {status.autotrain_last_error}
          <br />
          Защита откатила веса: новая модель хуже на synthetic-тесте. Live-классификация в
          камере не пострадала, если «Модель доступна: да».
        </p>
      ) : null}
      <p>Модель доступна: {status.model_exists ? "да" : "нет"}</p>
      <p>
        Классификация live:{" "}
        {status.live_classification === "ml"
          ? "ML (CNN-ResBiGRU)"
          : status.live_classification === "heuristic"
            ? "эвристики"
            : "—"}
      </p>
      {status.live_classification !== "ml" && status.ml_unavailable_reason ? (
        <p className="hint">Почему не ML: {status.ml_unavailable_reason}</p>
      ) : null}
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
      {autotrain.last_retrain_at ? (
        <p className="hint">Последний успешный retrain: {String(autotrain.last_retrain_at)}</p>
      ) : null}
    </section>
  );
}
