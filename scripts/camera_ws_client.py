"""
Простой клиент веб-камеры:
- получает landmarks через MediaPipe
- формирует событие позы через /api/live/ingest
- отправляет события в backend websocket /ws/live
"""

from __future__ import annotations

import json
import time

import cv2
import requests
import websockets.sync.client

try:
    import mediapipe as mp
except Exception:  # pragma: no cover - необязательно для окружений без камеры
    mp = None


BACKEND_HTTP = "http://localhost:8000"
BACKEND_WS = "ws://localhost:8000/ws/live"
ZONE_ID = "treadmill_zone_1"

# Нормализованный ROI для зоны "беговой дорожки" в кадре.
ROI = {"x_min": 0.25, "y_min": 0.2, "x_max": 0.75, "y_max": 0.95}


def iter_landmarks(cap: cv2.VideoCapture):
    if mp is None:
        raise RuntimeError("Пакет mediapipe не установлен")

    pose = mp.solutions.pose.Pose(
        min_detection_confidence=0.5,
        min_tracking_confidence=0.5,
    )
    landmark_names = [lm.name.lower() for lm in mp.solutions.pose.PoseLandmark]

    while True:
        ok, frame = cap.read()
        if not ok:
            break
        rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        result = pose.process(rgb)
        if not result.pose_landmarks:
            yield []
            continue

        payload = []
        for idx, lm in enumerate(result.pose_landmarks.landmark):
            payload.append({"name": landmark_names[idx], "x": float(lm.x), "y": float(lm.y)})
        yield payload


def run() -> None:
    cap = cv2.VideoCapture(0)
    if not cap.isOpened():
        raise RuntimeError("Не удалось открыть камеру")

    with websockets.sync.client.connect(BACKEND_WS) as ws:
        for landmarks in iter_landmarks(cap):
            ingest_payload = {
                "zone_id": ZONE_ID,
                "roi": ROI,
                "treadmill_zone": True,
                "landmarks": landmarks,
            }
            ingest_response = requests.post(f"{BACKEND_HTTP}/api/live/ingest", json=ingest_payload, timeout=2.0)
            ingest_response.raise_for_status()
            live_event = ingest_response.json()

            ws.send(json.dumps(live_event))
            _ = ws.recv()
            print(
                f"exercise={live_event['exercise']} present={live_event['is_present']} "
                f"phase={live_event['phase']} penalty={live_event['form_penalty']}"
            )
            time.sleep(0.1)

    cap.release()


if __name__ == "__main__":
    run()
