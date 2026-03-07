from __future__ import annotations

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse


class CSRFMiddleware(BaseHTTPMiddleware):
    """Valida CSRF token en mutaciones (POST/PUT/PATCH/DELETE).

    Regla:
    - Cookie 'csrf_token' (NO HttpOnly)
    - Header 'X-CSRF-Token'
    - Deben coincidir

    Excepciones: /auth/login, /auth/refresh, /auth/logout
    """

    async def dispatch(self, request: Request, call_next):
        if request.method in ["POST", "PUT", "DELETE", "PATCH"]:
            if request.url.path in ["/auth/login", "/auth/refresh", "/auth/logout"]:
                return await call_next(request)

            header_token = request.headers.get("X-CSRF-Token")
            cookie_token = request.cookies.get("csrf_token")

            if not header_token or header_token != cookie_token:
                return JSONResponse({"detail": "CSRF token inválido"}, status_code=403)

        response = await call_next(request)
        return response
