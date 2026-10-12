"""Small, fail-closed authorization boundary for operator-only mutations.

The operator token is a server secret, not a frontend configuration value. Public
research endpoints remain public; possession grants only the response-deployment
capability guarded by this dependency.
"""

import secrets

from fastapi import Header, HTTPException

from backend.core.settings import settings


def require_response_operator(authorization: str = Header(default="")) -> None:
    configured = getattr(settings, "admin_api_token", "") or ""
    if hasattr(configured, "get_secret_value"):
        configured = configured.get_secret_value()
    if not configured:
        raise HTTPException(status_code=503, detail="Operator authorization is not configured")
    scheme, _, supplied = authorization.partition(" ")
    if scheme.lower() != "bearer" or not supplied or not secrets.compare_digest(
        supplied.encode("utf-8"), str(configured).encode("utf-8")
    ):
        raise HTTPException(
            status_code=401,
            detail="Operator authorization required",
            headers={"WWW-Authenticate": "Bearer"},
        )
