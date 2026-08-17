"""
AgroSafe Predictor - Sprint 3
Backend Integrador (FastAPI)
Sompo Seguros | FIAP 1TIAOB

Orquestra o fluxo de ponta a ponta:
  entrada de telemetria -> persistência -> modelo de risco -> score/alerta -> saída

Executar:
    uvicorn backend.main:app --reload
Docs interativas (Swagger):
    http://localhost:8000/docs
"""

import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware

from backend import database, risk_model
from backend.models import ScoreSaida, TelemetriaEntrada
from backend.security import exigir_api_key

logging.basicConfig(level=logging.INFO, format="%(asctime)s | %(levelname)s | %(name)s | %(message)s")
logger = logging.getLogger("agrosafe.main")


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Inicializando AgroSafe Predictor — Backend Integrador")
    database.init_db()
    risk_model.carregar_ou_treinar()
    logger.info("Backend pronto.")
    yield
    logger.info("Encerrando backend.")


app = FastAPI(
    title="AgroSafe Predictor — Backend Integrador",
    description="Orquestra a entrada de telemetria, o banco de dados, o modelo de risco e a saída para o usuário.",
    version="1.0.0-sprint3",
    lifespan=lifespan,
)

# CORS liberado para o dashboard local consumir a API (ajustar em produção)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def log_requisicoes(request: Request, call_next):
    """Tratamento básico de exceções + log de toda requisição (rastreabilidade)."""
    try:
        response = await call_next(request)
    except Exception as exc:  # noqa: BLE001 - queremos capturar qualquer falha do fluxo
        logger.exception("Erro não tratado em %s", request.url.path)
        database.registrar_log(request.url.path, request.method, "sistema", 500, str(exc))
        raise HTTPException(status_code=500, detail="Erro interno ao processar a requisição.") from exc
    return response


# ── Endpoints públicos (health check) ──────────────────────────────

@app.get("/")
def raiz():
    return {
        "servico": "AgroSafe Predictor — Backend Integrador",
        "status": "online",
        "docs": "/docs",
    }


@app.get("/health")
def health():
    return {
        "status": "ok",
        "modelo_pronto": risk_model.modelo_pronto(),
        "metricas_modelo": risk_model.metricas_modelo(),
    }


# ── Endpoints protegidos (exigem X-API-Key) ────────────────────────

@app.post("/telemetria", response_model=ScoreSaida, status_code=201)
def receber_telemetria(payload: TelemetriaEntrada, cliente_id: str = Depends(exigir_api_key)):
    """
    Ponto único de entrada do fluxo integrado:
    1) valida os dados recebidos (Pydantic)
    2) persiste a telemetria no banco
    3) aciona o modelo de risco (Sprint 2)
    4) persiste o score/alerta gerado
    5) retorna o resultado ao cliente (operador, gestor, analista)
    """
    dados = payload.model_dump()

    with database.get_conn() as conn:
        id_registro = database.inserir_telemetria(conn, dados)

    resultado = risk_model.prever(dados)

    with database.get_conn() as conn:
        id_score = database.inserir_score(
            conn,
            id_registro=id_registro,
            score=resultado["score_risco"],
            nivel=resultado["nivel_risco"],
            alerta=resultado["alerta_ativo"],
            modelo_versao=resultado["modelo_versao"],
        )

    mensagem = (
        f"Risco {resultado['nivel_risco']} — alerta recomendado ao gestor/operador."
        if resultado["alerta_ativo"]
        else "Operação dentro dos parâmetros seguros."
    )

    database.registrar_log(
        "/telemetria", "POST", cliente_id, 201,
        f"equip={dados['id_equipamento']} nivel={resultado['nivel_risco']}",
    )

    return ScoreSaida(
        id_registro=id_registro,
        id_score=id_score,
        id_equipamento=dados["id_equipamento"],
        regiao=dados["regiao"],
        mensagem=mensagem,
        **resultado,
    )


@app.get("/scores")
def obter_scores(
    limit: int = 100,
    equipamento: str | None = None,
    regiao: str | None = None,
    cliente_id: str = Depends(exigir_api_key),
):
    """Retorna os scores de risco mais recentes, com filtros opcionais."""
    resultado = database.listar_scores(limit=limit, equipamento=equipamento, regiao=regiao)
    database.registrar_log("/scores", "GET", cliente_id, 200, f"{len(resultado)} registros")
    return {"total": len(resultado), "resultados": resultado}


@app.get("/alertas")
def obter_alertas(limit: int = 50, cliente_id: str = Depends(exigir_api_key)):
    """Retorna o histórico de alertas disparados (ALTO/CRÍTICO)."""
    resultado = database.listar_alertas(limit=limit)
    database.registrar_log("/alertas", "GET", cliente_id, 200, f"{len(resultado)} alertas")
    return {"total": len(resultado), "resultados": resultado}


@app.get("/resumo")
def obter_resumo(cliente_id: str = Depends(exigir_api_key)):
    """Painel resumido: contagens gerais + ranking de risco por equipamento."""
    geral = database.contagem_geral()
    por_equipamento = database.resumo_por_equipamento()
    database.registrar_log("/resumo", "GET", cliente_id, 200, "")
    return {"geral": geral, "por_equipamento": por_equipamento}
