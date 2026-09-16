from app.llm_client import generate_structured
from app.models import AnaliseComparativa, VagaExtraida

_PROMPT_TEMPLATE = """\
Você é um recrutador técnico sênior. Compare a vaga extraída abaixo com o currículo \
do candidato e produza uma avaliação honesta, no mesmo padrão que um recrutador \
experiente faria em uma triagem rápida.

Regras de julgamento:
- skills_presentes, skills_ausentes e skills_parciais são MUTUAMENTE EXCLUSIVAS: cada \
  skill crítica da vaga aparece em exatamente UMA dessas três listas, nunca em mais de \
  uma. Antes de responder, verifique que nenhuma skill se repete entre as listas.
- Uma skill do currículo só conta como "presente" se for equivalente ou claramente \
  transferível para a skill crítica da vaga (ex: "Vue.js" não é igual a "React", mas é \
  uma skill parcialmente transferível de front-end).
- Skills parcialmente atendidas vão em skills_parciais (e SOMENTE em skills_parciais), \
  com uma explicação curta e honesta do motivo (o que falta ou o que é diferente).
- Skills totalmente ausentes do currículo (sem equivalência nem menção) vão em \
  skills_ausentes (e SOMENTE em skills_ausentes) — não repita ali uma skill que já \
  entrou em skills_parciais.
- match_score (0 a 100) deve refletir a aderência real do candidato à vaga, sem \
  inflar por cortesia.
- red_flags são pontos que fariam um recrutador descartar o currículo rapidamente \
  para essa vaga específica (ex: nível de senioridade incompatível, ausência total \
  de uma skill crítica, formação em área não relacionada) — não invente red flags \
  que não têm base no texto.
- justificativa deve resumir em 2-4 frases o raciocínio por trás do score.
- Escreva justificativa, os títulos/descrições de red_flags e os motivos de \
  skills_parciais em português formal e objetivo, como um relatório técnico de RH \
  — frases completas, sem gírias, sem abreviações informais e sem tom de conversa \
  (ex: evite "meio que", "não rolou", "faltou né"; prefira "não há evidência de", \
  "o candidato não demonstra").

Vaga (já extraída em estrutura):
responsabilidades: {responsabilidades}
requisitos: {requisitos}
skills_criticas: {skills_criticas}

Currículo do candidato:
\"\"\"
{curriculo}
\"\"\"
"""


def comparar_e_julgar(vaga: VagaExtraida, curriculo: str) -> AnaliseComparativa:
    prompt = _PROMPT_TEMPLATE.format(
        responsabilidades=vaga.responsabilidades,
        requisitos=vaga.requisitos,
        skills_criticas=vaga.skills_criticas,
        curriculo=curriculo,
    )
    return generate_structured(prompt, AnaliseComparativa)
