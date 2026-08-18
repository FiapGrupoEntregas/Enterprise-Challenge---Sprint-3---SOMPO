"""
AgroSafe Predictor - Sprint 2
Modelo Preditivo de Risco Agrícola (Random Forest)
Sompo Seguros | FIAP 1TIAOB

Pipeline completo, organizado em funções reutilizáveis:
  1. Carregamento e preparação do dataset
  2. Treinamento (Random Forest Classifier) + validação cruzada
  3. Geração de figuras (retornadas em memória, sem salvar em disco)
  4. Função de predição individual

As figuras são retornadas como objetos matplotlib.Figure para que possam
ser consumidas tanto pelo dashboard Streamlit quanto pela execução via CLI.
A execução direta (python modelo_agrorisk.py) salva os gráficos em ./output
(diretório ignorado pelo Git).
"""

from pathlib import Path

import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import seaborn as sns
from sklearn.model_selection import train_test_split, cross_val_score
from sklearn.ensemble import RandomForestClassifier
from sklearn.preprocessing import LabelEncoder
from sklearn.metrics import (
    classification_report, confusion_matrix,
    accuracy_score, ConfusionMatrixDisplay,
)
import warnings

warnings.filterwarnings("ignore")

BASE_DIR = Path(__file__).resolve().parent
DATA_PATH = BASE_DIR / "data" / "agrorisk_dataset.csv"
OUTPUT_DIR = BASE_DIR / "output"

CORES = {
    "BAIXO":   "#2ecc71",
    "MEDIO":   "#f39c12",
    "ALTO":    "#e67e22",
    "CRITICO": "#e74c3c",
}

FEATURES = [
    "umidade_solo_pct",
    "inclinacao_lateral_graus",
    "precipitacao_3h_mm",
    "dist_corpo_agua_m",
    "velocidade_kmh",
    "temperatura_c",
    "horas_operacao_dia",
]
TARGET = "nivel_risco"
ORDEM = ["BAIXO", "MEDIO", "ALTO", "CRITICO"]


def configurar_visual():
    plt.rcParams["figure.facecolor"] = "white"
    plt.rcParams["axes.facecolor"] = "#f9f9f9"
    plt.rcParams["font.family"] = "DejaVu Sans"


def carregar_dados(path: Path = DATA_PATH) -> pd.DataFrame:
    return pd.read_csv(path, parse_dates=["timestamp"])


def preparar_dados(df: pd.DataFrame):
    X = df[FEATURES]
    le = LabelEncoder()
    le.classes_ = np.array(ORDEM)
    y_enc = le.transform(df[TARGET])
    return X, y_enc, le


