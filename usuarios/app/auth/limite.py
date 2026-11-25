"""Limite de tentativas de login (guardado na memória deste serviço)."""
import threading
import time

from app.config import LOGIN_JANELA_SEGUNDOS, LOGIN_MAX_FALHAS

_falhas: dict[str, list[float]] = {}
_trava = threading.Lock()


def _recentes(chave: str) -> list[float]:
    agora = time.monotonic()
    lista = [t for t in _falhas.get(chave, []) if agora - t < LOGIN_JANELA_SEGUNDOS]
    _falhas[chave] = lista
    return lista


def bloqueado(chave: str) -> bool:
    with _trava:
        return len(_recentes(chave)) >= LOGIN_MAX_FALHAS


def registrar_falha(chave: str) -> None:
    with _trava:
        _recentes(chave).append(time.monotonic())


def limpar(chave: str) -> None:
    with _trava:
        _falhas.pop(chave, None)
