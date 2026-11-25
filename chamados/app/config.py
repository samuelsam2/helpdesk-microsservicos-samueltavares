"""Configurações lidas das variáveis de ambiente (vêm do .env, nunca do código)."""
import os

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./servico.db")

# O MESMO segredo precisa estar em todos os serviços, senão um não valida o token do outro.
JWT_SEGREDO = os.getenv("JWT_SEGREDO") or ""
if len(JWT_SEGREDO) < 32:
    raise RuntimeError("Defina JWT_SEGREDO (32 caracteres ou mais) no arquivo .env")

JWT_ALGORITMO = "HS256"
JWT_EMISSOR = "helpdesk-ti"
TOKEN_MINUTOS = int(os.getenv("TOKEN_MINUTOS", "60"))

LOGIN_MAX_FALHAS = int(os.getenv("LOGIN_MAX_FALHAS", "5"))
LOGIN_JANELA_SEGUNDOS = int(os.getenv("LOGIN_JANELA_SEGUNDOS", "300"))

DOCS_ATIVA = os.getenv("DOCS", "0") == "1"

# Usados só pelo serviço de Chamados (dentro do Docker Compose, chamamos pelo nome do serviço)
USUARIOS_URL = os.getenv("USUARIOS_URL", "http://usuarios:8000")
INVENTARIO_URL = os.getenv("INVENTARIO_URL", "http://inventario:8000")
TIMEOUT_SEGUNDOS = float(os.getenv("TIMEOUT_SEGUNDOS", "3"))

# Fila de eventos (Redis). Chamados só escreve nela; quem lê é o serviço de Notificações.
REDIS_URL = os.getenv("REDIS_URL", "redis://redis:6379/0")
FILA_EVENTOS = os.getenv("FILA_EVENTOS", "eventos_chamados")
