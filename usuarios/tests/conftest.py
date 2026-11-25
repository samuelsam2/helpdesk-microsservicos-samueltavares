import os
import tempfile

# Estas variáveis precisam existir ANTES de importar o app
_pasta = tempfile.mkdtemp()
os.environ["JWT_SEGREDO"] = "segredo-so-para-testes-com-mais-de-32-caracteres"
os.environ["DATABASE_URL"] = f"sqlite:///{_pasta}/teste.db"
os.environ["DADOS_EXEMPLO"] = "0"

import pytest
from fastapi.testclient import TestClient

from app.auth import limite, tokens
from app.database import Base, SessionLocal, engine
from app.main import app
from app.usuarios import servico
from app.usuarios.esquemas import UsuarioCriar

SENHA = "Senha12345"


@pytest.fixture()
def senha():
    return SENHA


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    limite._falhas.clear()
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def criar_usuario():
    def _criar(nome="Fulano", email="fulano@empresa.com", perfil="solicitante"):
        with SessionLocal() as db:
            return servico.criar(db, UsuarioCriar(nome=nome, email=email, perfil=perfil, senha=SENHA))
    return _criar


@pytest.fixture()
def cabecalho():
    def _cabecalho(usuario_id, perfil):
        token, _ = tokens.criar(usuario_id, perfil)
        return {"Authorization": f"Bearer {token}"}
    return _cabecalho
