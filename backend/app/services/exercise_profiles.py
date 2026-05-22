"""
Профили упражнений: углы, полное выпрямление (lockout), фазы SADLA.

Пороги можно переопределить через env, например:
GYMNET_PUSHUP_STANDING_MIN_ANGLE=168
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Literal, Sequence, TypedDict

import numpy as np

BodyOrientation = Literal["frontal", "left_profile", "right_profile"]

from app.services.landmark_sequence import FEATURE_DIM, LANDMARK_NAMES, WINDOW_SIZE
from app.services.zone_locks import zone_lock

Point = tuple[float, float]
Landmarks = dict[str, Point]

_HIP_L = LANDMARK_NAMES.index("left_hip") * 3
_HIP_R = LANDMARK_NAMES.index("right_hip") * 3
_ANKLE_L = LANDMARK_NAMES.index("left_ankle") * 3
_ANKLE_R = LANDMARK_NAMES.index("right_ankle") * 3
_KNEE_L = LANDMARK_NAMES.index("left_knee") * 3
_KNEE_R = LANDMARK_NAMES.index("right_knee") * 3
_ELBOW_L = LANDMARK_NAMES.index("left_elbow") * 3
_ELBOW_R = LANDMARK_NAMES.index("right_elbow") * 3
_SHOULDER_L = LANDMARK_NAMES.index("left_shoulder") * 3
_SHOULDER_R = LANDMARK_NAMES.index("right_shoulder") * 3
_WRIST_L = LANDMARK_NAMES.index("left_wrist") * 3
_WRIST_R = LANDMARK_NAMES.index("right_wrist") * 3

_last_elbow_angle: dict[str, float] = {}
_last_knee_angle: dict[str, float] = {}


def _env_float(name: str, default: float) -> float:
    raw = os.environ.get(name)
    if raw is None:
        return default
    try:
        return float(raw)
    except ValueError:
        return default


@dataclass(frozen=True, slots=True)
class PushUpProfile:
    standing_min_angle: float = 168.0
    bottom_max_angle: float = 85.0
    transition_up_min: float = 155.0
    max_torso_span: float = 0.17
    min_elbow_range: float = 45.0
    bottom_min_elbow_drop: float = 0.07
    standing_min_arm_extension: float = 0.09
    standing_max_elbow_drop: float = 0.05


@dataclass(frozen=True, slots=True)
class SquatProfile:
    standing_min_angle: float = 168.0
    bottom_max_angle: float = 95.0
    transition_up_min: float = 140.0
    min_torso_span: float = 0.1
    min_knee_range: float = 40.0


@dataclass(frozen=True, slots=True)
class RunProfile:
    min_ankle_y_std: float = 0.014
    min_step_delta_y: float = 0.018
    min_torso_span: float = 0.11


def pushup_profile() -> PushUpProfile:
    return PushUpProfile(
        standing_min_angle=_env_float("GYMNET_PUSHUP_STANDING_MIN_ANGLE", 168.0),
        bottom_max_angle=_env_float("GYMNET_PUSHUP_BOTTOM_MAX_ANGLE", 85.0),
        transition_up_min=_env_float("GYMNET_PUSHUP_TRANSITION_UP_MIN", 155.0),
        max_torso_span=_env_float("GYMNET_PUSHUP_MAX_TORSO_SPAN", 0.17),
        min_elbow_range=_env_float("GYMNET_PUSHUP_MIN_ELBOW_RANGE", 45.0),
        bottom_min_elbow_drop=_env_float("GYMNET_PUSHUP_BOTTOM_MIN_ELBOW_DROP", 0.07),
        standing_min_arm_extension=_env_float("GYMNET_PUSHUP_STANDING_MIN_ARM_EXTENSION", 0.09),
        standing_max_elbow_drop=_env_float("GYMNET_PUSHUP_STANDING_MAX_ELBOW_DROP", 0.05),
    )


def squat_profile() -> SquatProfile:
    return SquatProfile(
        standing_min_angle=_env_float("GYMNET_SQUAT_STANDING_MIN_ANGLE", 168.0),
        bottom_max_angle=_env_float("GYMNET_SQUAT_BOTTOM_MAX_ANGLE", 95.0),
        transition_up_min=_env_float("GYMNET_SQUAT_TRANSITION_UP_MIN", 140.0),
        min_torso_span=_env_float("GYMNET_SQUAT_MIN_TORSO_SPAN", 0.1),
        min_knee_range=_env_float("GYMNET_SQUAT_MIN_KNEE_RANGE", 40.0),
    )


def run_profile() -> RunProfile:
    return RunProfile(
        min_ankle_y_std=_env_float("GYMNET_RUN_MIN_ANKLE_Y_STD", 0.014),
        min_step_delta_y=_env_float("GYMNET_RUN_MIN_STEP_DELTA_Y", 0.018),
        min_torso_span=_env_float("GYMNET_RUN_MIN_TORSO_SPAN", 0.11),
    )


def _angle(a: Point, b: Point, c: Point) -> float:
    import math

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    norm_ba = math.hypot(ba[0], ba[1]) or 1e-6
    norm_bc = math.hypot(bc[0], bc[1]) or 1e-6
    cos_value = max(-1.0, min(1.0, dot / (norm_ba * norm_bc)))
    return math.degrees(math.acos(cos_value))


def _pick(side: Landmarks, left: str, right: str) -> Point | None:
    return side.get(left) or side.get(right)


def _limb_angle(
    landmarks: Landmarks,
    *,
    a: str,
    b: str,
    c: str,
) -> float | None:
    triple = (landmarks.get(a), landmarks.get(b), landmarks.get(c))
    if not all(triple):
        return None
    return _angle(triple[0], triple[1], triple[2])


def _profile_shoulder_span_max() -> float:
    return _env_float("GYMNET_PROFILE_SHOULDER_SPAN_MAX", 0.10)


def detect_body_orientation(landmarks: Landmarks) -> BodyOrientation:
    """
    Фронт: плечи широко в кадре. Профиль: плечи «сложены» по X (человек боком).
    """
    ls = landmarks.get("left_shoulder")
    rs = landmarks.get("right_shoulder")
    lh = landmarks.get("left_hip")
    rh = landmarks.get("right_hip")
    if not ls or not rs:
        return "frontal"

    shoulder_span = abs(ls[0] - rs[0])
    hip_span = abs(lh[0] - rh[0]) if lh and rh else shoulder_span
    body_span = max(shoulder_span, hip_span)
    if body_span > _profile_shoulder_span_max():
        return "frontal"

    nose = landmarks.get("nose")
    mid_x = (ls[0] + rs[0]) / 2.0
    if nose is not None:
        if nose[0] <= mid_x - 0.015:
            return "left_profile"
        if nose[0] >= mid_x + 0.015:
            return "right_profile"

    if lh and rh:
        lk = landmarks.get("left_knee")
        rk = landmarks.get("right_knee")
        left_depth = abs(lh[0] - ls[0]) + (abs(lk[0] - lh[0]) if lk else 0.0)
        right_depth = abs(rh[0] - rs[0]) + (abs(rk[0] - rh[0]) if rk else 0.0)
        return "left_profile" if left_depth >= right_depth else "right_profile"
    return "left_profile"


def torso_span_per_side(landmarks: Landmarks) -> tuple[float, float]:
    """Вертикальный размах корпуса отдельно для левой и правой цепочки плечо–бедро."""
    left_s = landmarks.get("left_shoulder")
    left_h = landmarks.get("left_hip")
    right_s = landmarks.get("right_shoulder")
    right_h = landmarks.get("right_hip")
    left_span = abs(left_h[1] - left_s[1]) if left_s and left_h else 0.0
    right_span = abs(right_h[1] - right_s[1]) if right_s and right_h else 0.0
    return left_span, right_span


def torso_vertical_span(landmarks: Landmarks) -> float:
    """Для приседаний (в т.ч. боком): берём максимум по видимой стороне."""
    left_span, right_span = torso_span_per_side(landmarks)
    return max(left_span, right_span, 0.0)


def torso_horizontal_span(landmarks: Landmarks) -> float:
    """Для отжиманий (в т.ч. боком): берём минимум — корпус «горизонтален» с любой стороны."""
    left_span, right_span = torso_span_per_side(landmarks)
    spans = [s for s in (left_span, right_span) if s > 0]
    if not spans:
        return 0.5
    return min(spans)


def _merge_limb_angles(
    left: float | None,
    right: float | None,
    *,
    pick: Literal["min", "max", "avg"],
) -> float | None:
    values = [v for v in (left, right) if v is not None]
    if not values:
        return None
    if pick == "min":
        return float(min(values))
    if pick == "max":
        return float(max(values))
    return float(sum(values) / len(values))


def elbow_angle(landmarks: Landmarks, *, pick: Literal["min", "max", "avg"] = "avg") -> float | None:
    left = _limb_angle(
        landmarks, a="left_shoulder", b="left_elbow", c="left_wrist"
    )
    right = _limb_angle(
        landmarks, a="right_shoulder", b="right_elbow", c="right_wrist"
    )
    orientation = detect_body_orientation(landmarks)
    if orientation == "frontal":
        return _merge_limb_angles(left, right, pick="avg")
    return _merge_limb_angles(left, right, pick=pick)


def knee_angle(landmarks: Landmarks, *, pick: Literal["min", "max", "avg"] = "avg") -> float | None:
    left = _limb_angle(landmarks, a="left_hip", b="left_knee", c="left_ankle")
    right = _limb_angle(landmarks, a="right_hip", b="right_knee", c="right_ankle")
    orientation = detect_body_orientation(landmarks)
    if orientation == "frontal":
        return _merge_limb_angles(left, right, pick="avg")
    return _merge_limb_angles(left, right, pick=pick)


def _side_prefix(orientation: BodyOrientation) -> str:
    if orientation == "left_profile":
        return "left"
    if orientation == "right_profile":
        return "right"
    return "left"


def pushup_body_metrics(landmarks: Landmarks) -> tuple[float | None, float | None, float | None]:
    """(elbow_drop, arm_extension, elbow_angle) с учётом бокового ракурса."""
    orientation = detect_body_orientation(landmarks)

    def _side_metrics(prefix: str) -> tuple[float | None, float | None, float | None]:
        shoulder = landmarks.get(f"{prefix}_shoulder")
        elbow = landmarks.get(f"{prefix}_elbow")
        wrist = landmarks.get(f"{prefix}_wrist")
        if not shoulder or not elbow or not wrist:
            return None, None, None
        elbow_drop = elbow[1] - shoulder[1]
        arm_extension = wrist[1] - elbow[1]
        ang = _limb_angle(
            landmarks,
            a=f"{prefix}_shoulder",
            b=f"{prefix}_elbow",
            c=f"{prefix}_wrist",
        )
        return elbow_drop, arm_extension, ang

    left_m = _side_metrics("left")
    right_m = _side_metrics("right")

    if orientation == "frontal":
        shoulder_y = _avg_y(landmarks, ("left_shoulder", "right_shoulder"))
        elbow_y = _avg_y(landmarks, ("left_elbow", "right_elbow"))
        wrist_y = _avg_y(landmarks, ("left_wrist", "right_wrist"))
        if shoulder_y is None or elbow_y is None or wrist_y is None:
            return None, None, elbow_angle(landmarks, pick="avg")
        return (
            elbow_y - shoulder_y,
            wrist_y - elbow_y,
            elbow_angle(landmarks, pick="avg"),
        )

    preferred = _side_prefix(orientation)
    preferred_m = _side_metrics(preferred)
    if preferred_m[0] is not None:
        return preferred_m

    candidates = [m for m in (left_m, right_m) if m[0] is not None]
    if not candidates:
        return None, None, None
    return max(candidates, key=lambda item: item[0] or 0.0)


def _avg_y(landmarks: Landmarks, names: tuple[str, ...]) -> float | None:
    ys = [landmarks[name][1] for name in names if name in landmarks]
    if not ys:
        return None
    return float(sum(ys) / len(ys))


def ankle_motion_stats(landmarks: Landmarks) -> tuple[float, float]:
    ankles = [landmarks.get("left_ankle"), landmarks.get("right_ankle")]
    ys = [p[1] for p in ankles if p]
    if len(ys) < 2:
        return 0.0, 0.0
    return float(np.std(ys)), float(max(ys) - min(ys))


class MotionSignature(TypedDict):
    elbow_range: float | None
    knee_range: float | None
    ankle_y_std: float
    pushup_torso: float
    squat_torso: float


def motion_signature(
    landmarks: Landmarks,
    window: Sequence[Sequence[float]] | None,
) -> MotionSignature:
    """Сводка движения за окно: что доминирует — локти, колени или стопы."""
    elbow_metric: float | None = None
    knee_metric: float | None = None
    ankle_std, _ = ankle_motion_stats(landmarks)
    if window and len(window) >= 5:
        elbow_metric, knee_metric = _temporal_joint_angles(window)
        ys: list[float] = []
        for frame in window:
            if len(frame) != FEATURE_DIM:
                continue
            ys.append(float(frame[_ANKLE_L + 1]))
            ys.append(float(frame[_ANKLE_R + 1]))
        if len(ys) >= 4:
            ankle_std = max(ankle_std, float(np.std(ys)))
    return {
        "elbow_range": elbow_metric,
        "knee_range": knee_metric,
        "ankle_y_std": ankle_std,
        "pushup_torso": torso_horizontal_span(landmarks),
        "squat_torso": torso_vertical_span(landmarks),
    }


def _temporal_joint_angles(window: Sequence[Sequence[float]]) -> tuple[float | None, float | None]:
    elbow_vals: list[float] = []
    knee_vals: list[float] = []
    for frame in window:
        if len(frame) != FEATURE_DIM:
            continue
        lm: Landmarks = {}
        for i, name in enumerate(LANDMARK_NAMES):
            lm[name] = (float(frame[i * 3]), float(frame[i * 3 + 1]))
        e = elbow_angle(lm, pick="max")
        k = knee_angle(lm, pick="max")
        if e is not None:
            elbow_vals.append(e)
        if k is not None:
            knee_vals.append(k)
    elbow_range = (max(elbow_vals) - min(elbow_vals)) if len(elbow_vals) >= 2 else None
    knee_range = (max(knee_vals) - min(knee_vals)) if len(knee_vals) >= 2 else None
    elbow_max = max(elbow_vals) if elbow_vals else None
    knee_max = max(knee_vals) if knee_vals else None
    return (
        elbow_range if elbow_range is not None else elbow_max,
        knee_range if knee_range is not None else knee_max,
    )


def infer_pushup_phase(landmarks: Landmarks, zone_id: str) -> str:
    profile = pushup_profile()
    elbow_drop, arm_extension, angle = pushup_body_metrics(landmarks)
    if angle is None:
        angle = elbow_angle(landmarks, pick="max")
    metric = angle if angle is not None else 0.0
    with zone_lock(zone_id):
        prev = _last_elbow_angle.get(zone_id)
        _last_elbow_angle[zone_id] = metric

    full_extension = False
    if angle is not None and angle >= profile.standing_min_angle:
        full_extension = True
    elif (
        elbow_drop is not None
        and arm_extension is not None
        and elbow_drop <= profile.standing_max_elbow_drop
        and arm_extension >= profile.standing_min_arm_extension
    ):
        full_extension = True

    if full_extension:
        return "Standing"

    at_bottom = False
    if angle is not None and angle <= profile.bottom_max_angle:
        at_bottom = True
    elif (
        elbow_drop is not None
        and arm_extension is not None
        and elbow_drop >= profile.bottom_min_elbow_drop
        and arm_extension <= profile.standing_max_elbow_drop
    ):
        at_bottom = True

    if at_bottom:
        return "Bottom"

    if prev is not None and metric > prev + 2.0:
        return "TransitionUp"
    if prev is not None and metric < prev - 2.0:
        return "TransitionDown"
    if angle is not None and angle < profile.transition_up_min:
        return "TransitionDown"
    return "TransitionUp"


def infer_squat_phase(landmarks: Landmarks, zone_id: str) -> str:
    profile = squat_profile()
    angle = knee_angle(landmarks, pick="max")
    if angle is None:
        return "Neutral"

    with zone_lock(zone_id):
        prev = _last_knee_angle.get(zone_id)
        _last_knee_angle[zone_id] = angle

    if angle >= profile.standing_min_angle:
        return "Standing"
    bottom_angle = knee_angle(landmarks, pick="min")
    if bottom_angle is not None and bottom_angle <= profile.bottom_max_angle:
        return "Bottom"
    if angle <= profile.bottom_max_angle:
        return "Bottom"
    if prev is not None and angle > prev + 2.0 and angle >= profile.transition_up_min:
        return "TransitionUp"
    if prev is not None and angle < prev - 2.0:
        return "TransitionDown"
    if angle < profile.transition_up_min:
        return "TransitionDown"
    return "TransitionUp"


def infer_run_phase(landmarks: Landmarks) -> str:
    left = landmarks.get("left_ankle")
    right = landmarks.get("right_ankle")
    if left and right:
        delta = left[1] - right[1]
        profile = run_profile()
        if delta <= -profile.min_step_delta_y:
            return "TransitionUp"
        if delta >= profile.min_step_delta_y:
            return "TransitionDown"
    return "Standing"


def infer_phase_for_exercise(exercise: str, landmarks: Landmarks, zone_id: str) -> str:
    if exercise == "PushUps":
        return infer_pushup_phase(landmarks, zone_id)
    if exercise == "Squats":
        return infer_squat_phase(landmarks, zone_id)
    if exercise == "RunInPlace":
        return infer_run_phase(landmarks)
    return "Neutral"


def score_pushups(landmarks: Landmarks, window: Sequence[Sequence[float]] | None) -> float:
    profile = pushup_profile()
    torso = torso_horizontal_span(landmarks)
    if torso > profile.max_torso_span:
        return 0.0
    elbow_drop, arm_extension, angle = pushup_body_metrics(landmarks)
    score = 0.4
    if elbow_drop is not None and elbow_drop >= profile.bottom_min_elbow_drop * 0.6:
        score += 0.25
    if angle is not None and angle < profile.standing_min_angle:
        score += 0.15
    if window and len(window) >= 5:
        elbow_metric, _ = _temporal_joint_angles(window)
        if elbow_metric is not None and elbow_metric >= profile.min_elbow_range:
            score += 0.45
        elif angle is not None and angle < 150:
            score += 0.2
    return score


def score_squats(landmarks: Landmarks, window: Sequence[Sequence[float]] | None) -> float:
    profile = squat_profile()
    torso = torso_vertical_span(landmarks)
    if torso < profile.min_torso_span:
        return 0.0
    angle = knee_angle(landmarks)
    score = 0.35
    if angle is not None and angle < profile.standing_min_angle:
        score += 0.25
    if angle is not None and angle < 140:
        score += 0.2
    if window and len(window) >= 5:
        _, knee_metric = _temporal_joint_angles(window)
        if knee_metric is not None and knee_metric >= profile.min_knee_range:
            score += 0.5
        elif angle is not None and angle < 150:
            score += 0.25
    elif angle is not None and angle < 140:
        score += 0.25
    return score


def score_run(landmarks: Landmarks, window: Sequence[Sequence[float]] | None) -> float:
    profile = run_profile()
    sig = motion_signature(landmarks, window)
    if sig["squat_torso"] < profile.min_torso_span:
        return 0.0
    pushup_torso = sig["pushup_torso"]
    if pushup_torso <= pushup_profile().max_torso_span * 0.55:
        return 0.05
    elbow_r = sig["elbow_range"] or 0.0
    knee_r = sig["knee_range"] or 0.0
    if elbow_r >= pushup_profile().min_elbow_range * 0.85:
        return 0.08
    if knee_r >= squat_profile().min_knee_range * 0.85:
        return 0.08

    ankle_std = sig["ankle_y_std"]
    _, ankle_delta = ankle_motion_stats(landmarks)
    score = 0.2
    if ankle_std >= profile.min_ankle_y_std:
        score += 0.45
    if ankle_delta >= profile.min_step_delta_y:
        score += 0.35
    if ankle_std >= profile.min_ankle_y_std * 1.4 and knee_r < 30:
        score += 0.2
    return score


def apply_discrimination_gates(
    landmarks: Landmarks,
    scores: dict[str, float],
    *,
    window: Sequence[Sequence[float]] | None = None,
) -> dict[str, float]:
    """Пост-обработка score/вероятностей: корпус + доминирующее движение (локти/колени/стопы)."""
    sig = motion_signature(landmarks, window)
    squat_torso = sig["squat_torso"]
    pushup_torso = sig["pushup_torso"]
    orientation = detect_body_orientation(landmarks)
    pu = pushup_profile()
    sq = squat_profile()
    run_p = run_profile()
    adjusted = dict(scores)

    if pushup_torso > pu.max_torso_span:
        adjusted["PushUps"] *= 0.1
        adjusted["Squats"] *= 0.35
        adjusted["RunInPlace"] *= 0.2
    elif pushup_torso < pu.max_torso_span * 0.75:
        adjusted["PushUps"] *= 1.25
        adjusted["RunInPlace"] *= 0.35

    if squat_torso < sq.min_torso_span:
        adjusted["Squats"] *= 0.1
        adjusted["PushUps"] *= 0.35
        adjusted["RunInPlace"] *= 0.25
    elif squat_torso >= sq.min_torso_span + 0.03:
        adjusted["Squats"] *= 1.25
        adjusted["RunInPlace"] *= 0.45

    if orientation != "frontal":
        adjusted["Squats"] *= 1.15
        adjusted["PushUps"] *= 1.1

    elbow_drop, _, elbow_ang = pushup_body_metrics(landmarks)
    knee_ang = knee_angle(landmarks, pick="min")
    elbow_r = sig["elbow_range"] or 0.0
    knee_r = sig["knee_range"] or 0.0
    ankle_std = sig["ankle_y_std"]

    if elbow_drop is not None and elbow_drop >= pu.bottom_min_elbow_drop * 0.5:
        adjusted["Squats"] *= 0.25
        adjusted["PushUps"] *= 1.2
        adjusted["RunInPlace"] *= 0.3
    if knee_ang is not None and knee_ang < 150:
        adjusted["PushUps"] *= 0.25
        adjusted["Squats"] *= 1.2
        adjusted["RunInPlace"] *= 0.35
    if elbow_ang is not None and elbow_ang < 150 and pushup_torso < pu.max_torso_span:
        adjusted["Squats"] *= 0.2

    if elbow_r >= pu.min_elbow_range and knee_r < pu.min_elbow_range * 0.65:
        adjusted["PushUps"] *= 1.35
        adjusted["Squats"] *= 0.2
        adjusted["RunInPlace"] *= 0.25
    elif knee_r >= sq.min_knee_range and elbow_r < sq.min_knee_range * 0.65:
        adjusted["Squats"] *= 1.35
        adjusted["PushUps"] *= 0.2
        adjusted["RunInPlace"] *= 0.3
    elif (
        ankle_std >= run_p.min_ankle_y_std
        and elbow_r < pu.min_elbow_range * 0.75
        and knee_r < sq.min_knee_range * 0.75
        and squat_torso >= run_p.min_torso_span
    ):
        adjusted["RunInPlace"] *= 1.4
        adjusted["PushUps"] *= 0.35
        adjusted["Squats"] *= 0.4

    return adjusted


def _pick_label_from_scores(
    scores: dict[str, float],
    landmarks: Landmarks,
    window: Sequence[Sequence[float]] | None,
) -> str:
    pu = pushup_profile()
    sq = squat_profile()
    sig = motion_signature(landmarks, window)
    pushup_torso = sig["pushup_torso"]
    squat_torso = sig["squat_torso"]

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best, best_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0
    margin = _env_float("GYMNET_CLASSIFY_MIN_MARGIN", 0.12)

    if best in ("PushUps", "Squats") and best_val - second_val < margin:
        split = (pu.max_torso_span + sq.min_torso_span) / 2.0
        elbow_r = sig["elbow_range"] or 0.0
        knee_r = sig["knee_range"] or 0.0
        if elbow_r >= knee_r + 8:
            best = "PushUps"
        elif knee_r >= elbow_r + 8:
            best = "Squats"
        else:
            best = "PushUps" if pushup_torso < split else "Squats"

    if best == "RunInPlace" or best_val < _env_float("GYMNET_CLASSIFY_MIN_SCORE", 0.35):
        elbow_r = sig["elbow_range"] or 0.0
        knee_r = sig["knee_range"] or 0.0
        if elbow_r >= pu.min_elbow_range * 0.7 and pushup_torso <= pu.max_torso_span:
            return "PushUps"
        if knee_r >= sq.min_knee_range * 0.7 and squat_torso >= sq.min_torso_span:
            return "Squats"
        if best_val >= _env_float("GYMNET_CLASSIFY_MIN_SCORE", 0.35):
            return best
        return "RunInPlace"

    return best


def classify_heuristic_detailed(
    landmarks: Landmarks,
    window: Sequence[Sequence[float]] | None = None,
) -> tuple[str, dict[str, float], dict[str, float | None], BodyOrientation]:
    raw_scores = {
        "PushUps": score_pushups(landmarks, window),
        "Squats": score_squats(landmarks, window),
        "RunInPlace": score_run(landmarks, window),
    }
    scores = apply_discrimination_gates(landmarks, raw_scores, window=window)
    sig = motion_signature(landmarks, window)
    squat_torso = sig["squat_torso"]
    pushup_torso = sig["pushup_torso"]
    orientation = detect_body_orientation(landmarks)
    best = _pick_label_from_scores(scores, landmarks, window)

    elbow_drop, arm_ext, elbow_ang = pushup_body_metrics(landmarks)
    knee_min = knee_angle(landmarks, pick="min")
    knee_max = knee_angle(landmarks, pick="max")
    left_ts, right_ts = torso_span_per_side(landmarks)
    debug: dict[str, float | None] = {
        "torso_vertical_span": round(squat_torso, 3),
        "torso_horizontal_span": round(pushup_torso, 3),
        "torso_span_left": round(left_ts, 3),
        "torso_span_right": round(right_ts, 3),
        "elbow_drop": round(elbow_drop, 3) if elbow_drop is not None else None,
        "arm_extension": round(arm_ext, 3) if arm_ext is not None else None,
        "elbow_angle": round(elbow_ang, 1) if elbow_ang is not None else None,
        "knee_angle_min": round(knee_min, 1) if knee_min is not None else None,
        "knee_angle_max": round(knee_max, 1) if knee_max is not None else None,
        "elbow_range_window": round(sig["elbow_range"], 1) if sig["elbow_range"] is not None else None,
        "knee_range_window": round(sig["knee_range"], 1) if sig["knee_range"] is not None else None,
        "ankle_y_std_window": round(sig["ankle_y_std"], 3),
        "body_orientation_code": {
            "frontal": 0.0,
            "left_profile": 1.0,
            "right_profile": 2.0,
        }.get(orientation, 0.0),
    }
    return best, {k: round(v, 3) for k, v in scores.items()}, debug, orientation


def classify_heuristic(
    landmarks: Landmarks,
    window: Sequence[Sequence[float]] | None = None,
) -> str:
    label, _, _, _ = classify_heuristic_detailed(landmarks, window)
    return label


def form_penalty_for_exercise(exercise: str, landmarks: Landmarks, phase: str) -> float:
    penalty = 0.0
    if exercise == "PushUps":
        profile = pushup_profile()
        elbow_drop, arm_extension, angle = pushup_body_metrics(landmarks)
        if phase == "Standing":
            incomplete = False
            if angle is not None and angle < profile.standing_min_angle:
                incomplete = True
            elif (
                elbow_drop is not None
                and arm_extension is not None
                and (
                    elbow_drop > profile.standing_max_elbow_drop
                    or arm_extension < profile.standing_min_arm_extension
                )
            ):
                incomplete = True
            if incomplete:
                penalty += 6.0
        torso = torso_horizontal_span(landmarks)
        if torso > profile.max_torso_span + 0.05:
            penalty += 4.0
    elif exercise == "Squats":
        profile = squat_profile()
        angle = knee_angle(landmarks)
        if phase == "Standing" and angle is not None and angle < profile.standing_min_angle:
            penalty += 6.0
        left_knee = landmarks.get("left_knee")
        right_knee = landmarks.get("right_knee")
        left_ankle = landmarks.get("left_ankle")
        right_ankle = landmarks.get("right_ankle")
        if left_knee and right_knee and left_ankle and right_ankle:
            knee_gap = abs(left_knee[0] - right_knee[0])
            ankle_gap = abs(left_ankle[0] - right_ankle[0])
            if knee_gap < ankle_gap * 0.6:
                penalty += 8.0
    elif exercise == "RunInPlace":
        profile = run_profile()
        ankle_std, _ = ankle_motion_stats(landmarks)
        if ankle_std < profile.min_ankle_y_std * 0.7:
            penalty += 3.0
    return penalty


def reset_phase_tracking(zone_id: str) -> None:
    with zone_lock(zone_id):
        _last_elbow_angle.pop(zone_id, None)
        _last_knee_angle.pop(zone_id, None)
