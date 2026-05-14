import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useState } from "react";
const EXERCISES = ["ResistanceBand", "PushUps", "Squats", "RunInPlace"];
const PHASES = ["Neutral", "TransitionDown", "Bottom", "TransitionUp", "Standing"];
export default function LiveControls({ onSend }) {
    const [zoneId, setZoneId] = useState("treadmill_zone_1");
    const [isPresent, setIsPresent] = useState(true);
    const [exercise, setExercise] = useState("RunInPlace");
    const [phase, setPhase] = useState("Neutral");
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
    return (_jsxs("section", { className: "card", children: [_jsx("h2", { children: "Live Controls" }), _jsxs("label", { children: ["Zone ID", _jsx("input", { value: zoneId, onChange: (event) => setZoneId(event.target.value) })] }), _jsxs("label", { children: ["Presence", _jsx("input", { type: "checkbox", checked: isPresent, onChange: (event) => setIsPresent(event.target.checked) })] }), _jsxs("label", { children: ["Exercise", _jsx("select", { value: exercise, onChange: (event) => setExercise(event.target.value), children: EXERCISES.map((item) => (_jsx("option", { children: item }, item))) })] }), _jsxs("label", { children: ["SADLA phase", _jsx("select", { value: phase, onChange: (event) => setPhase(event.target.value), children: PHASES.map((item) => (_jsx("option", { children: item }, item))) })] }), _jsxs("label", { children: ["Form penalty", _jsx("input", { type: "number", min: 0, max: 100, value: penalty, onChange: (event) => setPenalty(Number(event.target.value)) })] }), _jsx("button", { onClick: send, children: "\u041E\u0442\u043F\u0440\u0430\u0432\u0438\u0442\u044C \u0441\u043E\u0431\u044B\u0442\u0438\u0435" })] }));
}
