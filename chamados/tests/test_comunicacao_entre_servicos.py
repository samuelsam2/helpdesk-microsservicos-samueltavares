"""Comunicação por HTTP: o que acontece quando Usuários ou Inventário não respondem."""
import httpx
import pytest

from app.chamados import clientes
from app.erros import NaoEncontrado

ANA, CARLA = 4, 2


def _servico_fora_do_ar(erro):
    def falha(*args, **kwargs):
        raise erro
    return falha


@pytest.mark.parametrize("erro", [httpx.ConnectError("parado"), httpx.ReadTimeout("lento")])
def test_inventario_fora_do_ar_da_503_com_mensagem_clara(client, cabecalho, novo_chamado, monkeypatch, erro):
    monkeypatch.setattr(httpx, "get", _servico_fora_do_ar(erro))
    novo_chamado["ativo_id"] = 1
    r = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 503
    assert "Inventário" in r.json()["detail"]


def test_chamado_sem_equipamento_funciona_com_inventario_fora_do_ar(client, cabecalho, novo_chamado, monkeypatch):
    monkeypatch.setattr(httpx, "get", _servico_fora_do_ar(httpx.ConnectError("parado")))
    r = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 201


def test_listar_chamados_funciona_com_os_outros_servicos_fora_do_ar(client, cabecalho, novo_chamado, monkeypatch):
    client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    monkeypatch.setattr(httpx, "get", _servico_fora_do_ar(httpx.ConnectError("parado")))
    r = client.get("/chamados", headers=cabecalho(CARLA, "tecnico"))
    assert r.status_code == 200 and len(r.json()) == 1


def test_usuarios_fora_do_ar_da_503_ao_atribuir(client, cabecalho, novo_chamado, monkeypatch):
    chamado = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante")).json()
    monkeypatch.setattr(httpx, "get", _servico_fora_do_ar(httpx.ReadTimeout("lento")))
    r = client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=cabecalho(CARLA, "tecnico"))
    assert r.status_code == 503
    assert "Usuários" in r.json()["detail"]


def test_equipamento_inexistente_da_404(client, cabecalho, novo_chamado, monkeypatch):
    def nao_existe(ativo_id, token):
        raise NaoEncontrado(f"Ativo {ativo_id} não encontrado.")
    monkeypatch.setattr(clientes, "obter_ativo", nao_existe)
    novo_chamado["ativo_id"] = 99
    r = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 404


def test_o_token_do_usuario_e_repassado_ao_outro_servico(client, cabecalho, novo_chamado, monkeypatch):
    recebidos = {}

    class RespostaFalsa:
        status_code = 200

        def json(self):
            return {"id": 1}

    def get_falso(url, headers=None, timeout=None):
        recebidos.update(url=url, headers=headers, timeout=timeout)
        return RespostaFalsa()

    monkeypatch.setattr(httpx, "get", get_falso)
    entrada = cabecalho(ANA, "solicitante")
    novo_chamado["ativo_id"] = 1
    assert client.post("/chamados", json=novo_chamado, headers=entrada).status_code == 201
    assert recebidos["headers"]["Authorization"] == entrada["Authorization"]
    assert recebidos["url"].endswith("/ativos/1")
    assert recebidos["timeout"] and recebidos["timeout"] <= 5  # sempre com limite de tempo
