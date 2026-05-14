from dataclasses import dataclass


@dataclass(slots=True)
class RoiRect:
    x_min: float
    y_min: float
    x_max: float
    y_max: float


def _angle(a: tuple[float, float], b: tuple[float, float], c: tuple[float, float]) -> float:
    import math

    ba = (a[0] - b[0], a[1] - b[1])
    bc = (c[0] - b[0], c[1] - b[1])
    dot = ba[0] * bc[0] + ba[1] * bc[1]
    norm_ba = math.hypot(ba[0], ba[1]) or 1e-6
    norm_bc = math.hypot(bc[0], bc[1]) or 1e-6
    cos_value = max(-1.0, min(1.0, dot / (norm_ba * norm_bc)))
    return math.degrees(math.acos(cos_value))


def points_inside_roi(landmarks: list[tuple[float, float]], roi: RoiRect) -> float:
    if not landmarks:
        return 0.0
    inside = 0
    for x, y in landmarks:
        if roi.x_min <= x <= roi.x_max and roi.y_min <= y <= roi.y_max:
            inside += 1
    return inside / len(landmarks)


def detect_presence(landmarks: list[tuple[float, float]], roi: RoiRect, threshold: float = 0.25) -> bool:
    return points_inside_roi(landmarks, roi) >= threshold


def classify_exercise(landmarks: dict[str, tuple[float, float]], treadmill_zone: bool = False) -> str:
    if treadmill_zone:
        return "RunInPlace"

    wrists = [landmarks.get("left_wrist"), landmarks.get("right_wrist")]
    shoulders = [landmarks.get("left_shoulder"), landmarks.get("right_shoulder")]
    hips = [landmarks.get("left_hip"), landmarks.get("right_hip")]
    knees = [landmarks.get("left_knee"), landmarks.get("right_knee")]

    if all(w and s for w, s in zip(wrists, shoulders)):
        # Wrists above shoulder level often indicates pulling band in this MVP heuristic.
        if wrists[0][1] < shoulders[0][1] and wrists[1][1] < shoulders[1][1]:
            return "ResistanceBand"

    if all(h and k for h, k in zip(hips, knees)):
        hip_to_knee_vertical = abs(hips[0][1] - knees[0][1]) + abs(hips[1][1] - knees[1][1])
        if hip_to_knee_vertical < 0.18:
            return "PushUps"

    return "Squats"


def infer_phase(exercise: str, landmarks: dict[str, tuple[float, float]]) -> str:
    if exercise == "PushUps":
        elbow = landmarks.get("left_elbow")
        shoulder = landmarks.get("left_shoulder")
        wrist = landmarks.get("left_wrist")
        if elbow and shoulder and wrist:
            angle = _angle(shoulder, elbow, wrist)
            if angle < 80:
                return "Bottom"
            if angle < 140:
                return "TransitionDown"
            return "Standing"
        return "Neutral"

    if exercise == "Squats":
        hip = landmarks.get("left_hip")
        knee = landmarks.get("left_knee")
        ankle = landmarks.get("left_ankle")
        if hip and knee and ankle:
            angle = _angle(hip, knee, ankle)
            if angle < 90:
                return "Bottom"
            if angle < 140:
                return "TransitionDown"
            return "Standing"
        return "Neutral"

    if exercise == "RunInPlace":
        return "Standing"

    return "TransitionUp"


def form_penalty(exercise: str, landmarks: dict[str, tuple[float, float]]) -> float:
    if exercise == "Squats":
        left_knee = landmarks.get("left_knee")
        right_knee = landmarks.get("right_knee")
        left_ankle = landmarks.get("left_ankle")
        right_ankle = landmarks.get("right_ankle")
        if left_knee and right_knee and left_ankle and right_ankle:
            knee_gap = abs(left_knee[0] - right_knee[0])
            ankle_gap = abs(left_ankle[0] - right_ankle[0])
            if knee_gap < ankle_gap * 0.6:
                return 8.0
    return 0.0
