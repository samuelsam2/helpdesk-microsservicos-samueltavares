"""Eventos publicados na fila e o que acontece quando a fila está fora do ar."""
import json

import pytest
import redis

from app.chamados import notificacoes

ANA, CARLA = 4, 2


def _eventos(fila):
    return [json.loads(i) for i in fila.itens]


def test_abrir_chamado_publica_chamado_aberto(client, cabecalho, novo_chamado, fila):
    r = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 201
    (evento,) = _eventos(fila)
    assert evento["tipo"] == "ChamadoAberto"
    assert evento["destinatario_id"] == ANA
    assert f"#{r.json()['id']}" in evento["mensagem"]


def test_atribuir_publica_evento_para_o_tecnico(client, cabecalho, novo_chamado, outros_servicos_no_ar, fila):
    chamado = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante")).json()
    client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=cabecalho(CARLA, "tecnico"))
    ultimo = _eventos(fila)[-1]
    assert ultimo["tipo"] == "ChamadoAtribuido" and ultimo["destinatario_id"] == 3


def test_resolver_publica_evento_para_o_solicitante(client, cabecalho, novo_chamado, outros_servicos_no_ar, fila):
    chamado = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante")).json()
    equipe = cabecalho(CARLA, "tecnico")
    client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=equipe)
    client.patch(f"/chamados/{chamado['id']}/status", json={"status": "resolvido"}, headers=equipe)
    ultimo = _eventos(fila)[-1]
    assert ultimo["tipo"] == "ChamadoResolvido" and ultimo["destinatario_id"] == ANA


def test_com_a_fila_fora_do_ar_o_chamado_abre_normalmente(client, cabecalho, novo_chamado, monkeypatch):
    class FilaQuebrada:
        def lpush(self, fila, corpo):
            raise redis.ConnectionError("redis fora do ar")

    monkeypatch.setattr(notificacoes, "_obter_cliente", lambda: FilaQuebrada())
    r = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 201  # o chamado NÃO depende do serviço de Notificações
    assert client.get(f"/chamados/{r.json()['id']}", headers=cabecalho(ANA, "solicitante")).status_code == 200
