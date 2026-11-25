"""Serviço de Inventário: este serviço NÃO tem banco de usuários, só confere o token."""
from datetime import datetime, timedelta, timezone

import jwt

from app.config import JWT_ALGORITMO, JWT_EMISSOR, JWT_SEGREDO


def _token(segredo=JWT_SEGREDO, expira_em=timedelta(minutes=10), perfil="tecnico"):
    agora = datetime.now(timezone.utc)
    dados = {"sub": "2", "perfil": perfil, "iat": agora, "exp": agora + expira_em, "iss": JWT_EMISSOR}
    return jwt.encode(dados, segredo, algorithm=JWT_ALGORITMO)


def test_sem_token_da_401(client):
    assert client.get("/ativos").status_code == 401
    assert client.get("/ativos/1").status_code == 401
    assert client.post("/ativos", json={}).status_code == 401


def test_token_invalido_da_401(client):
    assert client.get("/ativos", headers={"Authorization": "Bearer lixo"}).status_code == 401


def test_token_expirado_da_401(client):
    r = client.get("/ativos", headers={"Authorization": f"Bearer {_token(expira_em=timedelta(minutes=-5))}"})
    assert r.status_code == 401


def test_token_de_outro_segredo_da_401(client):
    r = client.get("/ativos", headers={"Authorization": f"Bearer {_token(segredo='outro-segredo-qualquer-com-mais-de-32-caracteres')}"})
    assert r.status_code == 401


def test_solicitante_nao_cria_ativo(client, cabecalho, ativo_valido):
    r = client.post("/ativos", json=ativo_valido, headers=cabecalho(4, "solicitante"))
    assert r.status_code == 403


def test_tecnico_cria_e_consulta_ativo(client, cabecalho, ativo_valido):
    criado = client.post("/ativos", json=ativo_valido, headers=cabecalho(2, "tecnico"))
    assert criado.status_code == 201
    ativo_id = criado.json()["id"]
    lido = client.get(f"/ativos/{ativo_id}", headers=cabecalho(4, "solicitante"))
    assert lido.status_code == 200
    assert lido.json()["patrimonio"] == "PAT-0100"


def test_patrimonio_repetido_da_422(client, cabecalho, ativo_valido):
    client.post("/ativos", json=ativo_valido, headers=cabecalho(2, "tecnico"))
    r = client.post("/ativos", json=ativo_valido, headers=cabecalho(2, "tecnico"))
    assert r.status_code == 422


def test_patrimonio_com_caracteres_invalidos_da_422(client, cabecalho, ativo_valido):
    ativo_valido["patrimonio"] = "PAT 01;--"
    r = client.post("/ativos", json=ativo_valido, headers=cabecalho(2, "tecnico"))
    assert r.status_code == 422


def test_campos_extras_sao_recusados(client, cabecalho, ativo_valido):
    ativo_valido["id"] = 999
    r = client.post("/ativos", json=ativo_valido, headers=cabecalho(2, "tecnico"))
    assert r.status_code == 422


def test_ativo_inexistente_da_404(client, cabecalho):
    assert client.get("/ativos/999", headers=cabecalho(2, "tecnico")).status_code == 404


def test_lista_filtra_por_setor(client, cabecalho, ativo_valido):
    client.post("/ativos", json=ativo_valido, headers=cabecalho(2, "tecnico"))
    outro = dict(ativo_valido, patrimonio="PAT-0101", setor="Recepção")
    client.post("/ativos", json=outro, headers=cabecalho(2, "tecnico"))
    todos = client.get("/ativos", headers=cabecalho(4, "solicitante")).json()
    so_recepcao = client.get("/ativos", params={"setor": "Recepção"}, headers=cabecalho(4, "solicitante")).json()
    assert len(todos) == 2
    assert [a["patrimonio"] for a in so_recepcao] == ["PAT-0101"]


def test_saude_responde_sem_token(client):
    r = client.get("/saude")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
