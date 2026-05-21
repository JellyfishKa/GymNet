"""
Профили упражнений: углы, полное выпрямление (lockout), фазы SADLA.

Пороги можно переопределить через env, например:
GYMNET_PUSHUP_STANDING_MIN_ANGLE=168
"""

from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Sequence

import numpy as np

from app.services.landmark_sequence import FEATURE_DIM, LANDMARK_NAMES, WINDOW_SIZE

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


def _bilateral_angle(
    landmarks: Landmarks,
    *,
    a_left: str,
    b_left: str,
    c_left: str,
    a_right: str,
    b_right: str,
    c_right: str,
) -> float | None:
    angles: list[float] = []
    left_triple = (landmarks.get(a_left), landmarks.get(b_left), landmarks.get(c_left))
    if all(left_triple):
        angles.append(_angle(left_triple[0], left_triple[1], left_triple[2]))
    right_triple = (landmarks.get(a_right), landmarks.get(b_right), landmarks.get(c_right))
    if all(right_triple):
        angles.append(_angle(right_triple[0], right_triple[1], right_triple[2]))
    if not angles:
        return None
    return float(sum(angles) / len(angles))


def elbow_angle(landmarks: Landmarks) -> float | None:
    return _bilateral_angle(
        landmarks,
        a_left="left_shoulder",
        b_left="left_elbow",
        c_left="left_wrist",
        a_right="right_shoulder",
        b_right="right_elbow",
        c_right="right_wrist",
    )


def knee_angle(landmarks: Landmarks) -> float | None:
    return _bilateral_angle(
        landmarks,
        a_left="left_hip",
        b_left="left_knee",
        c_left="left_ankle",
        a_right="right_hip",
        b_right="right_knee",
        c_right="right_ankle",
    )


def torso_vertical_span(landmarks: Landmarks) -> float:
    shoulder = _pick(landmarks, "left_shoulder", "right_shoulder")
    hip = _pick(landmarks, "left_hip", "right_hip")
    if not shoulder or not hip:
        return 0.5
    return abs(hip[1] - shoulder[1])


def _avg_y(landmarks: Landmarks, names: tuple[str, ...]) -> float | None:
    ys = [landmarks[name][1] for name in names if name in landmarks]
    if not ys:
        return None
    return float(sum(ys) / len(ys))


def pushup_body_metrics(landmarks: Landmarks) -> tuple[float | None, float | None, float | None]:
    """(elbow_drop, arm_extension, elbow_angle) — устойчиво к ракурсу камеры."""
    shoulder_y = _avg_y(landmarks, ("left_shoulder", "right_shoulder"))
    elbow_y = _avg_y(landmarks, ("left_elbow", "right_elbow"))
    wrist_y = _avg_y(landmarks, ("left_wrist", "right_wrist"))
    if shoulder_y is None or elbow_y is None or wrist_y is None:
        return None, None, elbow_angle(landmarks)
    elbow_drop = elbow_y - shoulder_y
    arm_extension = wrist_y - elbow_y
    return elbow_drop, arm_extension, elbow_angle(landmarks)


def ankle_motion_stats(landmarks: Landmarks) -> tuple[float, float]:
    ankles = [landmarks.get("left_ankle"), landmarks.get("right_ankle")]
    ys = [p[1] for p in ankles if p]
    if len(ys) < 2:
        return 0.0, 0.0
    return float(np.std(ys)), float(max(ys) - min(ys))


def _temporal_joint_angles(window: Sequence[Sequence[float]]) -> tuple[float | None, float | None]:
    elbow_vals: list[float] = []
    knee_vals: list[float] = []
    for frame in window:
        if len(frame) != FEATURE_DIM:
            continue
        lm: Landmarks = {}
        for i, name in enumerate(LANDMARK_NAMES):
            lm[name] = (float(frame[i * 3]), float(frame[i * 3 + 1]))
        e = elbow_angle(lm)
        k = knee_angle(lm)
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
    metric = angle if angle is not None else 0.0
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
    angle = knee_angle(landmarks)
    if angle is None:
        return "Neutral"

    prev = _last_knee_angle.get(zone_id)
    _last_knee_angle[zone_id] = angle

    if angle >= profile.standing_min_angle:
        return "Standing"
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
    torso = torso_vertical_span(landmarks)
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
    torso = torso_vertical_span(landmarks)
    if torso < profile.min_torso_span:
        return 0.0
    ankle_std, ankle_delta = ankle_motion_stats(landmarks)
    score = 0.2
    if window and len(window) >= 5:
        ys: list[float] = []
        for frame in window:
            if len(frame) != FEATURE_DIM:
                continue
            al = float(frame[_ANKLE_L + 1])
            ar = float(frame[_ANKLE_R + 1])
            ys.extend([al, ar])
        if len(ys) >= 4:
            ankle_std = max(ankle_std, float(np.std(ys)))
    if ankle_std >= profile.min_ankle_y_std:
        score += 0.45
    if ankle_delta >= profile.min_step_delta_y:
        score += 0.35
    return score


