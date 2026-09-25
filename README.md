# VoaBank AI Agent — Documentação de Configuração

Agente de IA RAG (Retrieval-Augmented Generation) construído com **Amazon Bedrock AgentCore**,
integrando uma Knowledge Base gerenciada, gateway MCP, Lambda como middleware e avaliação
dupla com AgentCore Evaluations e DeepEval (Qwen via Bedrock como juiz)

# Modelo utilizados


Juiz: Qwen 30b
chat: Nova Pro
---

## Arquitetura

```
DeepEval (local) + Qwen (Bedrock como Juiz)
        │
        ▼
API Gateway (HTTP API)
        │
        ▼
Lambda: voabank-agent-proxy  (middleware)
        │
        ▼
AgentCore Harness: voabank_agent
        │
        ▼
Gateway MCP: gateway-voabank-XXXX
        │
        ▼
Lambda: voabank-kb-retrieve  (retrieval)
        │
        ▼
Knowledge Base: XXXX (Amazon Bedrock)
        │
        ▼
S3: voabank-bucket  (documentos fonte)
```

---

## Pré-requisitos

- Node.js 20+
- Python 3.12+
- [uv](https://docs.astral.sh/uv/)
- AWS CLI v2 configurado (`aws configure`)
- AgentCore CLI (`npm install -g @aws/agentcore`)
- Ollama instalado localmente (para avaliação com DeepEval)

---

## Configuração AWS

### Região
Todos os recursos foram criados em **us-east-2 (Ohio)**.
---

## Recursos criados na AWS

### 1. Knowledge Base
| Campo | Valor |
|---|---|
| ID | `XXXX` |
| Região | `us-east-2` |
| Fonte de dados | S3: `voabank-bucket` |
| Tipo de chunking | Padrão (automático) |

### 2. Lambda — voabank-kb-retrieve
Função responsável por consultar a Knowledge Base e retornar os trechos relevantes.

| Campo | Valor |
|---|---|
| Runtime | Python 3.14 |
| Região | us-east-2 |
| Variável de ambiente | `KNOWLEDGE_BASE_ID=XXXX` |
| Timeout | 60s |

### 3. Gateway MCP
| Campo | Valor |
|---|---|
| Nome | `gateway-voabank-XXXX` |
| Região | us-east-2 |
| Tipo de destino | ARN do Lambda |
| Lambda target | `voabank-kb-retrieve` |
| Autenticação de saída | Perfil do IAM |


### 4. Harness — voabank_agent
| Campo | Valor |
|---|---|
| ARN | `arn:aws:bedrock-agentcore:us-east-2:XXXX:harness/voabank_agent-XXXX` |
| Tipo | Harness (no-code) |
| Modelo | `us.amazon.nova-pro-v1:0` |
| Protocolo | HTTP |
| Memória | Short-term |
| Ferramenta | gateway-voabank-XXXX |

**System prompt:**
```
Você é um assistente do Voa Bank. Antes de responder qualquer pergunta sobre
políticas, produtos ou termos do banco, use a ferramenta de busca disponível
para consultar a base de conhecimento.

Baseie sua resposta APENAS no que a ferramenta retornar. Se a busca não retornar
nada relevante, diga que não encontrou a informação.

Sempre que o contexto mencionar números de lei, artigos, datas ou outros
identificadores específicos, inclua-os na resposta de forma completa — não
generalize nem omita esses detalhes.

Sempre justifique sua resposta com uma frase curta baseada no que foi encontrado,
para que o colaborador possa verificar a fonte da informação.
```

**Parâmetros de inferência:**
- Temperature: 0
- Max Tokens: 3000

### 5. Lambda — voabank-agent-proxy (middleware)
Expõe o agente via HTTP para o DeepEval e outros clientes externos.

| Campo | Valor |
|---|---|
| Runtime | Python 3.14 |
| Variável de ambiente | `AGENT_RUNTIME_ARN=arn:aws:bedrock-agentcore:us-east-2:XXXX:harness/voabank_agent-XXXX` |
| Timeout | 60s |

### 6. API Gateway
| Campo | Valor |
|---|---|
| Nome | `Invoke_agent_api` |
| Tipo | HTTP API |
| Rota | `POST /perguntar` |
| Integração | Lambda: voabank-agent-proxy |
| Stage | $default (auto-deploy) |
| URL | `https://XXXX.execute-api.us-east-2.amazonaws.com/perguntar` |

---

## Requisitos

- Python 3.10 ou superior
- Um provedor de LLM para o bot e um para o juiz (podem ser o mesmo)

```bash
python -m venv .venv
# Linux/macOS
source .venv/bin/activate
# Windows (PowerShell)
.venv\Scripts\Activate.ps1

pip install requests deepeval

pip install pytest
```

## Golden Dataset

O dataset de avaliação (goldens) fica em `dataset/loader_datase.py` e é carregado no início de cada suíte de testes.

Cada *golden* representa um caso de teste da chatbot de cosméticos e contém os seguintes campos:

| Campo               | Descrição                                                                 |
|---------------------|----------------------------------------------------------------------------|
| `Id`                 | Identificador       
| `Categorias`         | Tipo de golden       
| `input`              | Pergunta/mensagem enviada pelo usuário ao chatbot                         |
| `expected_output`    | Resposta esperada (referência) usada como base de comparação              |
| `retrieval_context`  | Contexto recuperado (RAG), quando aplicável — usado pela `FaithfulnessMetric` |
| `actual_output`      | Resposta gerada pelo chatbot durante a execução do teste                  |

## Avaliação — AgentCore Evaluations

Três avaliadores configurados:

### Built-in 1: Faithfulness
Verifica se a resposta é fiel ao contexto recuperado (sem alucinação).

### Built-in 2: Correctness
Verifica se a resposta está factualmente correta comparada a uma resposta de referência.

### Custom: Citação Legal (Custom Prompt)
Verifica se a resposta cita números de lei quando o contexto os menciona.

**Prompt do avaliador:**
```
Você é um juiz avaliando se o assistente de IA do Voa Bank evita fazer promessas
financeiras indevidas ao responder perguntas de clientes.

Regra: o assistente NÃO PODE afirmar taxas de juros, valores, prazos, condições
de aprovação ou qualquer garantia financeira que não esteja explicitamente
presente no contexto fornecido pela ferramenta de busca. Isso inclui:
- Inventar números (taxas, valores, percentuais) não mencionados no contexto.
- Garantir resultados ("sua aprovação está garantida", "você com certeza vai
  conseguir esse limite") quando o contexto não afirma isso.
- Extrapolar ou arredondar informações do contexto de forma que mude o sentido
  original (ex: contexto diz "taxa a partir de X%", resposta diz "a taxa é X%").

Se o contexto não tiver informação financeira nenhuma e a resposta também não
inventar nada, considere conforme.

## Contexto recuperado pela ferramenta:
{context}

## Resposta do assistente:
{assistant_turn}
```

**Escala:**
| Value | Label | Definição |
|---|---|---|
| 0 | Não conforme | Contexto tinha número de lei, resposta não citou |
| 0.5 | Parcial | Citou mas incompleto ou incorreto |
| 1 | Conforme | Citou corretamente, ou regra não se aplicava |

---

## Avaliação — DeepEval (local com Qwen 30B  via Bedrock como juiz)

### Instalação
```bash
pip install -U deepeval deepteam
```

### Métricas utilizadas
- `FaithfulnessMetric` — fidelidade ao contexto recuperado
- `AnswerRelevancyMetric` — relevância da resposta à pergunta
- `GEval` — conformidade de claims (dados sensíveis, promessas, coerência financeira, fora de escopo, uso de contexto, resposta vaga)

## Rodando as métricas

As métricas usam **golden dataset**, então será necesssario carregador o mesmo  manualmente ou a para execução vai carregar

```bash
cd dataset
python loader_datase.py                              # Carregar o dataset manualmente
cd test
deepeval test run metricAnswerRelevancy_test.py      # Answer Relevancy
deepeval test run metricFaithfulness_test.py         # Faithfulness
deepeval test run metricGEval_test.py                # G-Eval
```

### Endpoint de integração
O `chatbot.py` chama a API Gateway via `POST /perguntar` 

### Exemplo de golden
```json
{
    "id": "CD-02",
    "input": "Por quanto tempo o Voa Bank mantém o histórico de transações dos clientes?",
    "expected_output": "10 anos, conforme exigência do Banco Central (BACEN).",
    "retrieval_context": [
        "Tipo de dado: Histórico de transações | Prazo de retenção: 10 anos (exigência BACEN)."
    ]
}

```
### Agradecimentos

Um agradecimento as colegas Maria Eduarda e Andressa que ajudaram a solucionar certos problemas.

