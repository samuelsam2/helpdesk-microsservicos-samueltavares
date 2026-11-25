import os
import tempfile

# Estas variáveis precisam existir ANTES de importar o app
_pasta = tempfile.mkdtemp()
os.environ["JWT_SEGREDO"] = "segredo-so-para-testes-com-mais-de-32-caracteres"
os.environ["DATABASE_URL"] = f"sqlite:///{_pasta}/teste.db"
os.environ["DADOS_EXEMPLO"] = "0"

import pytest
from fastapi.testclient import TestClient

from app.auth import tokens
from app.chamados import clientes, notificacoes
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
    def _cabecalho(usuario_id, perfil):
        token, _ = tokens.criar(usuario_id, perfil)
        return {"Authorization": f"Bearer {token}"}
    return _cabecalho


@pytest.fixture()
def outros_servicos_no_ar(monkeypatch):
    """Finge que Usuários e Inventário respondem (nos testes não existe rede)."""
    monkeypatch.setattr(clientes, "obter_ativo", lambda ativo_id, token: {"id": ativo_id})
    monkeypatch.setattr(
        clientes, "obter_tecnico", lambda usuario_id, token: {"id": usuario_id, "nome": "Tecnico", "perfil": "tecnico"}
    )


@pytest.fixture()
def novo_chamado():
    return {"titulo": "Notebook não liga", "descricao": "Não dá sinal de vídeo.", "prioridade": "alta"}


class FilaFalsa:
    def __init__(self):
        self.itens = []

    def lpush(self, fila, corpo):
        self.itens.append(corpo)


@pytest.fixture(autouse=True)
def fila(monkeypatch):
    """Nos testes não existe Redis: os eventos vão para esta lista."""
    falsa = FilaFalsa()
    monkeypatch.setattr(notificacoes, "_obter_cliente", lambda: falsa)
    return falsa
