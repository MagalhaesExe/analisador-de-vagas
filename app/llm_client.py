"""Wrapper fino sobre o provider de LLM (Gemini).

Isolar o provider aqui é o que permite trocar de Gemini pra outro
depois sem tocar nas etapas do pipeline.
"""

from google import genai
from google.genai import types
from pydantic import BaseModel

from app.config import GEMINI_API_KEY

_client = genai.Client(
    api_key=GEMINI_API_KEY,
    http_options=types.HttpOptions(
        retry_options=types.HttpRetryOptions(
            attempts=4,
            initial_delay=1.0,
            max_delay=8.0,
        ),
    ),
)

_MODEL = "gemini-3.1-flash-lite"


def generate_structured[T: BaseModel](prompt: str, response_model: type[T]) -> T:
    """Manda um prompt pro Gemini forçando a saída a seguir `response_model`
    (structured output) e devolve já validado como instância do schema."""

    response = _client.models.generate_content(
        model=_MODEL,
        contents=prompt,
        config=types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=response_model,
        ),
    )
    return response_model.model_validate_json(response.text)
