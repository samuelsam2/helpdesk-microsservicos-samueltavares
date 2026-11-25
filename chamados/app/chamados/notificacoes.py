"""Aviso de eventos. BÔNUS: por enquanto só registra no log.

Quando o serviço de Notificações existir, aqui o chamado publica o evento
(ChamadoAberto, ChamadoAtribuido, ChamadoResolvido) em uma fila (Redis/RabbitMQ)
em vez de só escrever no log.
"""
import logging

log = logging.getLogger("helpdesk.chamados")


def notificar(evento: str, usuario_id: int, mensagem: str) -> None:
    log.info("evento=%s usuario=%s mensagem=%s", evento, usuario_id, mensagem)
