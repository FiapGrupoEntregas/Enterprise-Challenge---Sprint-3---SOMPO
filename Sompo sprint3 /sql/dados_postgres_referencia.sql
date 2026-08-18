-- AgroSafe Predictor - Sprint 2
-- Banco de Dados: Schema e Queries
-- Sompo Seguros | FIAP 1TIAOB

-- ── CRIAÇÃO DAS TABELAS ────────────────────────

-- Tabela de equipamentos cadastrados
CREATE TABLE IF NOT EXISTS equipamentos (
    id_equipamento  VARCHAR(10)  PRIMARY KEY,
    descricao       VARCHAR(100) NOT NULL,
    ano_fabricacao  INT,
    modelo          VARCHAR(50),
    proprietario    VARCHAR(100),
    apólice_numero  VARCHAR(30)
);

-- Tabela de regiões monitoradas
CREATE TABLE IF NOT EXISTS regioes (
    id_regiao   SERIAL PRIMARY KEY,
    nome_regiao VARCHAR(50) NOT NULL UNIQUE,
    estado      CHAR(2),
    cultura     VARCHAR(50)
);

-- Tabela principal de telemetria (recebe dados dos sensores)
CREATE TABLE IF NOT EXISTS telemetria (
    id_registro              SERIAL PRIMARY KEY,
    timestamp                TIMESTAMP NOT NULL DEFAULT NOW(),
    id_equipamento           VARCHAR(10) REFERENCES equipamentos(id_equipamento),
    id_regiao                INT REFERENCES regioes(id_regiao),
    umidade_solo_pct         NUMERIC(5,1) CHECK (umidade_solo_pct BETWEEN 0 AND 100),
    inclinacao_lateral_graus NUMERIC(4,1) CHECK (inclinacao_lateral_graus BETWEEN 0 AND 45),
    precipitacao_3h_mm       NUMERIC(5,1) CHECK (precipitacao_3h_mm >= 0),
    dist_corpo_agua_m        INT          CHECK (dist_corpo_agua_m >= 0),
    velocidade_kmh           NUMERIC(4,1),
    temperatura_c            NUMERIC(4,1),
    horas_operacao_dia       NUMERIC(4,1)
);

-- Tabela de scores e alertas gerados pelo modelo de IA
CREATE TABLE IF NOT EXISTS scores_risco (
    id_score       SERIAL PRIMARY KEY,
    id_registro    INT REFERENCES telemetria(id_registro) ON DELETE CASCADE,
    timestamp_calc TIMESTAMP NOT NULL DEFAULT NOW(),
    score_risco    INT        CHECK (score_risco BETWEEN 0 AND 100),
    nivel_risco    VARCHAR(10) CHECK (nivel_risco IN ('BAIXO','MEDIO','ALTO','CRITICO')),
    alerta_ativo   BOOLEAN    NOT NULL DEFAULT FALSE,
    modelo_versao  VARCHAR(20) DEFAULT 'v1.0'
);

-- Tabela de histórico de alertas disparados
CREATE TABLE IF NOT EXISTS historico_alertas (
    id_alerta      SERIAL PRIMARY KEY,
    id_score       INT REFERENCES scores_risco(id_score),
    timestamp_alerta TIMESTAMP DEFAULT NOW(),
    canal_envio    VARCHAR(20) CHECK (canal_envio IN ('DASHBOARD','SMS','EMAIL','PUSH')),
    mensagem       TEXT,
    confirmado     BOOLEAN DEFAULT FALSE
);

-- ── ÍNDICES PARA PERFORMANCE ─────────────────────────────────

CREATE INDEX IF NOT EXISTS idx_telemetria_equipamento ON telemetria(id_equipamento);
CREATE INDEX IF NOT EXISTS idx_telemetria_timestamp   ON telemetria(timestamp);
CREATE INDEX IF NOT EXISTS idx_scores_nivel           ON scores_risco(nivel_risco);
CREATE INDEX IF NOT EXISTS idx_scores_alerta          ON scores_risco(alerta_ativo);

-- ==================
-- QUERIES ANALÍTICAS
-- ==================

-- Q1: Score médio de risco por equipamento (ranking)
SELECT
    t.id_equipamento,
    COUNT(*)                    AS total_registros,
    ROUND(AVG(s.score_risco),1) AS score_medio,
    MAX(s.score_risco)          AS score_maximo,
    SUM(s.alerta_ativo::INT)    AS total_alertas
FROM telemetria t
JOIN scores_risco s ON s.id_registro = t.id_registro
GROUP BY t.id_equipamento
ORDER BY score_medio DESC;

-- Q2: Distribuição de risco por região
SELECT
    r.nome_regiao,
    s.nivel_risco,
    COUNT(*) AS ocorrencias,
    ROUND(COUNT(*) * 100.0 / SUM(COUNT(*)) OVER (PARTITION BY r.nome_regiao), 1) AS pct_regiao
FROM telemetria t
JOIN regioes r ON r.id_regiao = t.id_regiao
JOIN scores_risco s ON s.id_registro = t.id_registro
GROUP BY r.nome_regiao, s.nivel_risco
ORDER BY r.nome_regiao, s.nivel_risco;

-- Q3: Últimos 10 alertas críticos ativos
SELECT
    t.timestamp,
    t.id_equipamento,
    r.nome_regiao,
    t.umidade_solo_pct,
    t.dist_corpo_agua_m,
    t.precipitacao_3h_mm,
    s.score_risco,
    s.nivel_risco
FROM telemetria t
JOIN scores_risco s ON s.id_registro = t.id_registro
JOIN regioes r ON r.id_regiao = t.id_regiao
WHERE s.nivel_risco IN ('ALTO','CRITICO')
  AND s.alerta_ativo = TRUE
ORDER BY t.timestamp DESC
LIMIT 10;

-- Q4: Correlação entre umidade do solo e score de risco
-- (Usado para validação estatística do modelo)
SELECT
    CASE
        WHEN umidade_solo_pct < 45  THEN '< 45%'
        WHEN umidade_solo_pct < 65  THEN '45-65%'
        WHEN umidade_solo_pct < 80  THEN '65-80%'
        ELSE '≥ 80%'
    END AS faixa_umidade,
    COUNT(*)                    AS registros,
    ROUND(AVG(s.score_risco),1) AS score_medio
FROM telemetria t
JOIN scores_risco s ON s.id_registro = t.id_registro
GROUP BY faixa_umidade
ORDER BY score_medio;

-- Q5: Série temporal de alertas por dia (para dashboard)
SELECT
    DATE(t.timestamp)        AS dia,
    COUNT(*)                 AS total_registros,
    SUM(s.alerta_ativo::INT) AS total_alertas,
    ROUND(AVG(s.score_risco),1) AS score_medio_dia
FROM telemetria t
JOIN scores_risco s ON s.id_registro = t.id_registro
GROUP BY DATE(t.timestamp)
ORDER BY dia DESC
LIMIT 30;

-- Q6: Equipamentos com maior risco acumulado nos últimos 7 dias
SELECT
    t.id_equipamento,
    COUNT(*)                 AS operacoes,
    ROUND(AVG(s.score_risco),1) AS score_medio_7d,
    MAX(s.score_risco)       AS pico_risco,
    SUM(s.alerta_ativo::INT) AS alertas_emitidos
FROM telemetria t
JOIN scores_risco s ON s.id_registro = t.id_registro
WHERE t.timestamp >= NOW() - INTERVAL '7 days'
GROUP BY t.id_equipamento
HAVING AVG(s.score_risco) > 40
ORDER BY score_medio_7d DESC;
