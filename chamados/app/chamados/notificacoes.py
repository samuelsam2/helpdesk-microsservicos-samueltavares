"""Publica eventos (ChamadoAberto, ChamadoAtribuido, ChamadoResolvido) na fila do Redis.

Quem transforma o evento em aviso para o usuário é o serviço de Notificações.
Regra importante: se a fila ou o serviço de Notificações estiver fora do ar, o chamado
continua funcionando. Só registramos um aviso no log e seguimos.
"""
import json
import logging
from datetime import datetime

import redis

from app.config import FILA_EVENTOS, REDIS_URL

log = logging.getLogger("helpdesk.chamados")

_cliente = None


def _obter_cliente():
    global _cliente
    if _cliente is None:
        # timeouts curtos: com o Redis fora do ar, não podemos deixar o chamado esperando
        _cliente = redis.Redis.from_url(REDIS_URL, socket_connect_timeout=1, socket_timeout=1)
    return _cliente


def notificar(evento: str, usuario_id: int, mensagem: str) -> None:
    corpo = json.dumps(
        {"tipo": evento, "destinatario_id": usuario_id, "mensagem": mensagem, "criada_em": datetime.now().isoformat()}
    )
    try:
        _obter_cliente().lpush(FILA_EVENTOS, corpo)
    except redis.RedisError as erro:
        log.warning("Fila indisponível, evento %s não publicado: %s", evento, erro)
