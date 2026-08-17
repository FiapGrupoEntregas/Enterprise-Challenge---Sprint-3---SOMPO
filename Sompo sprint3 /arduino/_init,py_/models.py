"""
AgroSafe Predictor - Sprint 3
Schemas Pydantic: validação de entrada/saída da API.
Sompo Seguros | FIAP 1TIAOB
"""

from typing import Optional
from pydantic import BaseModel, Field, field_validator


class TelemetriaEntrada(BaseModel):
    """Payload recebido de sensores/telemetria (real ou simulada)."""

    id_equipamento: str = Field(..., examples=["EQ-007"])
    regiao: str = Field(..., examples=["Cerrado-MT"])
    umidade_solo_pct: float = Field(..., ge=0, le=100)
    inclinacao_lateral_graus: float = Field(..., ge=0, le=45)
    precipitacao_3h_mm: float = Field(..., ge=0, le=200)
    dist_corpo_agua_m: float = Field(..., ge=0)
    velocidade_kmh: float = Field(15.0, ge=0, le=80)
    temperatura_c: float = Field(28.0, ge=-10, le=55)
    horas_operacao_dia: float = Field(8.0, ge=0, le=24)
    timestamp: Optional[str] = None
    origem: str = Field("SIMULADO", examples=["SENSOR_IOT", "SIMULADO", "MANUAL"])

    @field_validator("id_equipamento", "regiao")
    @classmethod
    def nao_vazio(cls, v: str) -> str:
        if not v or not v.strip():
            raise ValueError("campo não pode ser vazio")
        return v.strip()


class ScoreSaida(BaseModel):
    id_registro: int
    id_score: int
    id_equipamento: str
    regiao: str
    score_risco: int
    nivel_risco: str
    alerta_ativo: bool
    modelo_versao: str
    mensagem: str
