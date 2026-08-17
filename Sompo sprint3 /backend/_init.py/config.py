"""
AgroSafe Predictor - Sprint 3
Configuração central do backend integrador.
Sompo Seguros | FIAP 1TIAOB
"""

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent

# ── Banco de dados ────────────────────────────────────────────────
# SQLite para o protótipo/MVP (zero setup). Em produção, trocar a
# connection string por PostgreSQL sem alterar o restante do código
# (o módulo database.py usa apenas SQL padrão / parametrizado).
DB_PATH = BASE_DIR / "data" / "agrosafe.db"

# ── Dados de treino do modelo ─────────────────────────────────────
DATASET_PATH = BASE_DIR / "data" / "agrorisk_dataset.csv"
MODEL_CACHE_PATH = BASE_DIR / "data" / "modelo_rf.pkl"

# ── Segurança ──────────────────────────────────────────────────────
# Chave de API lida de variável de ambiente. Valor padrão SOMENTE
# para desenvolvimento local — nunca usar em produção.
API_KEY = os.getenv("AGROSAFE_API_KEY", "agrosafe-dev-key-2025")

# Limite simples de requisições por cliente (janela deslizante, em memória)
RATE_LIMIT_MAX_REQUESTS = int(os.getenv("AGROSAFE_RATE_LIMIT", "120"))
RATE_LIMIT_WINDOW_SECONDS = 60

# ── Alertas ────────────────────────────────────────────────────────
NIVEL_ALERTA = {"ALTO", "CRITICO"}

MODEL_VERSAO = "v1.0-sprint3"
