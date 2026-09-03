# Brief de Implementação — Agente Analisador de Vagas

> **Sobre este documento:** este é o brief de arquitetura e planejamento que guiou a construção deste projeto com o Claude Code como par de desenvolvimento. As decisões técnicas nele (escopo, stack, arquitetura do pipeline) são do autor; a seção 8 são as diretrizes de como o Claude Code deveria colaborar na implementação — revisadas e ajustadas ao longo do processo à medida que decisões concretas foram tomadas (ex: fusão das etapas de comparação e julgamento em uma única chamada de LLM). Fica no repositório como registro do processo de decisão, não como um artefato acidental.

## 1. Objetivo

Automatizar a análise que um recrutador sênior faz manualmente: receber uma vaga + um currículo e devolver, sem intervenção humana em cada etapa:

- **Match score** (0–100%)
- **Skills/palavras-chave críticas ausentes ou fracas** (lista)
- **Red flags** que fariam um recrutador descartar o currículo em menos de 10 segundos

O objetivo pessoal deste projeto é ter um artefato real e defensável em entrevista de "construção de agentes e integração de APIs", não só "usei uma API de LLM uma vez".

## 2. Por que isso é um agente, e não uma chamada de API

O que diferencia um agente de uma chamada única de prompt é ele **orquestrar múltiplas etapas com estado**, decidindo/estruturando o que fazer a cada passo, ao invés de devolver uma resposta solta em texto livre. Este projeto usa **tool use / function calling** do provider de LLM para forçar saídas estruturadas (JSON validado) em cada etapa do pipeline, e uma etapa dedicada de **validação de confiança** — o agente sinaliza quando não tem certeza, em vez de inventar.

Não é necessário (nem recomendado para o escopo do MVP) implementar um loop onde a LLM decide sozinha qual ferramenta chamar em qual ordem (estilo ReAct livre) — isso aumenta muito a superfície de bugs e é difícil de testar. Para o MVP, o pipeline é **determinístico na ordem das etapas**, mas cada etapa individual usa a LLM com tool use para fazer seu trabalho. Isso já é uma arquitetura de agente genuína e é o padrão usado em produção pela maioria das ferramentas reais (não só loops livres). Um "modo avançado" onde a LLM decide se precisa re-extrair dados antes de julgar (ex: currículo mal formatado) é uma boa evolução futura — não é requisito do MVP.

## 3. Arquitetura — pipeline de 4 etapas

```
POST /analisar
     │
     ▼
┌─────────────┐     ┌──────────────┐     ┌────────────┐     ┌─────────────┐
│  1. EXTRAIR │ ──▶ │ 2. COMPARAR  │ ──▶ │ 3. JULGAR  │ ──▶ │ 4. VALIDAR  │
│  vaga → JSON│     │ vaga x cv    │     │ score+gaps │     │ confiança   │
└─────────────┘     └──────────────┘     └────────────┘     └─────────────┘
```

| Etapa | Entrada | Saída | Usa LLM? |
|---|---|---|---|
| 1. Extrair | Texto bruto da vaga | JSON: `{responsabilidades[], requisitos[], skills_criticas[]}` | Sim (tool use, schema fixo) |
| 2. Comparar | JSON da vaga + currículo (texto ou JSON) | JSON: `{skills_presentes[], skills_ausentes[], skills_parciais[]}` | Sim (julgamento semântico: "Vue.js" ≈ "React" mas não é igual) |
| 3. Julgar | Saída da etapa 2 | JSON: `{match_score, red_flags[], justificativa}` | Sim |
| 4. Validar | Saída da etapa 3 | JSON: `{confianca: alta\|media\|baixa, motivo_baixa_confianca?}` | Sim — decide se o restante do resultado deve ser mostrado com aviso |

## 4. Stack técnica (tudo que você já domina)

- **Python 3.11+** e **FastAPI** (endpoint único no MVP: `POST /analisar`)
- **Pydantic** pra schemas de entrada/saída (isso também define os schemas de tool use)
- **Provider de LLM com tool use**: escolha um entre Anthropic Claude, Google Gemini ou OpenAI — todos têm tier gratuito/créditos iniciais. Recomendo começar com o que você já tem mais familiaridade (você já usa Claude Code e Gemini no dia a dia).
- **Sem banco de dados** no MVP — tudo em memória por request. Se quiser persistir histórico de análises, um `analises.json` local resolve, sem exagerar.
- **python-dotenv** pra carregar a API key do `.env` (nunca commitar a chave)
- **Opcional (deixe pro fim):** telinha simples em React reaproveitando o que você já fez no portfólio, consumindo o endpoint via Axios.

## 5. Estrutura de pastas sugerida