def treinar(df: pd.DataFrame) -> dict:
    """Treina o Random Forest e retorna modelo, métricas e dados de teste."""
    X, y_enc, le = preparar_dados(df)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y_enc, test_size=0.2, random_state=42, stratify=y_enc
    )

    rf = RandomForestClassifier(
        n_estimators=200,
        max_depth=10,
        min_samples_leaf=5,
        class_weight="balanced",
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    cv_scores = cross_val_score(rf, X, y_enc, cv=5, scoring="accuracy")
    y_pred = rf.predict(X_test)
    acc = accuracy_score(y_test, y_pred)

    return {
        "modelo": rf,
        "le": le,
        "X_train": X_train,
        "X_test": X_test,
        "y_train": y_train,
        "y_test": y_test,
        "y_pred": y_pred,
        "acuracia": acc,
        "cv_scores": cv_scores,
        "relatorio": classification_report(
            y_test, y_pred, target_names=ORDEM, output_dict=True
        ),
        "relatorio_txt": classification_report(y_test, y_pred, target_names=ORDEM),
    }


def fig_matriz_confusao(y_test, y_pred):
    fig, ax = plt.subplots(figsize=(7, 5))
    cm = confusion_matrix(y_test, y_pred, labels=[0, 1, 2, 3])
    disp = ConfusionMatrixDisplay(confusion_matrix=cm, display_labels=ORDEM)
    disp.plot(ax=ax, colorbar=False, cmap="Blues")
    ax.set_title("Matriz de Confusão — AgroSafe Predictor",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Classe Prevista", fontsize=11)
    ax.set_ylabel("Classe Real", fontsize=11)
    fig.tight_layout()
    return fig


def fig_importancia(rf):
    importancias = pd.Series(rf.feature_importances_, index=FEATURES).sort_values()
    fig, ax = plt.subplots(figsize=(8, 5))
    cores_barras = ["#3498db" if v < importancias.median() else "#e74c3c"
                    for v in importancias.values]
    importancias.plot(kind="barh", ax=ax, color=cores_barras, edgecolor="white")
    ax.set_title("Importância das Variáveis no Modelo RF",
                 fontsize=13, fontweight="bold", pad=12)
    ax.set_xlabel("Importância (Gini)", fontsize=11)
    ax.axvline(importancias.median(), color="gray", linestyle="--",
               alpha=0.6, label="Mediana")
    ax.legend()
    fig.tight_layout()
    return fig


def fig_distribuicao(df: pd.DataFrame):
    fig, axes = plt.subplots(1, 2, figsize=(12, 5))

    axes[0].hist(df["score_risco"], bins=30, color="#3498db",
                 edgecolor="white", alpha=0.85)
    axes[0].axvline(35, color=CORES["MEDIO"], linestyle="--", linewidth=2, label="Médio (35)")
    axes[0].axvline(55, color=CORES["ALTO"], linestyle="--", linewidth=2, label="Alto (55)")
    axes[0].axvline(75, color=CORES["CRITICO"], linestyle="--", linewidth=2, label="Crítico (75)")
    axes[0].set_title("Distribuição do Score de Risco", fontsize=12, fontweight="bold")
    axes[0].set_xlabel("Score de Risco (0–100)")
    axes[0].set_ylabel("Frequência")
    axes[0].legend(fontsize=9)

    contagem = df["nivel_risco"].value_counts().reindex(ORDEM)
    wedge_colors = [CORES[n] for n in ORDEM]
    axes[1].pie(
        contagem.values,
        labels=ORDEM,
        colors=wedge_colors,
        autopct="%1.1f%%",
        startangle=140,
        textprops={"fontsize": 10},
    )
    axes[1].set_title("Proporção por Nível de Risco", fontsize=12, fontweight="bold")

    fig.suptitle("AgroSafe Predictor — Análise do Dataset",
                 fontsize=14, fontweight="bold", y=1.02)
    fig.tight_layout()
    return fig


def fig_correlacao(df: pd.DataFrame):
    fig, ax = plt.subplots(figsize=(9, 7))
    corr = df[FEATURES + ["score_risco"]].corr()
    mask = np.triu(np.ones_like(corr, dtype=bool))
    sns.heatmap(
        corr, mask=mask, annot=True, fmt=".2f", cmap="RdYlGn_r",
        center=0, vmin=-1, vmax=1, ax=ax,
        linewidths=0.5, linecolor="white",
    )
    ax.set_title("Mapa de Correlação entre Variáveis",
                 fontsize=13, fontweight="bold", pad=12)
    fig.tight_layout()
    return fig


def prever_risco(rf, umidade, inclinacao, chuva_3h, dist_agua,
                 velocidade=15, temperatura=28, horas_op=8):
    """Prevê o nível de risco para um equipamento em tempo real.

    Retorna: (score estimado, nível, alerta)
    """
    entrada = np.array([[umidade, inclinacao, chuva_3h, dist_agua,
                         velocidade, temperatura, horas_op]])
    pred_enc = rf.predict(entrada)[0]
    prob = rf.predict_proba(entrada)[0]
    nivel = ORDEM[pred_enc]
    score_est = int(prob[2] * 40 + prob[3] * 80 + prob[1] * 20 + prob[0] * 5)
    alerta = nivel in ("ALTO", "CRITICO")
    return score_est, nivel, alerta


def main():
    configurar_visual()
    print("=" * 60)
    print("  AgroSafe Predictor — Pipeline de Machine Learning")
    print("=" * 60)

    df = carregar_dados()
    print(f"\n📊 Dataset carregado: {df.shape[0]} registros | {df.shape[1]} colunas")
    print("\nDistribuição do target (nivel_risco):")
    print(df["nivel_risco"].value_counts().to_string())

    res = treinar(df)
    print(f"\n✂️  Split: {len(res['X_train'])} treino | {len(res['X_test'])} teste")
    print("\n✅ Modelo treinado!")

    cv = res["cv_scores"]
    print("\n📐 Validação Cruzada (5-fold):")
    print(f"   Acurácia média : {cv.mean():.3f} ± {cv.std():.3f}")
    print(f"   Scores por fold: {[round(s, 3) for s in cv]}")

    acc = res["acuracia"]
    print(f"\n🎯 Acurácia no conjunto de teste: {acc:.3f} ({acc * 100:.1f}%)")
    print("\n📋 Relatório de Classificação:")
    print(res["relatorio_txt"])

    OUTPUT_DIR.mkdir(exist_ok=True)
    figuras = {
        "matriz_confusao.png": fig_matriz_confusao(res["y_test"], res["y_pred"]),
        "importancia_variaveis.png": fig_importancia(res["modelo"]),
        "distribuicao_scores.png": fig_distribuicao(df),
        "correlacao_variaveis.png": fig_correlacao(df),
    }
    for nome, fig in figuras.items():
        fig.savefig(OUTPUT_DIR / nome, dpi=150)
        plt.close(fig)
        print(f"📁 Salvo: output/{nome}")

    print("\n" + "=" * 60)
    print("  EXEMPLO DE PREDIÇÃO EM TEMPO REAL")
    print("=" * 60)
    cenarios = [
        ("Solo saturado, próximo ao rio", 85, 5, 35, 45),
        ("Inclinação alta, chuva moderada", 50, 22, 18, 400),
        ("Condição segura", 30, 3, 2, 800),
        ("Situação crítica combinada", 90, 28, 50, 30),
    ]
    for desc, umid, incl, chuva, dist in cenarios:
        score, nivel, alerta = prever_risco(res["modelo"], umid, incl, chuva, dist)
        emoji = "🔴" if nivel == "CRITICO" else "🟠" if nivel == "ALTO" else "🟡" if nivel == "MEDIO" else "🟢"
        print(f"\n  {emoji} {desc}")
        print(f"     Nível: {nivel} | Score estimado: ~{score} | Alerta: {'✅ SIM' if alerta else '❌ NÃO'}")

    print("\n\n✅ Pipeline completo executado com sucesso!")
    print(f"   Acurácia final: {acc * 100:.1f}%")


if __name__ == "__main__":
    main()
