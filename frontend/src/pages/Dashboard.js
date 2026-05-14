import { jsx as _jsx, jsxs as _jsxs } from "react/jsx-runtime";
import { useEffect, useMemo, useState } from "react";
import LiveControls from "../components/LiveControls";
import ZoneCard from "../components/ZoneCard";
import { LiveWsClient } from "../services/wsClient";
const initialZone = {
    zone_id: "treadmill_zone_1",
    status: "Free",
    dwell_seconds: 0,
    current_exercise: null,
    rep_count: 0,
    form_score: 100,
};
export default function Dashboard() {
    const [lastMessage, setLastMessage] = useState({
        zone: initialZone,
        sadla_phase: "Neutral",
        supported_exercises: ["ResistanceBand", "PushUps", "Squats", "RunInPlace"],
    });
    const ws = useMemo(() => new LiveWsClient("ws://localhost:8000/ws/live", (message) => {
        setLastMessage(message);
    }), []);
    useEffect(() => {
        return () => {
            // browser auto-closes socket, explicit close not required for this simple MVP
        };
    }, []);
    const send = (payload) => {
        ws.send(payload);
    };
    return (_jsxs("main", { className: "layout", children: [_jsx("h1", { children: "GymNet Live Dashboard" }), _jsx("p", { children: "\u0421\u0446\u0435\u043D\u0430\u0440\u0438\u0438: ResistanceBand, PushUps, Squats, RunInPlace (treadmill ROI)" }), _jsx(ZoneCard, { zoneId: lastMessage.zone.zone_id, status: lastMessage.zone.status, dwellSeconds: lastMessage.zone.dwell_seconds, exercise: lastMessage.zone.current_exercise, reps: lastMessage.zone.rep_count, formScore: lastMessage.zone.form_score, phase: lastMessage.sadla_phase }), _jsx(LiveControls, { onSend: send })] }));
}
