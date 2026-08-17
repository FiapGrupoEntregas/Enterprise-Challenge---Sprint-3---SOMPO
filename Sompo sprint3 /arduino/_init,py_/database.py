"""
AgroSafe Predictor - Sprint 3
Camada de Engenharia de Dados: schema, conexão e persistência.
Sompo Seguros | FIAP 1TIAOB

Usa SQLite para o MVP (sem dependências externas de servidor).
O schema é equivalente ao dados.sql da Sprint 2 (relacional, com
integridade referencial). Para produção, a troca para PostgreSQL
exige apenas trocar a connection string — as queries são padrão SQL.
"""

import sqlite3
from contextlib import contextmanager
from datetime import datetime, timezone

from backend.config import DB_PATH

SCHEMA = """
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

-- Log de uso/auditoria (requisito de segurança: rastreabilidade de
-- entradas, saídas e decisões do sistema)
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
"""

REGIOES_PADRAO = [
    ("Cerrado-MT", "MT", "Soja/Milho"),
    ("Soja-PR", "PR", "Soja"),
    ("Cana-SP", "SP", "Cana-de-açúcar"),
    ("Arroz-RS", "RS", "Arroz"),
    ("Milho-GO", "GO", "Milho"),
]


@contextmanager
def get_conn():
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db():
    """Cria o schema (idempotente) e popula as regiões padrão."""
    with get_conn() as conn:
        conn.executescript(SCHEMA)
        for nome, estado, cultura in REGIOES_PADRAO:
            conn.execute(
                "INSERT OR IGNORE INTO regioes (nome_regiao, estado, cultura) VALUES (?, ?, ?)",
                (nome, estado, cultura),
            )


def get_or_create_equipamento(conn, id_equipamento: str):
    row = conn.execute(
        "SELECT id_equipamento FROM equipamentos WHERE id_equipamento = ?",
        (id_equipamento,),
    ).fetchone()
    if not row:
        conn.execute(
            "INSERT INTO equipamentos (id_equipamento, descricao) VALUES (?, ?)",
            (id_equipamento, f"Equipamento {id_equipamento}"),
        )


def get_regiao_id(conn, nome_regiao: str) -> int:
    row = conn.execute(
        "SELECT id_regiao FROM regioes WHERE nome_regiao = ?", (nome_regiao,)
    ).fetchone()
    if row:
        return row["id_regiao"]
    cur = conn.execute(
        "INSERT INTO regioes (nome_regiao) VALUES (?)", (nome_regiao,)
    )
    return cur.lastrowid


def inserir_telemetria(conn, dados: dict) -> int:
    get_or_create_equipamento(conn, dados["id_equipamento"])
    id_regiao = get_regiao_id(conn, dados["regiao"])
    cur = conn.execute(
        """
        INSERT INTO telemetria
            (timestamp, id_equipamento, id_regiao, umidade_solo_pct,
             inclinacao_lateral_graus, precipitacao_3h_mm, dist_corpo_agua_m,
             velocidade_kmh, temperatura_c, horas_operacao_dia, origem)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            dados.get("timestamp") or datetime.now(timezone.utc).isoformat(),
            dados["id_equipamento"],
            id_regiao,
            dados["umidade_solo_pct"],
            dados["inclinacao_lateral_graus"],
            dados["precipitacao_3h_mm"],
            dados["dist_corpo_agua_m"],
            dados.get("velocidade_kmh"),
            dados.get("temperatura_c"),
            dados.get("horas_operacao_dia"),
            dados.get("origem", "SIMULADO"),
        ),
    )
    return cur.lastrowid


def inserir_score(conn, id_registro: int, score: int, nivel: str, alerta: bool, modelo_versao: str) -> int:
    cur = conn.execute(
        """
        INSERT INTO scores_risco
            (id_registro, timestamp_calc, score_risco, nivel_risco, alerta_ativo, modelo_versao)
        VALUES (?, ?, ?, ?, ?, ?)
        """,
        (
            id_registro,
            datetime.now(timezone.utc).isoformat(),
            score,
            nivel,
            int(alerta),
            modelo_versao,
        ),
    )
    id_score = cur.lastrowid
    if alerta:
        conn.execute(
            """
            INSERT INTO historico_alertas (id_score, canal_envio, mensagem)
            VALUES (?, 'DASHBOARD', ?)
            """,
            (id_score, f"Alerta de risco {nivel} gerado automaticamente."),
        )
    return id_score


def registrar_log(endpoint: str, metodo: str, cliente_id: str, status_code: int, detalhe: str = ""):
    with get_conn() as conn:
        conn.execute(
            """
            INSERT INTO log_uso (endpoint, metodo, cliente_id, status_code, detalhe)
            VALUES (?, ?, ?, ?, ?)
            """,
            (endpoint, metodo, cliente_id, status_code, detalhe),
        )


def listar_scores(limit: int = 100, equipamento: str | None = None, regiao: str | None = None):
    query = """
        SELECT s.id_score, t.timestamp, t.id_equipamento, r.nome_regiao,
               t.umidade_solo_pct, t.inclinacao_lateral_graus, t.precipitacao_3h_mm,
               t.dist_corpo_agua_m, s.score_risco, s.nivel_risco, s.alerta_ativo,
               s.modelo_versao
        FROM scores_risco s
        JOIN telemetria t ON t.id_registro = s.id_registro
        JOIN regioes r ON r.id_regiao = t.id_regiao
        WHERE 1=1
    """
    params = []
    if equipamento:
        query += " AND t.id_equipamento = ?"
        params.append(equipamento)
    if regiao:
        query += " AND r.nome_regiao = ?"
        params.append(regiao)
    query += " ORDER BY t.timestamp DESC LIMIT ?"
    params.append(limit)

    with get_conn() as conn:
        rows = conn.execute(query, params).fetchall()
        return [dict(r) for r in rows]


def listar_alertas(limit: int = 50):
    query = """
        SELECT h.id_alerta, h.timestamp_alerta, h.canal_envio, h.mensagem,
               s.score_risco, s.nivel_risco, t.id_equipamento, r.nome_regiao
        FROM historico_alertas h
        JOIN scores_risco s ON s.id_score = h.id_score
        JOIN telemetria t ON t.id_registro = s.id_registro
        JOIN regioes r ON r.id_regiao = t.id_regiao
        ORDER BY h.timestamp_alerta DESC
        LIMIT ?
    """
    with get_conn() as conn:
        rows = conn.execute(query, (limit,)).fetchall()
        return [dict(r) for r in rows]


def resumo_por_equipamento():
    query = """
        SELECT t.id_equipamento,
               COUNT(*) AS total_registros,
               ROUND(AVG(s.score_risco), 1) AS score_medio,
               MAX(s.score_risco) AS score_maximo,
               SUM(s.alerta_ativo) AS total_alertas
        FROM telemetria t
        JOIN scores_risco s ON s.id_registro = t.id_registro
        GROUP BY t.id_equipamento
        ORDER BY score_medio DESC
    """
    with get_conn() as conn:
        rows = conn.execute(query).fetchall()
        return [dict(r) for r in rows]


def contagem_geral():
    with get_conn() as conn:
        total = conn.execute("SELECT COUNT(*) c FROM telemetria").fetchone()["c"]
        alertas = conn.execute(
            "SELECT COUNT(*) c FROM scores_risco WHERE alerta_ativo = 1"
        ).fetchone()["c"]
        return {"total_registros": total, "total_alertas": alertas}
