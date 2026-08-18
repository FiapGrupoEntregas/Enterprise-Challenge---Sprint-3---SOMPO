"""
AgroSafe Predictor - Sprint 3
Simulador de Fontes de Dados (Integração com Fontes)
Sompo Seguros | FIAP 1TIAOB

Simula sensores IoT embarcados, API de clima e GPS/GIS enviando
telemetria em tempo real para o backend via HTTP (POST /telemetria),
validando o caminho de ponta a ponta: entrada -> banco -> modelo -> saída.

Executar (com o backend já rodando em outro terminal):
    python simulate_ingestion.py --n 30 --intervalo 0.5
"""

import argparse
import random
import time

import requests

API_URL = "http://localhost:8000"
API_KEY = "agrosafe-dev-key-2025"  # deve bater com AGROSAFE_API_KEY no backend

EQUIPAMENTOS = [f"EQ-{str(i).zfill(3)}" for i in range(1, 21)]
REGIOES = ["Cerrado-MT", "Soja-PR", "Cana-SP", "Arroz-RS", "Milho-GO"]


def gerar_leitura_sensor() -> dict:
    """Simula uma leitura combinada de sensores de solo, giroscópio, API de
    clima e GPS/GIS para um equipamento em operação — com chance de gerar
    cenários de risco elevado, para exercitar o fluxo de alertas."""
    cenario_critico = random.random() < 0.2

    if cenario_critico:
        umidade = random.uniform(75, 100)
        inclinacao = random.uniform(18, 45)
        chuva = random.uniform(20, 80)
        dist_agua = random.uniform(10, 250)
    else:
        umidade = random.uniform(20, 70)
        inclinacao = random.uniform(0, 15)
        chuva = random.uniform(0, 15)
        dist_agua = random.uniform(300, 1500)

    return {
        "id_equipamento": random.choice(EQUIPAMENTOS),
        "regiao": random.choice(REGIOES),
        "umidade_solo_pct": round(umidade, 1),
        "inclinacao_lateral_graus": round(inclinacao, 1),
        "precipitacao_3h_mm": round(chuva, 1),
        "dist_corpo_agua_m": round(dist_agua, 0),
        "velocidade_kmh": round(random.uniform(0, 35), 1),
        "temperatura_c": round(random.uniform(15, 40), 1),
        "horas_operacao_dia": round(random.uniform(1, 13), 1),
        "origem": "SENSOR_IOT_SIMULADO",
    }


def enviar(payload: dict) -> dict | None:
    headers = {"X-API-Key": API_KEY}
    try:
        resp = requests.post(f"{API_URL}/telemetria", json=payload, headers=headers, timeout=5)
    except requests.exceptions.ConnectionError:
        print("❌ Não foi possível conectar ao backend. Ele está rodando? (uvicorn backend.main:app --reload)")
        return None

    if resp.status_code == 201:
        r = resp.json()
        emoji = "🔴" if r["nivel_risco"] == "CRITICO" else "🟠" if r["nivel_risco"] == "ALTO" else "🟡" if r["nivel_risco"] == "MEDIO" else "🟢"
        print(f"{emoji} {r['id_equipamento']} @ {r['regiao']:10s} | score={r['score_risco']:3d} | "
              f"nível={r['nivel_risco']:8s} | alerta={'SIM' if r['alerta_ativo'] else 'não'}")
        return r
    else:
        print(f"⚠️  Falha ({resp.status_code}): {resp.text}")
        return None


def main():
    parser = argparse.ArgumentParser(description="Simulador de fontes de telemetria — AgroSafe Predictor")
    parser.add_argument("--n", type=int, default=20, help="Número de leituras a simular")
    parser.add_argument("--intervalo", type=float, default=0.3, help="Segundos entre leituras")
    args = parser.parse_args()

    print("=" * 70)
    print("  AgroSafe Predictor — Simulador de Fontes de Dados")
    print(f"  Enviando {args.n} leituras simuladas para {API_URL}/telemetria")
    print("=" * 70)

    sucesso = 0
    for i in range(args.n):
        payload = gerar_leitura_sensor()
        resultado = enviar(payload)
        if resultado:
            sucesso += 1
        time.sleep(args.intervalo)

    print("\n" + "=" * 70)
    print(f"  Concluído: {sucesso}/{args.n} leituras processadas com sucesso.")
    print("=" * 70)


if __name__ == "__main__":
    main()
