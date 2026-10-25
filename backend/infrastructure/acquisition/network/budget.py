"""Cooperative deadline for one provider chain; not a thread-kill mechanism."""
from contextlib import contextmanager
from contextvars import ContextVar
import time
import threading
from collections import Counter
from urllib.parse import urlsplit

_deadline = ContextVar("acquisition_deadline", default=None)
_request_budget = ContextVar("acquisition_request_budget", default=None)
_request_phase = ContextVar("acquisition_request_phase", default="reading")


class PublicRequestBudget:
    """Shared across copied worker contexts; counts native HTTP admissions.

    Reservations include redirects/retries and may fail before socket connect.
    These are not billed requests or proof the provider received a request.
    """
    def __init__(self, total=120, per_host=24):
        self.total, self.per_host = total, per_host
        self.lock = threading.Lock()
        self.hosts = Counter()
        self.closed = False
        self.rejected = 0
        self.phases = Counter()
        self.phase_hosts = Counter()
        self.discovery_limit = total
        self.discovery_per_host = per_host
        self.discovery_rejected = 0
        self._interleaved_discovery = None

    def reserve_reading_capacity(self, minimum):
        """Fence discovery, never extend total/host allowances or grant access.

        The unused allocation remains available for reads and their observed
        publisher lookups. It is an opportunity, not promised article yield.
        """
        with self.lock:
            limit = max(0, self.total - minimum)
            self.discovery_limit = min(self.discovery_limit, limit)
            if self._interleaved_discovery is not None:
                self._interleaved_discovery["legacy_discovery_cap"] = min(
                    self._interleaved_discovery["legacy_discovery_cap"], limit)
            self.discovery_per_host = min(self.discovery_per_host, max(1, self.per_host - 4))

    def configure_interleaved_discovery(self, initial=35, adaptive=25):
        """Opt in to a cumulative discovery allowance released after reads.

        Values are portions of a 120-admission budget, scaled down for smaller
        budgets. The pre-existing discovery fence remains authoritative. This
        is not an immutable per-worker phase quota: workers keep their copied
        ``discovery`` phase and share the currently released cumulative cap.
        Repeated configuration never resets spent admissions or released credit.
        """
        if (type(initial) is not int or type(adaptive) is not int
                or initial < 0 or adaptive < 0 or initial + adaptive > 60):
            raise ValueError("Discovery portions must be non-negative integers totaling at most 60")
        remaining_timeout()
        with self.lock:
            if self.closed:
                raise TimeoutError("Native HTTP request budget closed")
            if self._interleaved_discovery is not None:
                prior = self._interleaved_discovery
                if (initial, adaptive) != (prior["initial_portion"], prior["adaptive_portion"]):
                    raise ValueError("Interleaved discovery budget is already configured")
                return dict(prior)
            legacy_limit = self.discovery_limit
            scale = min(self.total, 120) / 120
            initial_limit = min(legacy_limit, max(self.phases["discovery"], round(initial * scale)))
            adaptive_reserve = min(max(0, legacy_limit - initial_limit), round(adaptive * scale))
            self.discovery_limit = initial_limit
            self._interleaved_discovery = {
                "initial_portion": initial, "adaptive_portion": adaptive,
                "initial_discovery_cap": initial_limit,
                "adaptive_reserved": adaptive_reserve, "adaptive_released": 0,
                "legacy_discovery_cap": legacy_limit,
                "scope": "CUMULATIVE_DISCOVERY_ALLOWANCE_NOT_PER_WORKER_PHASE_QUOTA",
            }
            return dict(self._interleaved_discovery)

    def release_adaptive_discovery(self, amount=None):
        """Release bounded reserved credit without changing total or host caps."""
        if amount is not None and (type(amount) is not int or amount < 0):
            raise ValueError("Adaptive release must be a non-negative integer")
        remaining_timeout()
        with self.lock:
            if self.closed:
                raise TimeoutError("Native HTTP request budget closed")
            state = self._interleaved_discovery
            if state is None:
                return 0
            available = max(0, state["adaptive_reserved"] - state["adaptive_released"])
            room = max(0, state["legacy_discovery_cap"] - self.discovery_limit)
            granted = min(available, room, available if amount is None else amount)
            self.discovery_limit += granted
            state["adaptive_released"] += granted
            return granted

    def discovery_remaining(self):
        with self.lock:
            return max(0, min(self.total - sum(self.hosts.values()),
                              self.discovery_limit - self.phases["discovery"]))

    def reserve(self, url):
        host = (urlsplit(url).hostname or "").lower()
        with self.lock:
            if self.closed or sum(self.hosts.values()) >= self.total or self.hosts[host] >= self.per_host:
                self.rejected += 1
                raise TimeoutError("Native HTTP request budget exhausted")
            phase = _request_phase.get()
            if phase == "discovery" and (self.phases[phase] >= self.discovery_limit
                    or self.phase_hosts[(phase, host)] >= self.discovery_per_host):
                self.rejected += 1
                self.discovery_rejected += 1
                raise TimeoutError("Discovery HTTP allowance exhausted; capacity reserved for reading")
            self.hosts[host] += 1
            self.phases[phase] += 1
            self.phase_hosts[(phase, host)] += 1

    def snapshot(self):
        with self.lock:
            result = {"native_http_admissions": sum(self.hosts.values()), "native_http_by_host": dict(self.hosts),
                    "native_http_cap": self.total, "native_http_per_host_cap": self.per_host,
                    "native_http_budget_rejections": self.rejected, "complete_network_accounting": False,
                    "native_http_by_phase": dict(self.phases), "discovery_http_cap": self.discovery_limit,
                    "discovery_http_per_host_cap": self.discovery_per_host,
                    "discovery_http_reserve_rejections": self.discovery_rejected}
            if self._interleaved_discovery is not None:
                result["interleaved_discovery_budget"] = dict(self._interleaved_discovery)
            return result

    def close(self):
        with self.lock:
            self.closed = True


def reserve_public_request(url):
    budget = _request_budget.get()
    if budget is not None:
        budget.reserve(url)


def has_public_request_budget():
    return _request_budget.get() is not None


def reserve_reading_capacity(minimum):
    budget = _request_budget.get()
    if budget is not None:
        budget.reserve_reading_capacity(min(max(0, minimum), budget.total // 2))


def configure_interleaved_discovery(initial=35, adaptive=25):
    budget = _request_budget.get()
    return budget.configure_interleaved_discovery(initial, adaptive) if budget is not None else None


def release_adaptive_discovery(amount=None):
    budget = _request_budget.get()
    return budget.release_adaptive_discovery(amount) if budget is not None else 0


def discovery_http_remaining():
    budget = _request_budget.get()
    return budget.discovery_remaining() if budget is not None else None


@contextmanager
def public_request_phase(phase):
    if phase not in {"discovery", "reading"}:
        raise ValueError("Unknown acquisition phase")
    token = _request_phase.set(phase)
    try:
        yield
    finally:
        _request_phase.reset(token)


@contextmanager
def public_request_budget(budget):
    token = _request_budget.set(budget)
    try:
        yield budget
    finally:
        _request_budget.reset(token)


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
