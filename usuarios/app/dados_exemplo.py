"""Usuários de exemplo (só entram se o banco estiver vazio). Senha de todos: Helpdesk2026.

ATENÇÃO: o serviço de Chamados cria chamados de exemplo que citam estes ids
(1 admin, 2 e 3 técnicos, 4 e 5 solicitantes). Não mude a ordem sem ajustar lá.
"""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.auth import senhas
from app.usuarios.modelos import Usuario

SENHA = "Helpdesk2026"
USUARIOS = [
    ("Admin do Sistema", "admin@empresa.com", "admin"),
    ("Carla Souza", "carla@empresa.com", "tecnico"),
    ("Bruno Lima", "bruno@empresa.com", "tecnico"),
    ("Ana Costa", "ana@empresa.com", "solicitante"),
    ("Diego Alves", "diego@empresa.com", "solicitante"),
]


def carregar(db: Session) -> None:
    if db.scalar(select(func.count(Usuario.id))):
        return
    for nome, email, perfil in USUARIOS:
        db.add(Usuario(nome=nome, email=email, perfil=perfil, senha_hash=senhas.gerar_hash(SENHA)))
    db.commit()
