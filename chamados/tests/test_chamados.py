"""Serviço de Chamados: regras do monólito (SLA, transições, permissões)."""
from datetime import datetime, timedelta, timezone

import jwt
import pytest

from app.config import JWT_ALGORITMO, JWT_EMISSOR, JWT_SEGREDO

ANA, DIEGO, CARLA = 4, 5, 2  # ids só para os tokens: aqui não existe banco de usuários


def _abrir(client, cabecalho, corpo, usuario_id=ANA, perfil="solicitante"):
    r = client.post("/chamados", json=corpo, headers=cabecalho(usuario_id, perfil))
    assert r.status_code == 201, r.text
    return r.json()


def test_abrir_chamado_define_status_solicitante_e_prazo(client, cabecalho, novo_chamado):
    chamado = _abrir(client, cabecalho, novo_chamado)
    assert chamado["status"] == "aberto"
    assert chamado["solicitante_id"] == ANA
    assert chamado["tecnico_id"] is None


@pytest.mark.parametrize("prioridade,horas", [("critica", 4), ("alta", 8), ("media", 24), ("baixa", 72)])
def test_prazo_de_sla_depende_da_prioridade(client, cabecalho, novo_chamado, prioridade, horas):
    novo_chamado["prioridade"] = prioridade
    chamado = _abrir(client, cabecalho, novo_chamado)
    criado = datetime.fromisoformat(chamado["criado_em"])
    prazo = datetime.fromisoformat(chamado["prazo_sla"])
    assert prazo - criado == timedelta(hours=horas)


def test_solicitante_nao_consegue_escolher_outro_solicitante(client, cabecalho, novo_chamado):
    novo_chamado["solicitante_id"] = DIEGO
    r = client.post("/chamados", json=novo_chamado, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 422


def test_solicitante_ve_so_os_proprios_chamados(client, cabecalho, novo_chamado):
    _abrir(client, cabecalho, novo_chamado, ANA)
    _abrir(client, cabecalho, novo_chamado, DIEGO)
    da_ana = client.get("/chamados", headers=cabecalho(ANA, "solicitante")).json()
    da_equipe = client.get("/chamados", headers=cabecalho(CARLA, "tecnico")).json()
    assert len(da_ana) == 1 and da_ana[0]["solicitante_id"] == ANA
    assert len(da_equipe) == 2


def test_solicitante_nao_ve_chamado_de_outra_pessoa(client, cabecalho, novo_chamado):
    do_diego = _abrir(client, cabecalho, novo_chamado, DIEGO)
    r = client.get(f"/chamados/{do_diego['id']}", headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 404  # não revela nem que o chamado existe
    assert client.get(f"/chamados/{do_diego['id']}", headers=cabecalho(CARLA, "tecnico")).status_code == 200


def test_sem_token_da_401(client):
    assert client.get("/chamados").status_code == 401
    assert client.get("/chamados/painel").status_code == 401
    assert client.post("/chamados", json={}).status_code == 401


def test_token_invalido_ou_expirado_da_401(client):
    assert client.get("/chamados", headers={"Authorization": "Bearer lixo"}).status_code == 401
    agora = datetime.now(timezone.utc)
    dados = {"sub": "4", "perfil": "tecnico", "iat": agora, "exp": agora - timedelta(minutes=1), "iss": JWT_EMISSOR}
    expirado = jwt.encode(dados, JWT_SEGREDO, algorithm=JWT_ALGORITMO)
    assert client.get("/chamados", headers={"Authorization": f"Bearer {expirado}"}).status_code == 401


def test_token_de_outro_segredo_da_401(client):
    agora = datetime.now(timezone.utc)
    dados = {"sub": "4", "perfil": "admin", "iat": agora, "exp": agora + timedelta(minutes=5), "iss": JWT_EMISSOR}
    falso = jwt.encode(dados, "outro-segredo-qualquer-com-mais-de-32-caracteres", algorithm=JWT_ALGORITMO)
    assert client.get("/chamados", headers={"Authorization": f"Bearer {falso}"}).status_code == 401


def test_solicitante_nao_atribui_chamado(client, cabecalho, novo_chamado, outros_servicos_no_ar):
    chamado = _abrir(client, cabecalho, novo_chamado)
    r = client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 403


def test_fluxo_completo_do_chamado(client, cabecalho, novo_chamado, outros_servicos_no_ar):
    chamado = _abrir(client, cabecalho, novo_chamado)
    equipe = cabecalho(CARLA, "tecnico")
    r = client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=equipe)
    assert r.status_code == 200
    assert r.json()["status"] == "em_atendimento" and r.json()["tecnico_id"] == 3
    r = client.patch(f"/chamados/{chamado['id']}/status", json={"status": "resolvido"}, headers=equipe)
    assert r.json()["status"] == "resolvido"
    r = client.patch(f"/chamados/{chamado['id']}/status", json={"status": "fechado"}, headers=equipe)
    assert r.json()["status"] == "fechado"


def test_transicao_invalida_da_422(client, cabecalho, novo_chamado):
    chamado = _abrir(client, cabecalho, novo_chamado)
    r = client.patch(f"/chamados/{chamado['id']}/status", json={"status": "resolvido"}, headers=cabecalho(CARLA, "tecnico"))
    assert r.status_code == 422


def test_solicitante_nao_muda_status_de_chamado_aberto(client, cabecalho, novo_chamado):
    chamado = _abrir(client, cabecalho, novo_chamado)
    r = client.patch(f"/chamados/{chamado['id']}/status", json={"status": "fechado"}, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 403


def test_solicitante_fecha_o_proprio_chamado_resolvido(client, cabecalho, novo_chamado, outros_servicos_no_ar):
    chamado = _abrir(client, cabecalho, novo_chamado)
    equipe = cabecalho(CARLA, "tecnico")
    client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=equipe)
    client.patch(f"/chamados/{chamado['id']}/status", json={"status": "resolvido"}, headers=equipe)
    r = client.patch(f"/chamados/{chamado['id']}/status", json={"status": "fechado"}, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 200 and r.json()["status"] == "fechado"


def test_comentario_usa_o_usuario_logado_e_fechado_nao_recebe(client, cabecalho, novo_chamado, outros_servicos_no_ar):
    chamado = _abrir(client, cabecalho, novo_chamado)
    r = client.post(f"/chamados/{chamado['id']}/comentarios", json={"texto": "Ainda sem vídeo."}, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 201 and r.json()["autor_id"] == ANA
    equipe = cabecalho(CARLA, "tecnico")
    client.patch(f"/chamados/{chamado['id']}/atribuir", json={"tecnico_id": 3}, headers=equipe)
    client.patch(f"/chamados/{chamado['id']}/status", json={"status": "resolvido"}, headers=equipe)
    client.patch(f"/chamados/{chamado['id']}/status", json={"status": "fechado"}, headers=equipe)
    r = client.post(f"/chamados/{chamado['id']}/comentarios", json={"texto": "Tarde demais."}, headers=cabecalho(ANA, "solicitante"))
    assert r.status_code == 422


def test_painel_conta_por_status(client, cabecalho, novo_chamado):
    _abrir(client, cabecalho, novo_chamado)
    _abrir(client, cabecalho, novo_chamado)
    painel = client.get("/chamados/painel", headers=cabecalho(CARLA, "tecnico")).json()
    assert painel["total"] == 2
    assert painel["por_status"] == {"aberto": 2}
    assert painel["atrasados"] == 0


def test_saude_responde_sem_token(client):
    r = client.get("/saude")
    assert r.status_code == 200 and r.json()["status"] == "ok"
