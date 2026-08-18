-- AgroSafe Predictor - Sprint 3
-- Schema SQLite usado pelo backend (backend/database.py)
-- Equivalente ao schema PostgreSQL da Sprint 2 (sql/dados_postgres_referencia.sql),
-- adaptado para rodar sem servidor externo no MVP.

CREATE TABLE IF NOT EXISTS equipamentos (
    id_equipamento  TEXT PRIMARY KEY,
    descricao       TEXT,
    modelo          TEXT,
    proprietario    TEXT,
    apolice_numero  TEXT
);

CREATE TABLE IF NOT EXISTS regioes (
    id_regiao   INTEGER PRIMARY KEY AUTOINCREMENT,
    nome_regiao TEXT NOT NULL UNIQUE,
    estado      TEXT,
    cultura     TEXT
);

CREATE TABLE IF NOT EXISTS telemetria (
    id_registro              INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp                TEXT NOT NULL,
    id_equipamento           TEXT REFERENCES equipamentos(id_equipamento),
    id_regiao                INTEGER REFERENCES regioes(id_regiao),
    umidade_solo_pct         REAL CHECK (umidade_solo_pct BETWEEN 0 AND 100),
    inclinacao_lateral_graus REAL CHECK (inclinacao_lateral_graus BETWEEN 0 AND 45),
    precipitacao_3h_mm       REAL CHECK (precipitacao_3h_mm >= 0),
    dist_corpo_agua_m        REAL CHECK (dist_corpo_agua_m >= 0),
    velocidade_kmh           REAL,
    temperatura_c            REAL,
    horas_operacao_dia       REAL,
    origem                   TEXT DEFAULT 'SIMULADO'
);

CREATE TABLE IF NOT EXISTS scores_risco (
    id_score       INTEGER PRIMARY KEY AUTOINCREMENT,
    id_registro    INTEGER REFERENCES telemetria(id_registro) ON DELETE CASCADE,
    timestamp_calc TEXT NOT NULL,
    score_risco    INTEGER CHECK (score_risco BETWEEN 0 AND 100),
    nivel_risco    TEXT CHECK (nivel_risco IN ('BAIXO','MEDIO','ALTO','CRITICO')),
    alerta_ativo   INTEGER NOT NULL DEFAULT 0,
    modelo_versao  TEXT DEFAULT 'v1.0'
);

CREATE TABLE IF NOT EXISTS historico_alertas (
    id_alerta        INTEGER PRIMARY KEY AUTOINCREMENT,
    id_score         INTEGER REFERENCES scores_risco(id_score),
    timestamp_alerta TEXT DEFAULT CURRENT_TIMESTAMP,
    canal_envio      TEXT CHECK (canal_envio IN ('DASHBOARD','SMS','EMAIL','PUSH')),
    mensagem         TEXT,
    confirmado       INTEGER DEFAULT 0
);

-- Log de uso/auditoria — requisito de segurança da informação:
-- rastreia entradas, saídas e decisões do sistema.
CREATE TABLE IF NOT EXISTS log_uso (
    id_log      INTEGER PRIMARY KEY AUTOINCREMENT,
    timestamp   TEXT DEFAULT CURRENT_TIMESTAMP,
    endpoint    TEXT,
    metodo      TEXT,
    cliente_id  TEXT,
    status_code INTEGER,
    detalhe     TEXT
);

CREATE INDEX IF NOT EXISTS idx_telemetria_equipamento ON telemetria(id_equipamento);
CREATE INDEX IF NOT EXISTS idx_telemetria_timestamp   ON telemetria(timestamp);
CREATE INDEX IF NOT EXISTS idx_scores_nivel           ON scores_risco(nivel_risco);
CREATE INDEX IF NOT EXISTS idx_scores_alerta          ON scores_risco(alerta_ativo);
