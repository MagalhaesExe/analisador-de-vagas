from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from google.genai.errors import APIError

from app.agent.comparador import comparar_e_julgar
from app.agent.extrator import extrair_vaga
from app.agent.validador import validar
from app.models import AnalisarRequest, AnalisarResponse

app = FastAPI(
    title="Analisador de Vagas",
    description="Agente que compara uma vaga e um currículo e devolve match score, skills faltando e red flags.",
)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.exception_handler(APIError)
def erro_provedor_llm(request: Request, exc: APIError) -> JSONResponse:
    """O provedor de LLM (Gemini) já tenta de novo automaticamente em erros \
    transitórios (ver retry_options em llm_client.py); se mesmo assim falhar, \
    devolvemos uma mensagem amigável em vez do erro genérico do servidor."""

    return JSONResponse(
        status_code=503,
        content={
            "erro": (
                "Não foi possível concluir a análise no momento porque o "
                "provedor de IA está indisponível ou sobrecarregado. "
                "Tente novamente em alguns instantes."
            ),
        },
    )


@app.post("/analisar", response_model=AnalisarResponse)
def analisar(request: AnalisarRequest) -> AnalisarResponse:
    vaga = extrair_vaga(request.vaga_texto)
    analise = comparar_e_julgar(vaga, request.curriculo)
    validacao = validar(request.vaga_texto, request.curriculo, vaga, analise)

    observacoes = analise.justificativa
    if validacao.motivo_baixa_confianca:
        observacoes += f" Observação sobre a confiança desta análise: {validacao.motivo_baixa_confianca}."

    return AnalisarResponse(
        match_score=analise.match_score,
        skills_faltando=analise.skills_ausentes,
        skills_parciais=analise.skills_parciais,
        red_flags=analise.red_flags,
        confianca=validacao.confianca,
        observacoes=observacoes,
    )
