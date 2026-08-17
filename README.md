# 🚜 AgroSafe Predictor — Sprint 3: Integração e MVP Funcional

**Challenge Sompo Seguros | FIAP 1TIAOB**

## 👥 Identificação do Grupo
| Nome | RM | Turma |
|---|---|---|
| Jonattas Felipe | 572692 | 1TIAOB |
| Bruna | 573509 | 1TIAOB |
| Kaio | 573402 | 1TIAOB |
| Natanael | 572474 | 1TIAOB |

📧 Contato: rm572692@fiap.com.br

🎥 **Vídeo de apresentação — Sprint 3:** *[adicionar link aqui após gravação — configurar como "não listado" no YouTube]*

---

## 📌 Evolução em Relação à Sprint 2

| Aspecto | Sprint 2 | Sprint 3 |
|---|---|---|
| Modelo | Script isolado (`modelo_agrorisk.py`) executado manualmente | Modelo acionado automaticamente pelo backend a cada novo dado |
| Banco de dados | Schema SQL documentado, sem persistência automatizada | Persistência real via backend (SQLite, schema idêntico ao da Sprint 2) |
| Entrada de dados | Dataset estático (CSV) | Endpoint HTTP (`POST /telemetria`) recebendo dados simulados em tempo real |
| Segurança | Constraints de integridade no SQL | + Autenticação por API Key, rate limiting e log de auditoria (`log_uso`) |
| Interface | Dashboard lia o CSV e treinava o modelo localmente | Dashboard consome a API do backend (arquitetura desacoplada) |
| Integração | Componentes isolados | Fluxo de ponta a ponta funcional: entrada → banco → modelo → saída |

Este é o MVP com ~60% da solução completa em funcionamento, conforme escopo da Sprint 3: o caminho de ponta a ponta está fechado e demonstrável, com foco em robustez da integração mais do que em sofisticação visual.

---

## 🧩 Arquitetura da Solução

```
┌──────────────────────────────────────────────────────────────────────┐
│                 AGROSAFE PREDICTOR — Sprint 3                        │
│                                                                      │
│   [Sensores IoT]      [API Clima]      [GPS/GIS]                     │
│         │                  │                │                        │
│         └──────────────────┴────────────────┘                        │
│                            │  (simulate_ingestion.py)                │
│                            ▼                                         │
│                 ┌────────────────────┐                               │
│                 │   POST /telemetria │  ← autenticado (X-API-Key)    │
│                 │   Backend FastAPI  │  ← rate limit + log de uso    │
│                 │  (backend/main.py) │                               │
│                 └──────────┬─────────┘                               │
│                            │                                         │
│              ┌─────────────┼──────────────┐                          │
│              ▼                            ▼                          │
│   ┌─────────────────────┐       ┌────────────────────────┐           │
│   │  Banco (SQLite)      │      │  Modelo de Risco       │           │
│   │  backend/database.py │◄────►│  Random Forest (Sprint 2)│         │
│   │  telemetria, scores, │      │  backend/risk_model.py │           │
│   │  alertas, log_uso    │      └────────────────────────┘           │
│   └──────────┬───────────┘                                           │
│              │                                                       │
│              ▼                                                       │
│   ┌─────────────────────────────┐                                    │
│   │ GET /scores /alertas /resumo│                                    │
│   └──────────────┬──────────────┘                                    │
│                  ▼                                                   │
│   ┌─────────────────────────────┐                                    │
│   │  Dashboard (Streamlit)      │  → gestor de frota / operador      │
│   │  dashboard/streamlit_app.py │  → analista Sompo                  │
│   └─────────────────────────────┘                                    │
└──────────────────────────────────────────────────────────────────────┘
```

**Fluxo de ponta a ponta:** um dado de telemetria (real ou simulado) chega via HTTP → é validado e persistido no banco → aciona o modelo Random Forest treinado na Sprint 2 → gera score de risco e, se necessário, um alerta → tudo fica disponível no dashboard para o operador, gestor de frota ou analista da seguradora.

