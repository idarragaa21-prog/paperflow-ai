from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import decode_token


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware que extrae user_id del JWT y lo setea en request.state.

    Esto permite que el rate limiter use user_id cuando exista.
    """

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("access_token")
        if token:
            payload = decode_token(token, "access")
            if payload and payload.get("sub"):
                request.state.user_id = payload["sub"]
                request.state.session_id = payload.get("sid")

        response = await call_next(request)
        return response