def _apply_pose_orientation_gates(
    landmarks: Landmarks,
    scores: dict[str, float],
) -> dict[str, float]:
    """Жёстче разделяем отжимания (горизонтальный корпус) и приседания (вертикальный)."""
    torso = torso_vertical_span(landmarks)
    pu = pushup_profile()
    sq = squat_profile()
    adjusted = dict(scores)

    if torso > pu.max_torso_span:
        adjusted["PushUps"] *= 0.1
        adjusted["Squats"] *= 0.35
    elif torso < pu.max_torso_span * 0.75:
        adjusted["PushUps"] *= 1.25

    if torso < sq.min_torso_span:
        adjusted["Squats"] *= 0.1
        adjusted["PushUps"] *= 0.35
    elif torso >= sq.min_torso_span + 0.03:
        adjusted["Squats"] *= 1.25

    elbow_drop, _, elbow_ang = pushup_body_metrics(landmarks)
    knee_ang = knee_angle(landmarks)
    if elbow_drop is not None and elbow_drop >= pu.bottom_min_elbow_drop * 0.5:
        adjusted["Squats"] *= 0.25
        adjusted["PushUps"] *= 1.2
    if knee_ang is not None and knee_ang < 150:
        adjusted["PushUps"] *= 0.25
        adjusted["Squats"] *= 1.2
    if elbow_ang is not None and elbow_ang < 150 and torso < pu.max_torso_span:
        adjusted["Squats"] *= 0.2

    return adjusted


def classify_heuristic_detailed(
    landmarks: Landmarks,
    window: Sequence[Sequence[float]] | None = None,
) -> tuple[str, dict[str, float], dict[str, float | None]]:
    raw_scores = {
        "PushUps": score_pushups(landmarks, window),
        "Squats": score_squats(landmarks, window),
        "RunInPlace": score_run(landmarks, window),
    }
    scores = _apply_pose_orientation_gates(landmarks, raw_scores)
    torso = torso_vertical_span(landmarks)
    pu = pushup_profile()
    sq = squat_profile()

    ranked = sorted(scores.items(), key=lambda item: item[1], reverse=True)
    best, best_val = ranked[0]
    second_val = ranked[1][1] if len(ranked) > 1 else 0.0

    margin = _env_float("GYMNET_CLASSIFY_MIN_MARGIN", 0.12)
    if best in ("PushUps", "Squats") and best_val - second_val < margin:
        split = (pu.max_torso_span + sq.min_torso_span) / 2.0
        best = "PushUps" if torso < split else "Squats"

    if best_val < _env_float("GYMNET_CLASSIFY_MIN_SCORE", 0.35):
        best = "RunInPlace"

    elbow_drop, arm_ext, elbow_ang = pushup_body_metrics(landmarks)
    knee_ang = knee_angle(landmarks)
    debug: dict[str, float | None] = {
        "torso_vertical_span": round(torso, 3),
        "elbow_drop": round(elbow_drop, 3) if elbow_drop is not None else None,
        "arm_extension": round(arm_ext, 3) if arm_ext is not None else None,
        "elbow_angle": round(elbow_ang, 1) if elbow_ang is not None else None,
        "knee_angle": round(knee_ang, 1) if knee_ang is not None else None,
    }
    return best, {k: round(v, 3) for k, v in scores.items()}, debug


def classify_heuristic(
    landmarks: Landmarks,
    window: Sequence[Sequence[float]] | None = None,
) -> str:
    label, _, _ = classify_heuristic_detailed(landmarks, window)
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
        torso = torso_vertical_span(landmarks)
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
    _last_elbow_angle.pop(zone_id, None)
    _last_knee_angle.pop(zone_id, None)
