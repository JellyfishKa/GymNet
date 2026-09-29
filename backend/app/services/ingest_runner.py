"""Отдельный пул потоков для ingest — не делим default pool с GET /api/ml/status."""

from __future__ import annotations

import asyncio
import threading
import time
from concurrent.futures import ThreadPoolExecutor

from app.schemas.ingest import PoseIngestRequest, PoseIngestResponse
from app.services.pose_ingest import process_pose_ingest

# Один worker: GPU inference + zone state без гонок.
_INGEST_POOL = ThreadPoolExecutor(max_workers=1, thread_name_prefix="gymnet-ingest")
_ingest_gate = threading.Lock()
_ingest_running = False


class IngestBusyError(Exception):
    """Не удалось занять слот ingest за отведённое ожидание."""


def ingest_slot_busy() -> bool:
    with _ingest_gate:
        return _ingest_running


async def wait_for_ingest_slot(wait_sec: float) -> bool:
    """Ждём и атомарно занимаем слот (после WS timeout поток может ещё работать)."""
    global _ingest_running
    deadline = time.monotonic() + max(0.05, wait_sec)
    while time.monotonic() < deadline:
        with _ingest_gate:
            if not _ingest_running:
                _ingest_running = True
                return True
        await asyncio.sleep(0.03)
    return False


def _run_ingest_gated(payload: PoseIngestRequest) -> PoseIngestResponse:
    global _ingest_running
    try:
        return process_pose_ingest(payload)
    finally:
        with _ingest_gate:
            _ingest_running = False


async def run_pose_ingest_async(
    payload: PoseIngestRequest,
    *,
    timeout_sec: float,
) -> PoseIngestResponse:
    slot_wait = max(1.0, timeout_sec - 1.0)
    if not await wait_for_ingest_slot(slot_wait):
        raise IngestBusyError()

    loop = asyncio.get_running_loop()
    try:
        return await asyncio.wait_for(
            loop.run_in_executor(_INGEST_POOL, _run_ingest_gated, payload),
            timeout=timeout_sec,
        )
    except Exception:
        with _ingest_gate:
            if _ingest_running:
                _ingest_running = False
        raise
