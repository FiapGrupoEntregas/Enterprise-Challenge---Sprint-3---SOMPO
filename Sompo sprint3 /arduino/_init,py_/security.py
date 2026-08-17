"""
AgroSafe Predictor - Sprint 3
Camada de Segurança da Informação.
Sompo Seguros | FIAP 1TIAOB

- Autenticação por API Key (header X-API-Key)
- Rate limiting simples por cliente (janela deslizante em memória)
- Toda tentativa (autorizada ou não) é registrada via database.registrar_log
"""

import time
from collections import defaultdict, deque

from fastapi import Header, HTTPException, Request, status

from backend.config import API_KEY, RATE_LIMIT_MAX_REQUESTS, RATE_LIMIT_WINDOW_SECONDS
from backend import database

_janelas_requisicoes: dict[str, deque] = defaultdict(deque)


def _cliente_id(request: Request, x_api_key: str | None) -> str:
    """Identifica o cliente para fins de rate limit e log (não expõe a key)."""
    if x_api_key:
        return f"key:{x_api_key[:4]}***"
    return f"ip:{request.client.host if request.client else 'desconhecido'}"


def verificar_rate_limit(cliente_id: str) -> bool:
    agora = time.monotonic()
    fila = _janelas_requisicoes[cliente_id]
    while fila and agora - fila[0] > RATE_LIMIT_WINDOW_SECONDS:
        fila.popleft()
    if len(fila) >= RATE_LIMIT_MAX_REQUESTS:
        return False
    fila.append(agora)
    return True


async def exigir_api_key(request: Request, x_api_key: str | None = Header(default=None)):
    """Dependência FastAPI: valida a API key e o rate limit antes de liberar o endpoint."""
    cliente_id = _cliente_id(request, x_api_key)
    endpoint = request.url.path

    if not x_api_key or x_api_key != API_KEY:
        database.registrar_log(endpoint, request.method, cliente_id, 401, "API key ausente ou inválida")
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="API key ausente ou inválida. Envie o header 'X-API-Key'.",
        )

    if not verificar_rate_limit(cliente_id):
        database.registrar_log(endpoint, request.method, cliente_id, 429, "Rate limit excedido")
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Limite de requisições excedido. Tente novamente em instantes.",
        )

    return cliente_id
