import type { RecentSession } from "../services/apiClient";
import { exerciseLabel } from "../utils/labels";

const REP_EXERCISES = new Set(["PushUps", "Squats"]);

type RecentSessionsProps = {
  sessions: RecentSession[];
};

export default function RecentSessions({ sessions }: RecentSessionsProps) {
  return (
    <section className="card">
      <h2>История сессий зоны</h2>
      <p className="hint">
        Сессии сохраняются автоматически при выходе человека из зоны (ingest). Здесь только просмотр
        истории, ручное сохранение не требуется.
      </p>
      {sessions.length === 0 ? (
        <p>Пока нет завершённых сессий в БД.</p>
      ) : (
        <table>
          <thead>
            <tr>
              <th>Упражнение</th>
              <th>Время в зоне (сек)</th>
              <th>Время упражнений (сек)</th>
              <th>Повторы</th>
              <th>Оценка техники</th>
            </tr>
          </thead>
          <tbody>
            {sessions.map((session) => (
              <tr key={session.id}>
                <td>{exerciseLabel(session.exercise)}</td>
                <td>{session.dwell_seconds}</td>
                <td>
                  {REP_EXERCISES.has(session.exercise)
                    ? session.exercise_seconds ?? 0
                    : "—"}
                </td>
                <td>{REP_EXERCISES.has(session.exercise) ? session.rep_count : "—"}</td>
                <td>{session.form_score.toFixed(1)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      )}
    </section>
  );
}
