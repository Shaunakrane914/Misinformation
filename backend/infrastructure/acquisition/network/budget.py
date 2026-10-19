"""Cooperative deadline for one provider chain; not a thread-kill mechanism."""
from contextlib import contextmanager
from contextvars import ContextVar
import time

_deadline = ContextVar("acquisition_deadline", default=None)


def remaining_timeout(limit=5.0):
    deadline = _deadline.get()
    remaining = float(limit) if deadline is None else min(float(limit), deadline - time.monotonic())
    if remaining <= 0:
        raise TimeoutError("Acquisition chain deadline exhausted")
    return remaining


@contextmanager
def acquisition_deadline(deadline):
    """Nested calls may shorten, but never extend, the caller's budget."""
    parent = _deadline.get()
    token = _deadline.set(min(deadline, parent) if parent is not None else deadline)
    try:
        remaining_timeout()
        yield
    finally:
        _deadline.reset(token)
