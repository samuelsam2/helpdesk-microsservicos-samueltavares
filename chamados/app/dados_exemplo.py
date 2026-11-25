"""Chamados de exemplo (só entram se o banco estiver vazio).

Os ids de usuário e de ativo abaixo vêm dos dados de exemplo dos outros serviços:
usuários 2 e 3 são técnicos, 4 e 5 são solicitantes; ativos 1 a 5.
"""
from datetime import datetime, timedelta

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.chamados.modelos import Chamado
from app.chamados.servico import calcular_prazo

# (título, descrição, prioridade, status, solicitante, técnico, ativo, horas atrás)
CHAMADOS = [
    ("Notebook não liga", "O notebook não dá sinal de vídeo ao ligar.", "alta", "aberto", 4, None, 1, 1),
    ("Impressora sem imprimir", "A fila de impressão trava em todos os documentos.", "media", "em_atendimento", 4, 2, 3, 5),
    ("Sem acesso à rede", "A sala inteira está sem internet desde cedo.", "critica", "em_atendimento", 5, 3, 4, 30),
    ("Instalar um programa", "Preciso do editor de planilhas instalado.", "baixa", "resolvido", 5, 2, None, 10),
]


def carregar(db: Session) -> None:
    if db.scalar(select(func.count(Chamado.id))):
        return
    agora = datetime.now()
    for titulo, descricao, prioridade, status, solicitante, tecnico, ativo, horas in CHAMADOS:
        criado = agora - timedelta(hours=horas)
        db.add(Chamado(
            titulo=titulo, descricao=descricao, prioridade=prioridade, status=status,
            solicitante_id=solicitante, tecnico_id=tecnico, ativo_id=ativo,
            criado_em=criado, prazo_sla=calcular_prazo(prioridade, criado),
        ))
    db.commit()
