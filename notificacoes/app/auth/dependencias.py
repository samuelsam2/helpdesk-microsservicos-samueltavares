"""Exige login e perfil lendo só o token (este serviço não tem o banco de usuários)."""
from dataclasses import dataclass

from fastapi import Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.auth import tokens

esquema = HTTPBearer(auto_error=False)


def _nao_autenticado() -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Faça login para continuar.",
        headers={"WWW-Authenticate": "Bearer"},
    )


@dataclass(frozen=True)
class Identidade:
    """Quem está chamando, segundo o token. `token` guarda o cabeçalho para repassar a outros serviços."""
    id: int
    perfil: str
    token: str


def usuario_atual(credenciais: HTTPAuthorizationCredentials | None = Depends(esquema)) -> Identidade:
    if credenciais is None or credenciais.scheme.lower() != "bearer":
        raise _nao_autenticado()
    try:
        usuario_id, perfil = tokens.ler(credenciais.credentials)
    except tokens.TokenInvalido:
        raise _nao_autenticado()
    return Identidade(usuario_id, perfil, f"Bearer {credenciais.credentials}")


def exigir_perfil(*perfis: str):
    def verificar(usuario: Identidade = Depends(usuario_atual)) -> Identidade:
        if usuario.perfil not in perfis:
            raise HTTPException(status.HTTP_403_FORBIDDEN, "Você não tem permissão para esta ação.")
        return usuario
    return verificar
