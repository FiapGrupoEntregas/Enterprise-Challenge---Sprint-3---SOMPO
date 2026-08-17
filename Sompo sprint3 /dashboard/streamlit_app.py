"""
AgroSafe Predictor - Sprint 3
Dashboard Integrado — consome o backend via API (não acessa o modelo/CSV direto)
Sompo Seguros | FIAP 1TIAOB

Executar (com o backend já rodando):
    streamlit run dashboard/streamlit_app.py
"""

import pandas as pd
import requests
import streamlit as st

API_URL = "http://localhost:8000"
API_KEY = "agrosafe-dev-key-2025"  # deve bater com AGROSAFE_API_KEY no backend
HEADERS = {"X-API-Key": API_KEY}

st.set_page_config(page_title="AgroSafe Predictor — Sprint 3", page_icon="🚜", layout="wide")

st.title("🚜 AgroSafe Predictor — Painel Integrado de Risco")
st.caption("Sompo Seguros | FIAP 1TIAOB — Sprint 3 (Backend + Banco + Modelo + Interface)")


@st.cache_data(ttl=5)
def get(endpoint: str, params: dict | None = None):
    try:
        resp = requests.get(f"{API_URL}{endpoint}", headers=HEADERS, params=params, timeout=5)
        resp.raise_for_status()
        return resp.json()
    except requests.exceptions.ConnectionError:
        return None
    except requests.exceptions.HTTPError:
        return {"erro": resp.status_code, "detalhe": resp.text}


health = get("/health")

if health is None:
    st.error(
        "❌ Não foi possível conectar ao backend em "
        f"`{API_URL}`. Rode `uvicorn backend.main:app --reload` em outro terminal e recarregue esta página."
    )
    st.stop()

if "erro" in (health or {}):
    st.error(f"Erro de autenticação com o backend: {health}")
    st.stop()

# ── Métricas principais ─────────────────────────────────────────
resumo = get("/resumo") or {"geral": {}, "por_equipamento": []}
geral = resumo.get("geral", {})
metricas_modelo = health.get("metricas_modelo", {})

col1, col2, col3, col4 = st.columns(4)
col1.metric("Registros processados", geral.get("total_registros", 0))
col2.metric("Alertas gerados", geral.get("total_alertas", 0))
col3.metric("Acurácia do modelo", f"{metricas_modelo.get('acuracia', 0) * 100:.1f}%")
col4.metric("Status do backend", "🟢 Online" if health.get("status") == "ok" else "🔴 Offline")

st.divider()

tab1, tab2, tab3, tab4 = st.tabs([
    "📊 Scores por Equipamento",
    "🚨 Alertas Recentes",
    "🗺️ Visão por Região",
    "📋 Registros Brutos",
])

with tab1:
    st.subheader("Ranking de Risco por Equipamento")
    dados_equip = resumo.get("por_equipamento", [])
    if dados_equip:
        df_equip = pd.DataFrame(dados_equip)
        st.dataframe(df_equip, use_container_width=True, hide_index=True)
        st.bar_chart(df_equip.set_index("id_equipamento")["score_medio"])
    else:
        st.info("Ainda não há registros processados. Rode `python simulate_ingestion.py` para simular telemetria.")

with tab2:
    st.subheader("Últimos Alertas Disparados (ALTO / CRÍTICO)")
    alertas = get("/alertas", {"limit": 30})
    if alertas and alertas.get("resultados"):
        df_alertas = pd.DataFrame(alertas["resultados"])
        st.dataframe(df_alertas, use_container_width=True, hide_index=True)
    else:
        st.success("✅ Nenhum alerta ativo no momento.")

with tab3:
    st.subheader("Distribuição de Scores por Região")
    scores = get("/scores", {"limit": 500})
    if scores and scores.get("resultados"):
        df_scores = pd.DataFrame(scores["resultados"])
        pivot = df_scores.groupby(["nome_regiao", "nivel_risco"]).size().unstack(fill_value=0)
        st.bar_chart(pivot)
    else:
        st.info("Sem dados suficientes ainda.")

with tab4:
    st.subheader("Últimos Registros de Telemetria + Score")
    scores = get("/scores", {"limit": 100})
    if scores and scores.get("resultados"):
        st.dataframe(pd.DataFrame(scores["resultados"]), use_container_width=True, hide_index=True)
    else:
        st.info("Sem registros ainda.")

st.divider()
st.caption(
    "Fluxo de ponta a ponta: entrada de telemetria (real/simulada) → API protegida por chave → "
    "persistência em banco relacional → modelo Random Forest (Sprint 2) → score e alerta → este painel."
)
