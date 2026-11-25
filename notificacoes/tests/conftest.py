import os
import tempfile

# Estas variáveis precisam existir ANTES de importar o app
_pasta = tempfile.mkdtemp()
os.environ["JWT_SEGREDO"] = "segredo-so-para-testes-com-mais-de-32-caracteres"
os.environ["DATABASE_URL"] = f"sqlite:///{_pasta}/teste.db"
os.environ["CONSUMIDOR"] = "0"  # nos testes não existe Redis

import pytest
from fastapi.testclient import TestClient

from app.auth import tokens
from app.database import Base, engine
from app.main import app


@pytest.fixture()
def client():
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)
    with TestClient(app) as c:
        yield c


@pytest.fixture()
def cabecalho():
    def _cabecalho(usuario_id, perfil="solicitante"):
        token, _ = tokens.criar(usuario_id, perfil)
        return {"Authorization": f"Bearer {token}"}
    return _cabecalho
