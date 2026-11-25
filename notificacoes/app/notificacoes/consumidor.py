"""Consumidor da fila: lê os eventos que o serviço de Chamados publicou e grava as notificações.

A fila é uma lista do Redis. Chamados coloca eventos com LPUSH; aqui tiramos com BRPOP.
Se este serviço ficar fora do ar, os eventos esperam na fila e são processados quando ele voltar.
Se o Redis cair, o consumidor tenta de novo a cada poucos segundos, sem derrubar o serviço.
"""
import json
import logging
import threading
from datetime import datetime

import redis
from pydantic import BaseModel, Field, ValidationError

from app.config import FILA_EVENTOS, REDIS_URL
from app.database import SessionLocal
from app.notificacoes import servico

log = logging.getLogger("helpdesk.notificacoes")

ESPERA_ENTRE_TENTATIVAS = 2.0


class Evento(BaseModel):
    tipo: str = Field(min_length=1, max_length=40)
    destinatario_id: int
    mensagem: str = Field(min_length=1, max_length=300)
    criada_em: datetime | None = None


def processar_mensagem(texto: str | bytes) -> bool:
    """Valida um evento e grava a notificação. Devolve False se o evento for inválido (é descartado)."""
    try:
        evento = Evento.model_validate(json.loads(texto))
    except (ValueError, ValidationError):
        log.warning("Evento inválido descartado: %r", texto)
        return False
    with SessionLocal() as db:
        servico.notificar(db, evento.tipo, evento.destinatario_id, evento.mensagem, evento.criada_em)
    log.info("Notificação gravada: %s para o usuário %s", evento.tipo, evento.destinatario_id)
    return True


def rodar(parar: threading.Event, cliente=None) -> None:
    """Laço do consumidor. Roda numa thread até `parar` ser acionado."""
    cliente = cliente or redis.Redis.from_url(REDIS_URL, socket_connect_timeout=2, socket_timeout=5)
    while not parar.is_set():
        try:
            item = cliente.brpop(FILA_EVENTOS, timeout=2)
            if item is None:
                continue
            processar_mensagem(item[1])
        except redis.RedisError as erro:
            log.warning("Fila indisponível (%s). Nova tentativa em instantes.", erro)
            parar.wait(ESPERA_ENTRE_TENTATIVAS)
        except Exception:  # um evento ruim nunca pode derrubar o consumidor
            log.exception("Erro ao processar evento")
