from app.llm_client import generate_structured
from app.models import VagaExtraida

_PROMPT_TEMPLATE = """\
Você é um recrutador técnico sênior. Leia o texto de vaga abaixo e extraia,
de forma objetiva e sem inventar informação que não está no texto:

- responsabilidades: lista das principais responsabilidades/atividades do dia a dia
- requisitos: lista dos requisitos e qualificações exigidos ou desejados
- skills_criticas: lista curta (até 10 itens) das skills/tecnologias/conhecimentos
  mais críticos para o sucesso na vaga — o que um recrutador olharia primeiro
  num currículo

Texto da vaga:
\"\"\"
{vaga_texto}
\"\"\"
"""


def extrair_vaga(vaga_texto: str) -> VagaExtraida:
    prompt = _PROMPT_TEMPLATE.format(vaga_texto=vaga_texto)
    return generate_structured(prompt, VagaExtraida)
