from fastapi import FastAPI

from app.agent.comparador import comparar_e_julgar
from app.agent.extrator import extrair_vaga
from app.agent.validador import validar
from app.models import AnalisarRequest, AnalisarResponse

app = FastAPI(
    title="Analisador de Vagas",
    description="Agente que compara uma vaga e um currículo e devolve match score, skills faltando e red flags.",
)


@app.post("/analisar", response_model=AnalisarResponse)
def analisar(request: AnalisarRequest) -> AnalisarResponse:
    vaga = extrair_vaga(request.vaga_texto)
    analise = comparar_e_julgar(vaga, request.curriculo)
    validacao = validar(request.vaga_texto, request.curriculo, vaga, analise)

    observacoes = analise.justificativa
    if validacao.motivo_baixa_confianca:
        observacoes += f" [Aviso de confiança: {validacao.motivo_baixa_confianca}]"

    return AnalisarResponse(
        match_score=analise.match_score,
        skills_faltando=analise.skills_ausentes,
        skills_parciais=analise.skills_parciais,
        red_flags=analise.red_flags,
        confianca=validacao.confianca,
        observacoes=observacoes,
    )
