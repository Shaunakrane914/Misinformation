"""
Aegis Protocol — Web Platform Acquisition Adapters
===================================================
Scrapling HTTP, Playwright rescue, and Jina Reader adapters for web document acquisition.
"""

from backend.infrastructure.acquisition.adapters.web.jina import (
    JinaWebReaderAdapter,
    execute_web_read,
)

__all__ = [
    "JinaWebReaderAdapter",
    "execute_web_read",
]
