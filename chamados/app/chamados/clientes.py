"""Chamadas HTTP aos outros serviços (no monólito eram chamadas de função).

Regras:
- sempre com timeout, para não ficar esperando para sempre;
- o token do usuário é repassado no cabeçalho Authorization (o outro serviço confere de novo);
- se o outro serviço não responder, lançamos ServicoIndisponivel, que vira HTTP 503.
"""
import httpx
from fastapi import HTTPException

from app.config import INVENTARIO_URL, TIMEOUT_SEGUNDOS, USUARIOS_URL
from app.erros import NaoEncontrado, RegraDeNegocio, ServicoIndisponivel


def _buscar(nome_do_servico: str, url: str, token: str) -> dict | None:
    """GET no outro serviço. Devolve o JSON, ou None se for 404."""
    try:
        resposta = httpx.get(url, headers={"Authorization": token}, timeout=TIMEOUT_SEGUNDOS)
    except httpx.HTTPError as erro:  # timeout, conexão recusada, serviço parado...
        raise ServicoIndisponivel(
            f"O serviço de {nome_do_servico} está indisponível. Tente novamente em instantes."
        ) from erro
    if resposta.status_code == 404:
        return None
    if resposta.status_code == 401:
        raise HTTPException(401, "Faça login para continuar.", headers={"WWW-Authenticate": "Bearer"})
    if resposta.status_code >= 400:
        raise ServicoIndisponivel(f"O serviço de {nome_do_servico} respondeu com erro ({resposta.status_code}).")
    return resposta.json()


def obter_tecnico(usuario_id: int, token: str) -> dict:
    """Confere no serviço de Usuários se o id existe e é de um técnico."""
    dados = _buscar("Usuários", f"{USUARIOS_URL}/usuarios/{usuario_id}", token)
    if dados is None:
        raise NaoEncontrado(f"Usuário {usuario_id} não encontrado.")
    if dados.get("perfil") != "tecnico":
        raise RegraDeNegocio(f"Usuário {usuario_id} não é técnico.")
    return dados


def obter_ativo(ativo_id: int, token: str) -> dict:
    """Confere no serviço de Inventário se o equipamento existe."""
    dados = _buscar("Inventário", f"{INVENTARIO_URL}/ativos/{ativo_id}", token)
    if dados is None:
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    return dados
