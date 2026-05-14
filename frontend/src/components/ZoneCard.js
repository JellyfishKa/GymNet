import { jsxs as _jsxs } from "react/jsx-runtime";
export default function ZoneCard(props) {
    return (_jsxs("section", { className: "card", children: [_jsxs("h2", { children: ["\u0417\u043E\u043D\u0430: ", props.zoneId] }), _jsxs("p", { children: ["\u0421\u0442\u0430\u0442\u0443\u0441: ", props.status] }), _jsxs("p", { children: ["\u0423\u043F\u0440\u0430\u0436\u043D\u0435\u043D\u0438\u0435: ", props.exercise ?? "—"] }), _jsxs("p", { children: ["Dwell Time: ", props.dwellSeconds, " \u0441\u0435\u043A"] }), _jsxs("p", { children: ["\u041F\u043E\u0432\u0442\u043E\u0440\u0435\u043D\u0438\u044F: ", props.reps] }), _jsxs("p", { children: ["Form Score: ", props.formScore] }), _jsxs("p", { children: ["SADLA \u0444\u0430\u0437\u0430: ", props.phase] })] }));
}
