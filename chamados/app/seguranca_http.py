"""Cabeçalhos de segurança em todas as respostas."""
from starlette.middleware.base import BaseHTTPMiddleware


class CabecalhosDeSeguranca(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        resposta = await call_next(request)
        resposta.headers["X-Content-Type-Options"] = "nosniff"
        resposta.headers["X-Frame-Options"] = "DENY"
        resposta.headers["Referrer-Policy"] = "no-referrer"
        resposta.headers["Cache-Control"] = "no-store"
        return resposta
