import { useState } from "react";

import type { LiveUpdatePayload } from "../services/wsClient";
import { exerciseLabel, phaseLabel } from "../utils/labels";

type LiveControlsProps = {
  onSend: (payload: LiveUpdatePayload) => void;
};

const EXERCISES = ["ResistanceBand", "PushUps", "Squats", "RunInPlace"] as const;
const PHASES = ["Neutral", "TransitionDown", "Bottom", "TransitionUp", "Standing"] as const;

export default function LiveControls({ onSend }: LiveControlsProps) {
  const [zoneId, setZoneId] = useState("treadmill_zone_1");
  const [isPresent, setIsPresent] = useState(true);
  const [exercise, setExercise] = useState<(typeof EXERCISES)[number]>("RunInPlace");
  const [phase, setPhase] = useState<(typeof PHASES)[number]>("Neutral");
  const [penalty, setPenalty] = useState(0);

  const send = () => {
    onSend({
      zone_id: zoneId,
      is_present: isPresent,
      exercise,
      phase,
      form_penalty: penalty,
    });
  };

  return (
    <section className="card">
      <h2>Управление потоком</h2>
      <label>
        Идентификатор зоны
        <input value={zoneId} onChange={(event) => setZoneId(event.target.value)} />
      </label>
      <label>
        Присутствие в зоне
        <input type="checkbox" checked={isPresent} onChange={(event) => setIsPresent(event.target.checked)} />
      </label>
      <label>
        Упражнение
        <select value={exercise} onChange={(event) => setExercise(event.target.value as (typeof EXERCISES)[number])}>
          {EXERCISES.map((item) => (
            <option key={item} value={item}>
              {exerciseLabel(item)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Фаза SADLA
        <select value={phase} onChange={(event) => setPhase(event.target.value as (typeof PHASES)[number])}>
          {PHASES.map((item) => (
            <option key={item} value={item}>
              {phaseLabel(item)}
            </option>
          ))}
        </select>
      </label>
      <label>
        Штраф за технику
        <input
          type="number"
          min={0}
          max={100}
          value={penalty}
          onChange={(event) => setPenalty(Number(event.target.value))}
        />
      </label>
      <button onClick={send}>Отправить событие</button>
    </section>
  );
}
