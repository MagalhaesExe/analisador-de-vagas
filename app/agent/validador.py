"""Etapa 4 (validar) — heurística, sem chamada de LLM.

Sinais de baixa qualidade (texto de entrada curto demais, extração pobre,
inconsistência lógica na saída da etapa 2+3) costumam correlacionar bem com
"o modelo não tinha informação suficiente pra julgar direito" — não precisa
gastar outra chamada de LLM só pra descobrir isso.
"""

from app.models import AnaliseComparativa, ValidacaoConfianca, VagaExtraida

_MIN_VAGA_TEXTO_CHARS = 200
_MIN_CURRICULO_CHARS = 100
_MIN_JUSTIFICATIVA_CHARS = 20
_MIN_REQUISITOS = 2
_MIN_SKILLS_CRITICAS = 2


def validar(
    vaga_texto: str,
    curriculo: str,
    vaga: VagaExtraida,
    analise: AnaliseComparativa,
) -> ValidacaoConfianca:
    motivos_fortes: list[str] = []
    motivos_fracos: list[str] = []

    if len(vaga_texto.strip()) < _MIN_VAGA_TEXTO_CHARS:
        motivos_fortes.append("texto da vaga é curto demais para uma extração confiável")

    if len(curriculo.strip()) < _MIN_CURRICULO_CHARS:
        motivos_fortes.append("currículo é curto demais para uma comparação confiável")

    if not vaga.responsabilidades and not vaga.requisitos:
        motivos_fortes.append("a extração da vaga não encontrou responsabilidades nem requisitos")

    nomes_parciais = {s.skill for s in analise.skills_parciais}
    overlap = set(analise.skills_presentes) & set(analise.skills_ausentes) | (
        set(analise.skills_ausentes) & nomes_parciais
    ) | (set(analise.skills_presentes) & nomes_parciais)
    if overlap:
        motivos_fortes.append(
            f"inconsistência: skill(s) classificada(s) em mais de uma categoria ({', '.join(sorted(overlap))})"
        )

    if len(vaga.requisitos) < _MIN_REQUISITOS:
        motivos_fracos.append("poucos requisitos foram extraídos da vaga")

    if len(vaga.skills_criticas) < _MIN_SKILLS_CRITICAS:
        motivos_fracos.append("poucas skills críticas foram identificadas na vaga")

    if len(analise.justificativa.strip()) < _MIN_JUSTIFICATIVA_CHARS:
        motivos_fracos.append("a justificativa do julgamento é curta demais")

    if analise.match_score in (0, 100):
        motivos_fracos.append("match_score em valor extremo (0 ou 100), o que é raro em avaliações reais")

    if motivos_fortes:
        return ValidacaoConfianca(
            confianca="baixa",
            motivo_baixa_confianca="; ".join(motivos_fortes),
        )

    if len(motivos_fracos) >= 2:
        return ValidacaoConfianca(
            confianca="baixa",
            motivo_baixa_confianca="; ".join(motivos_fracos),
        )

    if len(motivos_fracos) == 1:
        return ValidacaoConfianca(
            confianca="media",
            motivo_baixa_confianca=motivos_fracos[0],
        )

    return ValidacaoConfianca(confianca="alta")
