from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.core.security import verify_token


class AuthMiddleware(BaseHTTPMiddleware):
    """Middleware que extrae user_id del JWT y lo setea en request.state.

    Esto permite que el rate limiter use user_id cuando exista.
    """

    async def dispatch(self, request: Request, call_next):
        token = request.cookies.get("access_token")
        if token:
            user_id = verify_token(token, "access")
            if user_id:
                request.state.user_id = user_id

        response = await call_next(request)
        return response