---

## 📂 Estrutura do Repositório

```
sompo-sprint3/
│
├── backend/
│   ├── main.py            # Orquestrador FastAPI (endpoints, fluxo integrado)
│   ├── database.py         # Engenharia de dados: schema + persistência (SQLite)
│   ├── risk_model.py        # Integração com o modelo de risco (Sprint 2)
│   ├── security.py          # Autenticação por API Key + rate limiting + log
│   ├── models.py             # Schemas Pydantic (validação de entrada/saída)
│   └── config.py              # Configurações centrais (chave de API, caminhos)
│
├── dashboard/
│   └── streamlit_app.py        # Interface simples — consome a API do backend
│
├── modelo_agrorisk.py            # Pipeline ML da Sprint 2 (reutilizado sem alterações no núcleo)
├── simulate_ingestion.py          # Simulador de fontes (sensores IoT, API clima, GPS/GIS)
│
├── data/
│   └── agrorisk_dataset.csv        # Dataset usado para treinar o modelo (Sprint 2)
│
├── sql/
│   ├── schema_sqlite.sql            # Schema usado pelo backend (SQLite, MVP)
│   └── dados_postgres_referencia.sql # Schema original da Sprint 2 (PostgreSQL) + queries analíticas
│
├── requirements.txt
├── .env.example
├── .gitignore
└── README.md
```

---

## 🗄️ Engenharia de Dados

O banco (SQLite no MVP; schema equivalente ao PostgreSQL documentado na Sprint 2) mantém 5 tabelas com integridade referencial:

- `equipamentos` — cadastro da frota (criado automaticamente na primeira leitura de cada equipamento)
- `regioes` — áreas monitoradas (pré-populada com as 5 regiões do dataset)
- `telemetria` — dados brutos recebidos via API (tabela principal)
- `scores_risco` — resultados gerados pelo modelo de IA a cada requisição
- `historico_alertas` — rastro de alertas ALTO/CRÍTICO disparados
- `log_uso` **(novo na Sprint 3)** — auditoria de todas as requisições (autorizadas, negadas ou com erro), com endpoint, cliente e status

> Por que SQLite no MVP? Zero setup para os tutores rodarem localmente. O código de acesso (`backend/database.py`) usa SQL parametrizado padrão, então a troca para PostgreSQL em produção é uma mudança de connection string, sem reescrever queries. O schema PostgreSQL original está preservado em `sql/dados_postgres_referencia.sql`.

---

## 🤖 Modelo de Risco (herdado da Sprint 2)

O backend não reimplementa o modelo — ele **importa e aciona** `modelo_agrorisk.py` da Sprint 2 a cada nova telemetria (`backend/risk_model.py`). Isso é o núcleo da integração pedida: o modelo isolado passa a fazer parte de um fluxo vivo.

- **Algoritmo:** Random Forest Classifier (200 árvores, `class_weight="balanced"`)
- **Acurácia (teste):** 80.5% | **CV 5-fold:** 79.2% ± 1.6%
- **Cache:** o modelo é treinado uma vez na subida do backend e cacheado em `data/modelo_rf.pkl` (evita retreinar a cada requisição)
- **Faixas de risco:** BAIXO (0–34) · MÉDIO (35–54) · ALTO (55–74) · CRÍTICO (75–100)
- Alertas são disparados automaticamente para níveis **ALTO** e **CRÍTICO**

---

## 🔒 Segurança da Informação (novo na Sprint 3)

| Controle | Implementação |
|---|---|
| Autenticação | Toda escrita/leitura de dados exige header `X-API-Key` válido (`backend/security.py`) |
| Autorização negada | Retorna `401` e é registrada em `log_uso` |
| Rate limiting | Janela deslizante por cliente (padrão: 120 req/min), retorna `429` se excedido |
| Integridade dos dados | `CHECK constraints` no schema (faixas válidas de umidade, inclinação, níveis de risco) |
| Auditoria/rastreabilidade | Toda requisição (sucesso ou falha) é logada em `log_uso` com timestamp, endpoint, cliente e status |
| Tratamento de exceções | Middleware global captura falhas não tratadas e evita vazamento de stack trace ao cliente |
| Segredos | Chave de API via variável de ambiente (`.env`, nunca versionado — ver `.env.example`) |

