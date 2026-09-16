# Analisador de Vagas

Um agente que automatiza a triagem que um recrutador sênior faz manualmente: recebe o texto de uma vaga e um currículo, e devolve, sem intervenção humana em cada etapa:

- **Match score** (0–100%)
- **Skills críticas ausentes ou parcialmente atendidas**
- **Red flags** que fariam um recrutador descartar o currículo em segundos
- Um sinal de **confiança** na própria análise, pra avisar quando os dados de entrada eram fracos demais pra um julgamento seguro

## Por que isso é um agente, e não só uma chamada de API

A diferença entre um agente e uma chamada única de prompt é orquestrar múltiplas etapas com estado, cada uma decidindo/estruturando o que fazer, em vez de devolver uma resposta solta em texto livre.

O pipeline aqui é **determinístico na ordem das etapas**, mas cada etapa usa a LLM (Gemini) com **structured output forçado por schema Pydantic** — nunca parsing manual de texto livre. A etapa final de validação (heurística, sem custo extra de LLM) decide se o resultado deve ser mostrado com um aviso de baixa confiança, em vez de sempre devolver uma resposta com aparência de certeza absoluta.

```
POST /analisar
     │
     ▼
┌─────────────┐     ┌───────────────────┐     ┌─────────────┐
│  1. EXTRAIR │ ──▶ │ 2+3. COMPARAR+     │ ──▶ │  4. VALIDAR │
│  vaga → JSON│     │ JULGAR (1 chamada) │     │  confiança  │
└─────────────┘     └───────────────────┘     └─────────────┘
     LLM                    LLM                  heurística
```

| Etapa | O que faz | Usa LLM? |
|---|---|---|
| 1. Extrair | Lê o texto bruto da vaga e estrutura responsabilidades, requisitos e skills críticas | Sim |
| 2+3. Comparar + Julgar | Compara a vaga estruturada com o currículo, julgando equivalências semânticas (ex: "Vue.js" ≈ mas ≠ "React"), e já produz o match score, red flags e justificativa numa única chamada | Sim |
| 4. Validar | Aplica sinais objetivos (texto de entrada curto, extração pobre, inconsistência lógica entre listas) pra sinalizar confiança alta/média/baixa | Não — heurística pura |

As etapas 2 e 3 do desenho original foram fundidas numa chamada só: comparar skills e julgar o score são semanticamente inseparáveis (o modelo já precisa julgar pra decidir se uma skill é parcial), então rodar como duas chamadas de LLM só dobraria custo e latência sem ganho de qualidade. A etapa de validação, por sua vez, não precisa de mais uma chamada de LLM — baixa confiança correlaciona bem com sinais objetivos e baratos de detectar (currículo muito curto, extração da vaga vazia, inconsistência entre as listas de skills).

## Stack

- Python 3.12 + FastAPI (endpoint único: `POST /analisar`)
- Pydantic (schemas de request/response e do structured output)
- Google Gemini (`gemini-3.1-flash-lite`) via `google-genai`, com `response_schema` forçando a saída ao formato Pydantic
- Sem banco de dados — tudo em memória, por request

## Como rodar localmente

```bash
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

cp .env.example .env
# edite .env e cole sua GEMINI_API_KEY (gere uma gratuita em aistudio.google.com/apikey)

.venv/bin/uvicorn app.main:app --reload
```

Acesse `http://localhost:8000/docs` pro Swagger UI interativo, ou `http://localhost:8000/static/test.html` pra uma interface visual mais prática: cole o texto da vaga e do currículo direto (sem se preocupar em escapar JSON) ou faça upload de um `.txt`/`.pdf` — o PDF é lido e tem o texto extraído no próprio navegador, via [pdf.js](https://mozilla.github.io/pdf.js/), antes de enviar pro endpoint. O resultado aparece formatado (score, skills e red flags), com o JSON bruto disponível num painel colapsável.

Currículos e uma vaga real de exemplo estão em `examples/`. Se preferir testar via `curl`/Swagger em vez da página, `scripts/gerar_payload.py` gera o JSON já formatado corretamente a partir de arquivos `.txt` (colar texto multi-linha bruto direto no Swagger quebra o JSON — as quebras de linha precisam vir escapadas):

```bash
.venv/bin/python scripts/gerar_payload.py examples/vaga_exemplo.txt examples/curriculos/automacao.txt
```

Copie a saída e cole no campo do "Try it out" do Swagger.

### Rodando os testes

```bash
.venv/bin/pytest tests/ -v
```

Os testes mockam a resposta da LLM — não batem na API de verdade, então rodam instantâneos e não custam nada.

## Exemplo real de input/output

Testado com uma vaga real de estágio em Governança de Segurança da Informação e um currículo real focado em automação/IA (nenhum dos dois foi escrito pra "combinar" — é um teste honesto de mismatch parcial).

**Request** (resumido):
```json
{
  "vaga_texto": "Pessoa Estagiária de Governança de SI [...] Serão considerados diferenciais cursos ou conhecimentos introdutórios em segurança da informação, LGPD, ISO 27001, gestão de riscos, auditoria ou inteligência artificial.",
  "curriculo": "[...] experiência prática em Python (FastAPI), Node.js [...] Uso diário de ferramentas de IA agêntica (GitHub Copilot, Claude Code, ChatGPT, Gemini) [...]"
}
```

**Response**:
```json
{
  "match_score": 55,
  "skills_faltando": ["Compliance"],
  "skills_parciais": [
    {
      "skill": "Segurança da Informação",
      "motivo": "Possui experiência básica de suporte de rede (N1), mas falta exposição direta a controles de segurança corporativa ou gestão de vulnerabilidades."
    },
    {
      "skill": "LGPD",
      "motivo": "Não há menção explícita no currículo, embora o candidato trabalhe com validação de dados em APIs."
    }
  ],
  "red_flags": [
    {
      "titulo": "Perfil estritamente técnico/desenvolvedor",
      "descricao": "O candidato é fortemente inclinado ao desenvolvimento de software e automação de APIs, enquanto a vaga é voltada para GRC (Governança, Riscos e Compliance)."
    }
  ],
  "confianca": "alta",
  "observacoes": "O candidato possui excelente proficiência em IA e automação, alinhando-se bem com o uso de ferramentas agênticas solicitado pela vaga. No entanto, o currículo carece de experiência em GRC, LGPD e normas de segurança."
}
```

Como comparação, o mesmo pipeline rodado com um currículo focado em front-end (sem menção a ferramentas de IA) contra a mesma vaga devolveu `match_score: 45` — a diferença reflete corretamente que o currículo de automação tem um diferencial real (uso de ferramentas de IA agêntica) que o de front-end não tem.

## Estrutura do projeto

```
app/
├── main.py              # FastAPI app + rota POST /analisar
├── models.py             # Schemas Pydantic (request/response de cada etapa)
├── config.py              # Carrega API key via .env
├── llm_client.py           # Wrapper fino do Gemini com structured output
└── agent/
    ├── extrator.py          # Etapa 1
    ├── comparador.py         # Etapa 2+3 combinada
    └── validador.py           # Etapa 4 (heurística)
tests/
└── test_pipeline.py     # Testes com a LLM mockada
examples/
├── vaga_exemplo.txt      # Vaga real usada nos testes manuais
└── curriculos/            # 5 currículos reais (frontend, backend, full-stack, automação, suporte)
scripts/
└── gerar_payload.py      # Helper pra montar payloads de teste pro Swagger UI
static/
└── test.html             # Interface visual manual (paste ou upload de .txt/.pdf)
```
