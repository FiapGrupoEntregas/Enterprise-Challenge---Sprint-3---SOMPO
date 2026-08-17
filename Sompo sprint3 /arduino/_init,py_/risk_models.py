"""
AgroSafe Predictor - Sprint 3
Camada de integração com o modelo preditivo (Sprint 2).
Sompo Seguros | FIAP 1TIAOB

Encapsula treino/carregamento do Random Forest em um único ponto,
para ser acionado pelo backend a cada novo registro de telemetria.
"""

import pickle
import logging

import pandas as pd

from backend.config import DATASET_PATH, MODEL_CACHE_PATH, MODEL_VERSAO
from backend.config import NIVEL_ALERTA

import modelo_agrorisk as ml

logger = logging.getLogger("agrosafe.risk_model")

_estado = {"modelo": None, "le": None, "metricas": None}


def carregar_ou_treinar():
    """Carrega o modelo do cache em disco, ou treina e salva um novo."""
    if MODEL_CACHE_PATH.exists():
        try:
            with open(MODEL_CACHE_PATH, "rb") as f:
                cache = pickle.load(f)
            _estado["modelo"] = cache["modelo"]
            _estado["le"] = cache["le"]
            _estado["metricas"] = cache["metricas"]
            logger.info("Modelo carregado do cache (%s)", MODEL_CACHE_PATH)
            return
        except Exception:
            logger.warning("Falha ao carregar cache, retreinando modelo.")

    df = pd.read_csv(DATASET_PATH, parse_dates=["timestamp"])
    resultado = ml.treinar(df)
    _estado["modelo"] = resultado["modelo"]
    _estado["le"] = resultado["le"]
    _estado["metricas"] = {
        "acuracia": resultado["acuracia"],
        "cv_media": float(resultado["cv_scores"].mean()),
        "cv_desvio": float(resultado["cv_scores"].std()),
    }

    MODEL_CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    with open(MODEL_CACHE_PATH, "wb") as f:
        pickle.dump(
            {"modelo": _estado["modelo"], "le": _estado["le"], "metricas": _estado["metricas"]},
            f,
        )
    logger.info(
        "Modelo treinado e cacheado. Acurácia teste=%.3f | CV=%.3f±%.3f",
        _estado["metricas"]["acuracia"],
        _estado["metricas"]["cv_media"],
        _estado["metricas"]["cv_desvio"],
    )


def modelo_pronto() -> bool:
    return _estado["modelo"] is not None


def metricas_modelo() -> dict:
    return _estado["metricas"] or {}


def prever(dados: dict) -> dict:
    """Aciona o modelo treinado na Sprint 2 e retorna score/nível/alerta."""
    if not modelo_pronto():
        carregar_ou_treinar()

    score, nivel, _ = ml.prever_risco(
        _estado["modelo"],
        umidade=dados["umidade_solo_pct"],
        inclinacao=dados["inclinacao_lateral_graus"],
        chuva_3h=dados["precipitacao_3h_mm"],
        dist_agua=dados["dist_corpo_agua_m"],
        velocidade=dados.get("velocidade_kmh", 15),
        temperatura=dados.get("temperatura_c", 28),
        horas_op=dados.get("horas_operacao_dia", 8),
    )
    alerta = nivel in NIVEL_ALERTA
    return {
        "score_risco": int(score),
        "nivel_risco": nivel,
        "alerta_ativo": alerta,
        "modelo_versao": MODEL_VERSAO,
    }
