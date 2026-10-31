"""Shared SEC request spacing within the existing cooperative deadline."""
import threading
import time

from backend.infrastructure.acquisition.network.budget import remaining_timeout

_lock = threading.Lock()
_last_admitted = 0.0


def wait_for_sec_slot():
    global _last_admitted
    allowance = remaining_timeout(5.0)
    if not _lock.acquire(timeout=allowance):
        raise TimeoutError("SEC request spacing deadline exhausted")
    try:
        delay = max(0.0, _last_admitted + 0.12 - time.monotonic())
        if delay >= remaining_timeout(allowance):
            raise TimeoutError("SEC request spacing exceeds remaining deadline")
        if delay:
            time.sleep(delay)
        _last_admitted = time.monotonic()
    finally:
        _lock.release()