---

## 🚀 Como Executar

### Pré-requisitos
```bash
pip install -r requirements.txt
```

### Passo a passo

```bash
# 1. (Opcional) Definir a chave de API — senão usa o valor padrão de desenvolvimento
cp .env.example .env

# 2. Subir o backend integrador (primeira execução treina e cacheia o modelo)
uvicorn backend.main:app --reload
# → Backend em http://localhost:8000
# → Documentação interativa (Swagger) em http://localhost:8000/docs

# 3. Em outro terminal: simular fontes de dados enviando telemetria em tempo real
python simulate_ingestion.py --n 30 --intervalo 0.3
# → Simula sensores IoT / API clima / GPS enviando dados ao backend
# → Cada leitura já retorna o score de risco calculado na hora

# 4. Em outro terminal: abrir o dashboard
streamlit run dashboard/streamlit_app.py
# → Acesse http://localhost:8501
# → Consome a API (não lê o CSV/modelo diretamente) — prova a integração real
```

### Testando a API diretamente (sem o dashboard)

```bash
curl -X POST http://localhost:8000/telemetria \
  -H "Content-Type: application/json" \
  -H "X-API-Key: agrosafe-dev-key-2025" \
  -d '{
    "id_equipamento": "EQ-007",
    "regiao": "Cerrado-MT",
    "umidade_solo_pct": 88,
    "inclinacao_lateral_graus": 22,
    "precipitacao_3h_mm": 40,
    "dist_corpo_agua_m": 60
  }'
```

Resposta esperada (score/alerta calculados pelo modelo em tempo real):
```json
{
  "id_registro": 1,
  "id_score": 1,
  "id_equipamento": "EQ-007",
  "regiao": "Cerrado-MT",
  "score_risco": 68,
  "nivel_risco": "ALTO",
  "alerta_ativo": true,
  "modelo_versao": "v1.0-sprint3",
  "mensagem": "Risco ALTO — alerta recomendado ao gestor/operador."
}
```

---

## 🎯 User Stories Atendidas

| Persona | User Story | Como foi atendida na Sprint 3 |
|---|---|---|
| **Operador** | Receber alertas de risco em tempo real | `POST /telemetria` retorna o alerta imediatamente; `historico_alertas` persiste o disparo |
| **Gestor de Frota** | Monitorar score de risco da frota | `GET /resumo` (ranking por equipamento) + aba "Scores por Equipamento" no dashboard |
| **Analista Sompo** | Rastreabilidade de dados para bonificação | `log_uso` + `historico_alertas` com timestamp, origem do dado e versão do modelo |

---

## 🧭 Limitações do MVP (transparência sobre o ~60%)

- Autenticação por chave estática (não há gestão de usuários/perfis ainda)
- Banco SQLite local, não PostgreSQL gerenciado (mudança de connection string, sem retrabalho de schema)
- Dados de entrada são simulados (`simulate_ingestion.py`); integração com sensores reais ficaria para a próxima etapa
- Dashboard é read-only e não paginado para grandes volumes
- Sem containerização (Docker) ainda — execução local via `uvicorn` e `streamlit`

---

## 📎 Links

- 🎥 [Vídeo Sprint 1](https://youtu.be/3Em1MsapoEM?si=QdFbxhZFvli6SFoB)
- 🎥 [Vídeo Sprint 2](https://youtu.be/LQdnhLRkRbA)
- 🎥 Vídeo Sprint 3: *adicionar após gravação*
- 📁 Repositório privado — colaborador: **fiap-tutoria** (https://github.com/fiap-tutoria)
