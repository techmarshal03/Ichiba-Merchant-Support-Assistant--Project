<div align="center">

# 🏪 Ichiba Merchant Support Assistant

### Multi-Agent Enterprise AI Platform for Rakuten Ichiba Merchants

[![Python](https://img.shields.io/badge/Python-3.12+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![LangGraph](https://img.shields.io/badge/LangGraph-0.4-1C3C3C?style=for-the-badge&logo=langchain&logoColor=white)](https://langchain-ai.github.io/langgraph/)
[![Azure OpenAI](https://img.shields.io/badge/Azure_OpenAI-GPT--4o-0078D4?style=for-the-badge&logo=microsoft-azure&logoColor=white)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)
[![AKS](https://img.shields.io/badge/AKS-Kubernetes-326CE5?style=for-the-badge&logo=kubernetes&logoColor=white)](https://azure.microsoft.com/en-us/products/kubernetes-service)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.115-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg?style=for-the-badge)](LICENSE)

**Multilingual (🇯🇵 JP / 🇺🇸 EN) · LangGraph Multi-Agent · Hybrid RAG · Azure OpenAI · AKS**

[Architecture](#-architecture) · [Features](#-features) · [Tech Stack](#-tech-stack) · [Quick Start](#-quick-start) · [Project Structure](#-project-structure) · [API Reference](#-api-reference) · [Deployment](#-deployment)

</div>

---

## 📋 Overview

The **Ichiba Merchant Support Assistant** is a production-grade, multilingual AI platform that resolves Rakuten Ichiba merchant inquiries 24/7 — across store management, product listings, order processing, payment settlement, campaign participation, RMS API integration, and platform policy.

Built on **LangGraph's hierarchical multi-agent architecture**, every response is grounded in a **Hybrid RAG pipeline** (dense vector + BM25 + Cohere reranker) over the Ichiba knowledge corpus. Low-confidence and high-risk responses are automatically escalated to human agents via Azure Service Bus.

### Key Outcomes

| Metric | Target |
|---|---|
| Query deflection rate | **70–80%** of tier-1 support tickets |
| Response latency P95 | **≤ 3 seconds** (streaming SSE) |
| Response faithfulness | **≥ 0.85** (LLM-as-a-Judge, nightly eval) |
| Languages supported | **Japanese (primary) · English (secondary)** |
| Availability | **99.9%** (AKS multi-zone, Japan East) |
| Compliance | **APPI · GDPR · Rakuten data policies** |

---

## 🏗️ Architecture

### System Architecture Diagram

![Ichiba Merchant Support Architecture](architecture/architecture.png)

### Agent Flow

```
Merchant Query (JP/EN)
       │
       ▼
┌─────────────────────────────────────────────────────────────┐
│              SUPERVISOR AGENT  (GPT-4o)                     │
│  Language Detect → Intent Classify → Route → Confidence Gate│
└───┬──────────┬──────────┬──────────┬──────────┬────────────┘
    ▼          ▼          ▼          ▼          ▼
 [Store]   [Order]   [Payment]  [Campaign]  [API/RMS]  [Policy]
  Agent     Agent     Agent      Agent       Agent      Agent
    └──────────┴──────────┴──────────┴──────────┴────────────┘
                              │
                    HYBRID RAG RETRIEVER
              Dense(vector) + BM25 → RRF → Reranker
                              │
              ┌───────────────┼────────────────┐
         Azure AI Search  Cosmos DB       Redis Cache
          (Vector+BM25)  (Sessions)    (Semantic Cache)
```

### LangGraph Node Graph

```
[START] → [language_detector] → [intent_classifier] → [router]
              │                                           │
              │              ┌────────────────────────────┤
              │              ▼                            ▼
              │    [store|order|payment|              [escalation]
              │     campaign|api|policy]_agent             │
              │              │                             │
              │    [confidence_evaluator]                  │
              │         │         │                        │
              │       pass    retry/escalate ──────────────┤
              │         │                                  │
              │    [hallucination_checker]                  │
              │         │         │                        │
              │        safe     risky ────────────────────┤
              │         │                                  │
              └──→ [response_formatter] → [END]        [END]
```

---

## ✨ Features

### 🤖 Multi-Agent Intelligence
- **Hierarchical Supervisor** — single entry point, delegates to 6 domain specialists
- **ReAct Agents** — Reasoning + Acting loop with domain-specific tools
- **Stateful Sessions** — LangGraph checkpointer persists cross-turn context per merchant
- **Auto-Escalation** — confidence < 0.75 or hallucination risk > 0.35 → human handoff

### 🔍 Hybrid RAG Pipeline
- **Dense Search** — Azure AI Search vector index (text-embedding-3-large, 3072-dim)
- **Sparse BM25** — `ja.microsoft` morphological analyzer for Japanese keyword matching
- **Reciprocal Rank Fusion** — merges dense + sparse rankings
- **Cohere Reranker** — cross-encoder reranking of top-K candidates
- **Metadata Filtering** — domain, language, merchant tier, policy version

### 🌏 Multilingual (JP/EN)
- Language detection: LangDetect + CJK character heuristic + merchant profile fallback
- Locale-native system prompts in Japanese and English
- Mixed-script handling (common in RMS API queries with JP text + EN model names)
- Response formatter appends locale-correct citations and escalation CTAs

### 🔒 Enterprise Security
- **Zero-trust secrets** — Azure Key Vault + Workload Identity (no API keys in code)
- **Prompt injection guard** — pattern + LLM-based, covers JP and EN attack variants
- **PII protection** — Presidio masks merchant IDs, phone numbers, email before logging
- **RBAC** — tool access gated by merchant tier (standard / gold / platinum)
- **Network policy** — deny-all default, explicit ingress allow-list

### 📊 Observability
- LangSmith tracing (every LangGraph node, token counts, routing decisions)
- OpenTelemetry distributed tracing through full call chain
- Prometheus metrics: latency P95, confidence score, escalation rate, RAG score
- Grafana dashboards + Azure Monitor alerts

---

## 🛠️ Tech Stack

| Layer | Technology |
|---|---|
| **Agent Framework** | LangGraph 0.4 + LangChain 0.3 |
| **LLM** | Azure OpenAI GPT-4o (Japan East) |
| **Embeddings** | Azure OpenAI text-embedding-3-large (3072-dim) |
| **Vector Store** | Azure AI Search (S2, Hybrid Search + `ja.microsoft` analyzer) |
| **Reranker** | Cohere multilingual-v3 |
| **Session Store** | PostgreSQL (LangGraph AsyncPostgresSaver) |
| **Merchant Profiles** | Azure Cosmos DB |
| **Semantic Cache** | Azure Cache for Redis (P1) |
| **API Server** | FastAPI 0.115 + Uvicorn |
| **Auth** | Azure Entra ID + JWT + Workload Identity |
| **Secrets** | Azure Key Vault + CSI Driver |
| **Orchestration** | Kubernetes (AKS, Japan East, multi-zone) |
| **CI/CD** | GitHub Actions (canary deploy → staging → production) |
| **Observability** | LangSmith · OpenTelemetry · Prometheus · Grafana · Azure Monitor |
| **PII** | Microsoft Presidio (JP + EN recognizers) |
| **Evaluation** | LLM-as-a-Judge (GPT-4o) · Golden Dataset (300 JP+EN queries) |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.12+
- Docker + kubectl
- Azure subscription (OpenAI, AI Search, Cosmos DB, Redis, Key Vault)
- `az` CLI authenticated

### 1. Clone the repository

```bash
git clone https://github.com/your-org/ichiba-merchant-support.git
cd ichiba-merchant-support
```

### 2. Create virtual environment

```bash
python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
```

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

### 4. Configure environment variables

```bash
cp .env.example .env
# Edit .env with your Azure resource endpoints and Key Vault URL
```

Required variables (all secrets are fetched from Key Vault at runtime):

```env
# Azure Identity
AZURE_TENANT_ID=your-tenant-id
AZURE_CLIENT_ID=your-workload-identity-client-id
KEY_VAULT_URL=https://ichiba-kv.vault.azure.net/

# Azure OpenAI
AZURE_OPENAI_ENDPOINT=https://ichiba-aoai.openai.azure.com/
AZURE_OPENAI_FALLBACK_ENDPOINT=https://ichiba-aoai-sea.openai.azure.com/

# Azure AI Search
AZURE_SEARCH_ENDPOINT=https://ichiba-search.search.windows.net
AZURE_SEARCH_INDEX=ichiba-knowledge-base

# Azure Cosmos DB
COSMOS_ENDPOINT=https://ichiba-cosmos.documents.azure.com/

# Azure Cache for Redis
REDIS_HOST=ichiba-redis.redis.cache.windows.net

# LangSmith (observability)
LANGCHAIN_TRACING_V2=true
LANGCHAIN_PROJECT=ichiba-merchant-support

# Environment
ENVIRONMENT=development
LOG_LEVEL=INFO
```

### 5. Ingest the knowledge base

```bash
python scripts/ingest_knowledge_base.py \
  --source docs/knowledge_base/ \
  --index ichiba-knowledge-base
```

### 6. Run the backend

```bash
uvicorn backend.main:app --reload --host 0.0.0.0 --port 8080
```

API available at: `http://localhost:8080`  
Swagger docs: `http://localhost:8080/docs`

### 7. Run with Docker Compose (local dev)

```bash
docker compose up --build
```

Services: `ichiba-agent:8080` · `postgres:5432` · `redis:6379`

---

## 📁 Project Structure

```
ichiba-merchant-support/
│
├── architecture/
│   ├── architecture.png               ← System architecture diagram
│   ├── agent-flow.png                 ← LangGraph node graph
│   └── sequence-diagram.png           ← Request sequence diagram
│
├── backend/
│   ├── main.py                        ← FastAPI app + lifespan startup
│   ├── config.py                      ← Pydantic settings (reads from Key Vault)
│   │
│   ├── agents/
│   │   ├── graph.py                   ← LangGraph StateGraph builder
│   │   ├── state.py                   ← IchibaAgentState (Pydantic model)
│   │   ├── supervisor.py              ← Language detector, intent classifier, router
│   │   └── specialists/
│   │       ├── base.py                ← Specialist agent factory (ReAct + RAG)
│   │       ├── store_agent.py
│   │       ├── order_agent.py
│   │       ├── payment_agent.py
│   │       ├── campaign_agent.py
│   │       ├── api_agent.py
│   │       └── policy_agent.py
│   │
│   ├── rag/
│   │   ├── retriever.py               ← Hybrid RAG (dense + BM25 + reranker)
│   │   ├── embedder.py                ← Azure OpenAI text-embedding-3-large
│   │   ├── reranker.py                ← Cohere multilingual reranker
│   │   ├── chunker.py                 ← JP/EN language-aware text splitting
│   │   └── query_rewriter.py          ← GPT-4o-mini query normalization
│   │
│   ├── memory/
│   │   ├── checkpointer.py            ← PostgreSQL LangGraph checkpointer
│   │   ├── merchant_profile.py        ← Cosmos DB merchant profile repository
│   │   └── semantic_cache.py          ← Redis semantic cache (cosine ≥ 0.95)
│   │
│   ├── llm/
│   │   ├── azure_openai.py            ← Client: Workload Identity + retry + fallback
│   │   └── prompts/
│   │       ├── ja/                    ← Japanese system prompts per domain
│   │       │   ├── store.txt
│   │       │   ├── order.txt
│   │       │   ├── payment.txt
│   │       │   ├── campaign.txt
│   │       │   ├── api.txt
│   │       │   └── policy.txt
│   │       └── en/                    ← English system prompts per domain
│   │           ├── store.txt
│   │           ├── order.txt
│   │           ├── payment.txt
│   │           ├── campaign.txt
│   │           ├── api.txt
│   │           └── policy.txt
│   │
│   ├── guardrails/
│   │   ├── injection_guard.py         ← Prompt injection detection (JP + EN)
│   │   ├── hallucination_checker.py   ← NLI-based grounding score
│   │   └── pii_protector.py           ← Presidio PII masking
│   │
│   ├── tools/
│   │   ├── registry.py                ← Tool registry + tier-gated loader
│   │   ├── knowledge_search.py        ← Hybrid RAG search tool
│   │   ├── order_lookup.py            ← Order status API tool
│   │   ├── settlement_query.py        ← Payment settlement API tool
│   │   ├── campaign_eligibility.py    ← Campaign check tool
│   │   └── rms_api_docs.py            ← RMS API docs search tool
│   │
│   ├── observability/
│   │   ├── metrics.py                 ← Prometheus counters + histograms
│   │   ├── tracing.py                 ← OpenTelemetry setup
│   │   └── langsmith_config.py        ← LangSmith project config
│   │
│   └── security/
│       ├── auth.py                    ← JWT + Azure Entra ID validation
│       ├── secrets.py                 ← Azure Key Vault client (cached)
│       └── rbac.py                    ← Merchant tier tool permissions
│
├── k8s/
│   ├── production/
│   │   ├── deployment.yaml            ← Deployment + Workload Identity
│   │   ├── service.yaml               ← ClusterIP service
│   │   ├── hpa.yaml                   ← HPA (CPU + Service Bus queue)
│   │   ├── pdb.yaml                   ← PodDisruptionBudget (minAvailable: 2)
│   │   ├── network-policy.yaml        ← Deny-all default network policy
│   │   └── secrets-provider.yaml      ← Azure Key Vault CSI SecretProviderClass
│   └── staging/
│       └── deployment.yaml
│
├── .github/
│   └── workflows/
│       ├── ci.yml                     ← Test + Security scan (every PR)
│       └── deploy.yml                 ← Build → Staging → Canary → Production
│
├── scripts/
│   ├── ingest_knowledge_base.py       ← Batch document ingestion to Azure AI Search
│   ├── create_search_index.py         ← Create/update Azure AI Search index schema
│   └── canary_monitor.py              ← Canary deployment health monitor
│
├── tests/
│   ├── unit/
│   │   ├── test_language_detector.py
│   │   ├── test_intent_classifier.py
│   │   ├── test_hallucination_checker.py
│   │   ├── test_injection_guard.py
│   │   └── test_hybrid_retriever.py
│   ├── integration/
│   │   └── smoke_test.py              ← End-to-end smoke tests (JP + EN)
│   └── eval/
│       ├── offline_eval.py            ← Nightly LLM-as-a-Judge evaluation
│       ├── golden_dataset_ja.jsonl    ← 200 curated JP merchant queries
│       └── golden_dataset_en.jsonl    ← 100 curated EN merchant queries
│
├── docs/
│   ├── knowledge_base/                ← Source documents for RAG ingestion
│   │   ├── 01_store_management/
│   │   ├── 02_product_catalog/
│   │   ├── 03_orders_logistics/
│   │   ├── 04_payment_settlement/
│   │   ├── 05_campaigns/
│   │   ├── 06_api_rms/
│   │   └── 07_policy_compliance/
│   ├── API.md                         ← API reference
│   └── RUNBOOK.md                     ← Operations runbook
│
├── jupyter notebooks/
│   ├── 01_hybrid_rag_exploration.ipynb
│   ├── 02_jp_chunking_analysis.ipynb
│   ├── 03_golden_dataset_curation.ipynb
│   └── 04_evaluation_analysis.ipynb
│
├── architecture/                      ← Architecture diagrams (PNG + source)
├── Dockerfile
├── docker-compose.yml
├── pyproject.toml
├── requirements.txt
├── requirements-dev.txt
├── .env.example
├── .gitignore
├── CONTRIBUTING.md
└── LICENSE
```

---

## 🌐 API Reference

### POST `/v1/chat` — Send merchant message

```bash
curl -X POST http://localhost:8080/v1/chat \
  -H "Authorization: Bearer <jwt_token>" \
  -H "Content-Type: application/json" \
  -d '{
    "message": "スーパーSALEに参加するための条件を教えてください",
    "session_id": "sess_abc123"
  }'
```

**Response (Server-Sent Events)**:
```
data: {"content": "スーパーSALEへの参加条件は以下の通りです...", "done": false}
data: {"content": "\n\n【参照: キャンペーン参加ガイドv2.1】", "done": true}
data: [DONE]
```

### GET `/v1/sessions/{session_id}` — Get session history

### GET `/health/live` — Liveness probe

### GET `/health/ready` — Readiness probe (checks PostgreSQL, Redis, Azure Search)

### GET `/metrics` — Prometheus metrics

Full API documentation: `http://localhost:8080/docs` (Swagger UI)

---

## 🧠 Hybrid RAG Pipeline

```
Merchant Query
      │
      ▼
Query Rewriter (GPT-4o-mini)         ← Normalize JP kanji variants, expand abbreviations
      │
  ┌───┴───┐
  ▼       ▼
Dense   Sparse
Vector  BM25                         ← ja.microsoft analyzer (morphological tokenization)
Search  Search
  │       │
  └───┬───┘
      │  Reciprocal Rank Fusion (α=0.6 dense / 0.4 sparse)
      ▼
  Cohere Reranker                    ← multilingual-v3 cross-encoder, top-5
      │
  Metadata Filter                    ← domain, language (ja/en/bilingual), merchant_tier
      │
  Context Assembler                  ← ≤ 6K tokens, section headings, source URLs
```

**Why Hybrid RAG for Japanese:**
- Dense search handles semantic paraphrases ("注文取消" ≈ "キャンセル処理")  
- BM25 catches exact Rakuten terms: `スーパーSALE出店料`, `RMS API v2.0`
- `ja.microsoft` correctly tokenizes Japanese without word boundaries

---

## 🚢 Deployment

### AKS Cluster Setup

```bash
# Create AKS cluster (Japan East, multi-zone)
az aks create \
  --resource-group ichiba-rg-prod \
  --name ichiba-aks-prod \
  --location japaneast \
  --zones 1 2 3 \
  --node-count 3 \
  --node-vm-size Standard_DS4_v3 \
  --enable-workload-identity \
  --enable-oidc-issuer \
  --attach-acr ichiba

# Install CSI secrets driver
az aks enable-addons \
  --addons azure-keyvault-secrets-provider \
  --name ichiba-aks-prod \
  --resource-group ichiba-rg-prod
```

### Deploy to AKS

```bash
# Apply manifests
kubectl apply -f k8s/production/

# Check rollout
kubectl rollout status deployment/ichiba-agent -n merchant-support

# Watch HPA
kubectl get hpa ichiba-agent-hpa -n merchant-support --watch
```

### CI/CD Flow

```
PR merged to main
      │
      ▼
  [test]                   ← pytest + offline eval (JP + EN golden datasets)
      │
  [security]               ← Trivy (container scan) + Bandit (Python SAST)
      │
  [build]                  ← Docker build → push to Azure Container Registry
      │
  [deploy-staging]         ← Apply to staging AKS
      │
  [smoke-test]             ← End-to-end tests (JP + EN scenarios)
      │
  [deploy-production]      ← Manual approval gate
      │
  Canary 10% → monitor 5 min → promote to 100%
  (auto-rollback if error rate > 1% or P95 > 5s)
```

---

## 🧪 Testing & Evaluation

### Unit tests

```bash
pytest tests/unit/ -v --cov=backend
```

### Integration smoke tests

```bash
python tests/integration/smoke_test.py \
  --endpoint http://localhost:8080 \
  --languages ja en \
  --scenarios store order payment campaign api policy
```

### Nightly offline evaluation

```bash
python tests/eval/offline_eval.py \
  --lang ja \
  --dataset tests/eval/golden_dataset_ja.jsonl \
  --fail-below 0.80
```

**Evaluation rubric (LLM-as-a-Judge):**

| Metric | Weight | Target |
|---|---|---|
| Faithfulness | 35% | ≥ 0.85 |
| Relevance | 30% | ≥ 0.80 |
| Completeness | 20% | ≥ 0.75 |
| Citation quality | 15% | ≥ 0.80 |
| **Overall weighted** | **100%** | **≥ 0.80** |

---

## 💰 Cost Model

| Component | Config | Monthly |
|---|---|---|
| GPT-4o input (150M tokens) | $2.50/1M | $375 |
| GPT-4o output (30M tokens) | $10.00/1M | $300 |
| GPT-4o-mini (200M tokens) | $0.15/1M | $30 |
| text-embedding-3-large (500M) | $0.13/1M | $65 |
| Azure AI Search (S2, 2 replicas) | managed | $1,000 |
| Azure Cosmos DB | 10K RU/s | $600 |
| Azure Cache for Redis (P1) | 6GB | $550 |
| AKS (DS4_v3 × 6 avg) | on-demand | $800 |
| **Base Total** | | **~$3,720/mo** |
| **With semantic cache (40% hit rate)** | | **~$2,600/mo** |

---

## 🔐 Security

- **Zero secrets in code** — all credentials fetched from Azure Key Vault via Workload Identity
- **Prompt injection guard** — regex + LLM classifier covering JP and EN attack patterns
- **PII masking** — Microsoft Presidio with JP-specific recognizers (phone, merchant ID, email)
- **RBAC** — tool permissions by merchant tier: standard → gold → platinum
- **APPI compliant** — data residency Japan East, PII logged only in masked form
- **Network isolation** — AKS deny-all network policy with explicit allow-list

> ⚠️ **Never commit `.env` files** — all runtime secrets are managed by Azure Key Vault.

---

## 🤝 Contributing

See [CONTRIBUTING.md](CONTRIBUTING.md) for development guidelines, branch naming conventions, and PR checklist.

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

**Built with ❤️ for Rakuten Ichiba Merchants**

[LangGraph](https://langchain-ai.github.io/langgraph/) · [Azure OpenAI](https://azure.microsoft.com/en-us/products/ai-services/openai-service) · [Azure AI Search](https://azure.microsoft.com/en-us/products/ai-services/ai-search) · [AKS](https://azure.microsoft.com/en-us/products/kubernetes-service)

</div>
