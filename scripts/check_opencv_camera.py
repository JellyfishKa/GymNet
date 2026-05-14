"""
Диагностика OpenCV-камеры:
- версия OpenCV
- какие индексы камеры доступны
- удается ли прочитать хотя бы один кадр
"""

from __future__ import annotations

import cv2


def probe_camera(index: int) -> tuple[bool, bool, str]:
    cap = cv2.VideoCapture(index, cv2.CAP_ANY)
    opened = cap.isOpened()
    if not opened:
        cap.release()
        return False, False, "не открыта"
    ok, _frame = cap.read()
    cap.release()
    if not ok:
        return True, False, "открыта, но кадр не читается"
    return True, True, "открыта и кадр читается"


def main() -> None:
    print(f"OpenCV version: {cv2.__version__}")
    print("Проверка индексов камеры 0..3")
    any_ok = False
    for idx in range(4):
        opened, readable, message = probe_camera(idx)
        print(f"Камера {idx}: {message}")
        if opened and readable:
            any_ok = True

    if not any_ok:
        print("ИТОГ: рабочая камера не найдена в OpenCV.")
        print("Проверьте права доступа к камере и закрытие других приложений (Zoom, Telegram, браузер).")
    else:
        print("ИТОГ: OpenCV видит как минимум одну рабочую камеру.")


if __name__ == "__main__":
    main()
