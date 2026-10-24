"""Request-local observation only: never changes evidence or research budgets."""

from contextvars import ContextVar


progress_observer = ContextVar("research_progress_observer", default=None)
requested_research_profile = ContextVar("requested_research_profile", default=None)


def report_progress(**observation):
    observer = progress_observer.get()
    if observer is not None:
        try:
            observer(observation)
        except Exception:
            pass  # Telemetry must not turn a successful investigation into failure.
