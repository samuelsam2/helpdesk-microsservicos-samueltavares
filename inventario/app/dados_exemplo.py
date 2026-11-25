"""Ativos de exemplo (só entram se o banco estiver vazio)."""
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.inventario.modelos import Ativo

ATIVOS = [
    ("PAT-0001", "notebook", "Notebook Dell Latitude 5420", "Financeiro"),
    ("PAT-0002", "computador", "Desktop HP ProDesk 400", "Recepção"),
    ("PAT-0003", "impressora", "Impressora HP LaserJet Pro", "Administrativo"),
    ("PAT-0004", "rede", "Switch 24 portas Cisco", "Sala de servidores"),
    ("PAT-0005", "notebook", "Notebook Lenovo ThinkPad E14", "Comercial"),
]


def carregar(db: Session) -> None:
    if db.scalar(select(func.count(Ativo.id))):
        return
    for patrimonio, tipo, descricao, setor in ATIVOS:
        db.add(Ativo(patrimonio=patrimonio, tipo=tipo, descricao=descricao, setor=setor))
    db.commit()
