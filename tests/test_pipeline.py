"""Testes do pipeline com a LLM mockada — nunca bate na API de verdade."""

from fastapi.testclient import TestClient

from app.agent.comparador import comparar_e_julgar
from app.agent.extrator import extrair_vaga
from app.agent.validador import validar
from app.main import app
from app.models import AnaliseComparativa, RedFlag, SkillParcial, VagaExtraida

_VAGA_EXTRAIDA_MOCK = VagaExtraida(
    responsabilidades=["Manter APIs REST", "Revisar código em Python"],
    requisitos=["3 anos de experiência", "Conhecimento em FastAPI"],
    skills_criticas=["Python", "FastAPI", "Docker"],
)

_ANALISE_MOCK = AnaliseComparativa(
    skills_presentes=["Python"],
    skills_ausentes=["Docker"],
    skills_parciais=[SkillParcial(skill="FastAPI", motivo="tem Flask, não FastAPI")],
    match_score=60,
    red_flags=[RedFlag(titulo="Sem Docker", descricao="vaga exige Docker e o currículo não menciona")],
    justificativa="Candidato tem base sólida em Python mas falta Docker e experiência direta em FastAPI.",
)


def test_extrair_vaga_usa_llm_mockada(monkeypatch):
    monkeypatch.setattr(
        "app.agent.extrator.generate_structured",
        lambda prompt, model: _VAGA_EXTRAIDA_MOCK,
    )

    resultado = extrair_vaga("Vaga: Desenvolvedor Python pleno.")

    assert resultado == _VAGA_EXTRAIDA_MOCK


def test_comparar_e_julgar_usa_llm_mockada(monkeypatch):
    monkeypatch.setattr(
        "app.agent.comparador.generate_structured",
        lambda prompt, model: _ANALISE_MOCK,
    )

    resultado = comparar_e_julgar(_VAGA_EXTRAIDA_MOCK, "Currículo qualquer")

    assert resultado == _ANALISE_MOCK


def test_validar_confianca_alta_com_dados_completos():
    validacao = validar(
        vaga_texto="x" * 300,
        curriculo="y" * 200,
        vaga=_VAGA_EXTRAIDA_MOCK,
        analise=_ANALISE_MOCK,
    )

    assert validacao.confianca == "alta"
    assert validacao.motivo_baixa_confianca is None


def test_validar_confianca_baixa_com_curriculo_curto():
    validacao = validar(
        vaga_texto="x" * 300,
        curriculo="Sei programar.",
        vaga=_VAGA_EXTRAIDA_MOCK,
        analise=_ANALISE_MOCK,
    )

    assert validacao.confianca == "baixa"
    assert "curto" in validacao.motivo_baixa_confianca


def test_validar_confianca_baixa_com_skills_duplicadas_entre_listas():
    analise_inconsistente = _ANALISE_MOCK.model_copy(
        update={"skills_presentes": ["Docker"]}  # Docker também está em skills_ausentes
    )

    validacao = validar(
        vaga_texto="x" * 300,
        curriculo="y" * 200,
        vaga=_VAGA_EXTRAIDA_MOCK,
        analise=analise_inconsistente,
    )

    assert validacao.confianca == "baixa"
    assert "inconsistência" in validacao.motivo_baixa_confianca


def test_endpoint_analisar_end_to_end_com_llm_mockada(monkeypatch):
    monkeypatch.setattr(
        "app.agent.extrator.generate_structured",
        lambda prompt, model: _VAGA_EXTRAIDA_MOCK,
    )
    monkeypatch.setattr(
        "app.agent.comparador.generate_structured",
        lambda prompt, model: _ANALISE_MOCK,
    )

    client = TestClient(app)
    response = client.post(
        "/analisar",
        json={"vaga_texto": "Vaga: Desenvolvedor Python pleno.", "curriculo": "Currículo qualquer"},
    )

    assert response.status_code == 200
    body = response.json()
    assert body["match_score"] == 60
    assert body["skills_faltando"] == ["Docker"]
    # payload de teste é curto de propósito, então a heurística da etapa 4
    # deve sinalizar confiança baixa
    assert body["confianca"] == "baixa"
    assert "FastAPI" in body["observacoes"] or "Python" in body["observacoes"]
