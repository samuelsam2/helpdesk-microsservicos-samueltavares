"""Serviço de Notificações: recebe eventos pela fila (Redis) e mostra os avisos de cada usuário."""
import os
import threading
from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.config import DOCS_ATIVA
from app.database import Base, engine
from app.erros import NaoEncontrado, RegraDeNegocio, SemPermissao
from app.notificacoes import consumidor
from app.notificacoes.rotas import router as notificacoes_router
from app.seguranca_http import CabecalhosDeSeguranca


@asynccontextmanager
async def ciclo_de_vida(app: FastAPI):
    Base.metadata.create_all(engine)
    parar = threading.Event()
    thread = None
    if os.getenv("CONSUMIDOR", "1") == "1":  # os testes desligam o consumidor
        thread = threading.Thread(target=consumidor.rodar, args=(parar,), name="consumidor", daemon=True)
        thread.start()
    yield
    parar.set()
    if thread:
        thread.join(timeout=5)


app = FastAPI(
    title="HelpDesk TI - Notificações", version="3.0.0", lifespan=ciclo_de_vida,
    docs_url="/docs" if DOCS_ATIVA else None, redoc_url=None,
    openapi_url="/openapi.json" if DOCS_ATIVA else None,
)
app.add_middleware(CabecalhosDeSeguranca)
app.include_router(notificacoes_router)


@app.exception_handler(NaoEncontrado)
def tratar_nao_encontrado(request: Request, erro: NaoEncontrado):
    return JSONResponse(status_code=404, content={"detail": str(erro)})


@app.exception_handler(RegraDeNegocio)
def tratar_regra(request: Request, erro: RegraDeNegocio):
    return JSONResponse(status_code=422, content={"detail": str(erro)})


@app.exception_handler(SemPermissao)
def tratar_sem_permissao(request: Request, erro: SemPermissao):
    return JSONResponse(status_code=403, content={"detail": str(erro)})


@app.get("/saude", tags=["Saúde"])
def saude():
    return {"status": "ok", "servico": "notificacoes"}