```
agente-analisador-vagas/
├── app/
│   ├── main.py              # FastAPI app + rota POST /analisar
│   ├── models.py            # Schemas Pydantic (request/response de cada etapa)
│   ├── agent/
│   │   ├── extrator.py      # Etapa 1
│   │   ├── comparador.py    # Etapa 2
│   │   ├── julgador.py      # Etapa 3
│   │   └── validador.py     # Etapa 4
│   ├── llm_client.py        # Wrapper fino do provider escolhido (facilita trocar depois)
│   └── config.py            # Carrega API key via .env
├── tests/
│   └── test_pipeline.py     # Testes com a LLM mockada (não bater na API de verdade)
├── examples/
│   ├── vaga_exemplo.txt     # Cole uma vaga real da Coamo aqui como fixture
│   └── curriculo_exemplo.json
├── .env.example
├── requirements.txt
├── README.md
└── .gitignore
```

## 6. Contrato da API

**Request** (`POST /analisar`):
```json
{
  "vaga_texto": "texto completo da vaga colado",
  "curriculo": "texto do currículo ou JSON estruturado com skills/experiências"
}
```

**Response**:
```json
{
  "match_score": 42,
  "skills_faltando": ["Power BI", "ETL", "Modelagem multidimensional"],
  "skills_parciais": [{"skill": "SQL analítico", "motivo": "tem SQL transacional via ORM, não analítico"}],
  "red_flags": [
    {"titulo": "...", "descricao": "..."}
  ],
  "confianca": "media",
  "observacoes": "opcional — qualquer nuance que o modelo julgou relevante"
}
```

## 7. Plano de execução (por fases, sem prazo fixo)

Sem cronograma — vá avançando fase por fase, na velocidade que der. Cada fase entrega algo testável antes de passar pra próxima, então dá pra pausar e retomar sem perder o fio.

**Fase 1 — Base do projeto**
1. `git init`, estrutura de pastas, `requirements.txt` (`fastapi`, `uvicorn`, `pydantic`, `python-dotenv`, SDK do provider escolhido).
2. Escreve os schemas Pydantic de cada etapa primeiro (isso trava o "contrato" antes de escrever lógica).
3. Implementa `llm_client.py` com uma função só: manda um prompt + schema de tool use, devolve JSON validado.

**Fase 2 — Metade do pipeline**
1. Implementa as etapas 1 e 2 (extrair, comparar) e testa isoladas no terminal com uma vaga real colada (use uma das da Coamo).
2. Sobe o endpoint `POST /analisar` já rodando as etapas 1 e 2, testa via Swagger UI (`/docs` do FastAPI) ou `curl`.

**Fase 3 — Pipeline completo**
1. Implementa etapas 3 e 4 (julgar, validar) e pluga no pipeline completo.
2. Roda o pipeline end-to-end com pelo menos 2 vagas reais diferentes (ex: as duas da Coamo que você já tem) e revisa se os resultados fazem sentido comparado à análise manual que já fizemos nessa conversa — isso serve de "teste de aceitação" informal.

**Fase 4 — Finalização e publicação**
1. Escreve o `README.md` com: o que o projeto faz, por que conta como agente (pode reaproveitar a seção 2 deste brief), como rodar localmente, e um exemplo real de input/output.
2. `.env.example` sem chave real, `.gitignore` cobrindo `.env` e `__pycache__`.
3. Commits incrementais com mensagens claras (não um commit gigante squash — mostra processo pra quem for olhar o repo).
4. Push pro GitHub.

## 8. Instruções para você, Claude Code

- Antes de escrever qualquer código, pergunte ao usuário: (a) qual provider de LLM ele quer usar (Anthropic/Gemini/OpenAI) e se ele já tem a API key à mão; (b) se ele quer currículo como texto livre colado ou como JSON estruturado no request.
- Construa incrementalmente: uma etapa do pipeline por vez, testando cada uma isoladamente antes de plugar na próxima. Não escreva o pipeline inteiro de uma vez sem testar partes.
- Use tool use / structured output do provider escolhido para cada etapa — não faça parsing manual de texto livre da LLM com regex, isso quebra fácil.
- Nunca hardcode a API key no código. Sempre via `.env` + `python-dotenv`, com `.env.example` no repo (sem valor real).
- Escreva pelo menos um teste que mocka a resposta da LLM (não bata na API de verdade nos testes automatizados — custa dinheiro e trava CI).
- Mantenha o escopo enxuto do MVP: não adicione autenticação, banco de dados, frontend completo ou fila de processamento a menos que o usuário peça explicitamente. O objetivo é ter algo terminado e demonstrável, não um sistema em produção.
- Avance fase por fase (seção 7). Ao final de cada fase, pare, mostre o que está funcionando e confirme com o usuário antes de seguir pra próxima — ele vai trabalhar nisso aos poucos, então cada fase precisa ficar num estado estável e retomável.
- Ao final, gere um `README.md` que sirva como peça de portfólio: precisa ser legível por um recrutador não-técnico, com um exemplo real de input/output.
