from typing import Literal, Optional

from pydantic import BaseModel, Field


class AnalisarRequest(BaseModel):
    vaga_texto: str
    curriculo: str


class VagaExtraida(BaseModel):
    """Saída da Etapa 1 (extrair)."""

    responsabilidades: list[str]
    requisitos: list[str]
    skills_criticas: list[str]


class SkillParcial(BaseModel):
    skill: str
    motivo: str


class RedFlag(BaseModel):
    titulo: str
    descricao: str


class AnaliseComparativa(BaseModel):
    """Saída da Etapa 2+3 combinada (comparar + julgar em uma só chamada de LLM)."""

    skills_presentes: list[str]
    skills_ausentes: list[str]
    skills_parciais: list[SkillParcial]
    match_score: int = Field(ge=0, le=100)
    red_flags: list[RedFlag]
    justificativa: str


class ValidacaoConfianca(BaseModel):
    """Saída da Etapa 4 (validar) — heurística, sem chamada de LLM."""

    confianca: Literal["alta", "media", "baixa"]
    motivo_baixa_confianca: Optional[str] = None


class AnalisarResponse(BaseModel):
    match_score: int
    skills_faltando: list[str]
    skills_parciais: list[SkillParcial]
    red_flags: list[RedFlag]
    confianca: Literal["alta", "media", "baixa"]
    observacoes: Optional[str] = None
