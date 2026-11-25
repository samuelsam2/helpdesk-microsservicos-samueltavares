"""Serviço de Notificações: consumo de eventos da fila e leitura protegida por token."""
import json
import threading
from datetime import datetime, timedelta, timezone

import jwt
import redis

from app.config import JWT_ALGORITMO, JWT_EMISSOR
from app.notificacoes import consumidor


def _evento(tipo="ChamadoAberto", destinatario_id=4, mensagem="Seu chamado #1 foi aberto."):
    return json.dumps({"tipo": tipo, "destinatario_id": destinatario_id, "mensagem": mensagem})


class FilaFalsa:
    """Finge o Redis: entrega os itens combinados e depois manda o consumidor parar."""

    def __init__(self, itens, parar, erro_antes=None):
        self.itens, self.parar, self.erro_antes = list(itens), parar, erro_antes

    def brpop(self, fila, timeout=0):
        if self.erro_antes:
            erro, self.erro_antes = self.erro_antes, None
            raise erro
        if self.itens:
            return (fila, self.itens.pop(0))
        self.parar.set()
        return None


# ---------- consumidor ----------
def test_evento_valido_vira_notificacao(client, cabecalho):
    assert consumidor.processar_mensagem(_evento()) is True
    r = client.get("/notificacoes", headers=cabecalho(4))
    assert r.status_code == 200
    assert [n["tipo"] for n in r.json()] == ["ChamadoAberto"]
    assert r.json()[0]["destinatario_id"] == 4


def test_evento_invalido_e_descartado_sem_derrubar(client, cabecalho):
    assert consumidor.processar_mensagem("isto não é json") is False
    assert consumidor.processar_mensagem(json.dumps({"tipo": "X"})) is False  # faltam campos
    assert client.get("/notificacoes", headers=cabecalho(4)).json() == []


def test_laco_do_consumidor_grava_todos_os_eventos(client, cabecalho):
    parar = threading.Event()
    fila = FilaFalsa([_evento(destinatario_id=4), _evento("ChamadoResolvido", 4, "Resolvido")], parar)
    consumidor.rodar(parar, cliente=fila)
    assert [n["tipo"] for n in client.get("/notificacoes", headers=cabecalho(4)).json()] == [
        "ChamadoAberto", "ChamadoResolvido"]


def test_consumidor_sobrevive_a_queda_do_redis(client, cabecalho, monkeypatch):
    monkeypatch.setattr(consumidor, "ESPERA_ENTRE_TENTATIVAS", 0)
    parar = threading.Event()
    fila = FilaFalsa([_evento()], parar, erro_antes=redis.ConnectionError("redis caiu"))
    consumidor.rodar(parar, cliente=fila)
    assert len(client.get("/notificacoes", headers=cabecalho(4)).json()) == 1


# ---------- leitura ----------
def test_cada_usuario_ve_so_as_proprias_notificacoes(client, cabecalho):
    consumidor.processar_mensagem(_evento(destinatario_id=4, mensagem="da Ana"))
    consumidor.processar_mensagem(_evento(destinatario_id=5, mensagem="do Diego"))
    da_ana = client.get("/notificacoes", headers=cabecalho(4)).json()
    assert [n["mensagem"] for n in da_ana] == ["da Ana"]


def test_admin_tambem_so_ve_as_proprias(client, cabecalho):
    consumidor.processar_mensagem(_evento(destinatario_id=4))
    assert client.get("/notificacoes", headers=cabecalho(1, "admin")).json() == []


def test_sem_token_da_401(client):
    assert client.get("/notificacoes").status_code == 401


def test_token_invalido_expirado_ou_de_outro_segredo_da_401(client):
    assert client.get("/notificacoes", headers={"Authorization": "Bearer lixo"}).status_code == 401
    agora = datetime.now(timezone.utc)
    base = {"sub": "4", "perfil": "solicitante", "iat": agora, "iss": JWT_EMISSOR}
    expirado = jwt.encode({**base, "exp": agora - timedelta(minutes=1)}, __import__("app.config").config.JWT_SEGREDO, algorithm=JWT_ALGORITMO)
    falso = jwt.encode({**base, "exp": agora + timedelta(minutes=5)}, "outro-segredo-qualquer-com-mais-de-32-caracteres", algorithm=JWT_ALGORITMO)
    assert client.get("/notificacoes", headers={"Authorization": f"Bearer {expirado}"}).status_code == 401
    assert client.get("/notificacoes", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_saude_responde_sem_token(client):
    r = client.get("/saude")
    assert r.status_code == 200 and r.json() == {"status": "ok", "servico": "notificacoes"}
