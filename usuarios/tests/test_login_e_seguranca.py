"""Serviço de Usuários: login, token e permissões (testes de segurança adaptados do monólito)."""
from datetime import datetime, timedelta, timezone

import jwt

from app.config import JWT_ALGORITMO, JWT_EMISSOR, JWT_SEGREDO, LOGIN_MAX_FALHAS
from app.database import SessionLocal
from app.usuarios.modelos import Usuario


def _token(segredo=JWT_SEGREDO, algoritmo=JWT_ALGORITMO, expira_em=timedelta(minutes=10), sub="1"):
    agora = datetime.now(timezone.utc)
    dados = {"sub": sub, "perfil": "admin", "iat": agora, "exp": agora + expira_em, "iss": JWT_EMISSOR}
    return jwt.encode(dados, segredo, algorithm=algoritmo)


def test_login_correto_devolve_token_sem_expor_senha(client, criar_usuario, senha):
    criar_usuario(email="ana@empresa.com")
    r = client.post("/auth/login", json={"email": "ana@empresa.com", "senha": senha})
    assert r.status_code == 200
    corpo = r.json()
    assert corpo["access_token"]
    assert corpo["usuario"]["email"] == "ana@empresa.com"
    assert "senha" not in str(corpo).lower().replace("senha_", "")  # nenhum hash na resposta
    assert "senha_hash" not in corpo["usuario"]


def test_senha_errada_da_401(client, criar_usuario):
    criar_usuario(email="ana@empresa.com")
    r = client.post("/auth/login", json={"email": "ana@empresa.com", "senha": "errada123"})
    assert r.status_code == 401


def test_email_inexistente_da_a_mesma_resposta(client, criar_usuario):
    criar_usuario(email="ana@empresa.com")
    certo = client.post("/auth/login", json={"email": "ana@empresa.com", "senha": "errada123"})
    falso = client.post("/auth/login", json={"email": "ninguem@empresa.com", "senha": "errada123"})
    assert falso.status_code == 401
    assert falso.json() == certo.json()  # não revela se o e-mail existe


def test_muitas_tentativas_bloqueiam_o_login(client, criar_usuario, senha):
    criar_usuario(email="ana@empresa.com")
    for _ in range(LOGIN_MAX_FALHAS):
        assert client.post("/auth/login", json={"email": "ana@empresa.com", "senha": "errada123"}).status_code == 401
    r = client.post("/auth/login", json={"email": "ana@empresa.com", "senha": senha})
    assert r.status_code == 429


def test_rotas_protegidas_sem_token_dao_401(client):
    assert client.get("/usuarios").status_code == 401
    assert client.get("/usuarios/1").status_code == 401
    assert client.get("/auth/eu").status_code == 401
    assert client.post("/usuarios", json={}).status_code == 401


def test_token_invalido_da_401(client):
    r = client.get("/auth/eu", headers={"Authorization": "Bearer isto-nao-e-um-token"})
    assert r.status_code == 401


def test_token_expirado_da_401(client, criar_usuario):
    criar_usuario()
    r = client.get("/auth/eu", headers={"Authorization": f"Bearer {_token(expira_em=timedelta(minutes=-5))}"})
    assert r.status_code == 401


def test_token_assinado_com_outro_segredo_da_401(client, criar_usuario):
    criar_usuario()
    r = client.get("/auth/eu", headers={"Authorization": f"Bearer {_token(segredo='outro-segredo-qualquer-com-mais-de-32-caracteres')}"})
    assert r.status_code == 401


def test_token_sem_assinatura_alg_none_da_401(client, criar_usuario):
    criar_usuario()
    agora = datetime.now(timezone.utc)
    dados = {"sub": "1", "perfil": "admin", "iat": agora, "exp": agora + timedelta(minutes=10), "iss": JWT_EMISSOR}
    falso = jwt.encode(dados, None, algorithm="none")
    r = client.get("/auth/eu", headers={"Authorization": f"Bearer {falso}"})
    assert r.status_code == 401


def test_token_valido_funciona(client, criar_usuario, cabecalho):
    usuario = criar_usuario()
    r = client.get("/auth/eu", headers=cabecalho(usuario.id, "solicitante"))
    assert r.status_code == 200
    assert r.json()["id"] == usuario.id


def test_usuario_desativado_nao_passa_mesmo_com_token(client, criar_usuario, cabecalho):
    usuario = criar_usuario()
    with SessionLocal() as db:
        u = db.get(Usuario, usuario.id)
        u.ativo = False
        db.commit()
    r = client.get("/auth/eu", headers=cabecalho(usuario.id, "solicitante"))
    assert r.status_code == 401


def test_solicitante_nao_cria_usuario(client, criar_usuario, cabecalho):
    usuario = criar_usuario()
    novo = {"nome": "Novo", "email": "novo@empresa.com", "perfil": "admin", "senha": "Senha12345"}
    r = client.post("/usuarios", json=novo, headers=cabecalho(usuario.id, "solicitante"))
    assert r.status_code == 403


def test_admin_cria_usuario_e_a_resposta_nao_traz_hash(client, criar_usuario, cabecalho):
    admin = criar_usuario(email="admin@empresa.com", perfil="admin")
    novo = {"nome": "Novo", "email": "novo@empresa.com", "perfil": "solicitante", "senha": "Senha12345"}
    r = client.post("/usuarios", json=novo, headers=cabecalho(admin.id, "admin"))
    assert r.status_code == 201
    assert "senha_hash" not in r.json()
    assert "senha" not in r.json()


def test_email_repetido_da_422(client, criar_usuario, cabecalho):
    admin = criar_usuario(email="admin@empresa.com", perfil="admin")
    novo = {"nome": "Outro", "email": "admin@empresa.com", "perfil": "solicitante", "senha": "Senha12345"}
    r = client.post("/usuarios", json=novo, headers=cabecalho(admin.id, "admin"))
    assert r.status_code == 422


def test_senha_so_com_letras_e_recusada(client, criar_usuario, cabecalho):
    admin = criar_usuario(email="admin@empresa.com", perfil="admin")
    novo = {"nome": "Novo", "email": "novo@empresa.com", "perfil": "solicitante", "senha": "apenasletras"}
    r = client.post("/usuarios", json=novo, headers=cabecalho(admin.id, "admin"))
    assert r.status_code == 422


def test_dados_publicos_nao_mostram_email(client, criar_usuario, cabecalho):
    usuario = criar_usuario(email="ana@empresa.com")
    r = client.get(f"/usuarios/{usuario.id}", headers=cabecalho(usuario.id, "solicitante"))
    assert r.status_code == 200
    assert set(r.json()) == {"id", "nome", "perfil"}


def test_usuario_inexistente_da_404(client, criar_usuario, cabecalho):
    usuario = criar_usuario()
    r = client.get("/usuarios/999", headers=cabecalho(usuario.id, "solicitante"))
    assert r.status_code == 404


def test_saude_responde_sem_token(client):
    r = client.get("/saude")
    assert r.status_code == 200
    assert r.json()["status"] == "ok"
