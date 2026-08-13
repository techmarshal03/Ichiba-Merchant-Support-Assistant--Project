# Contributing to Ichiba Merchant Support Assistant

Thank you for contributing! This guide covers the development workflow, standards, and PR checklist.

## Development Setup

```bash
git clone https://github.com/your-org/ichiba-merchant-support.git
cd ichiba-merchant-support
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt -r requirements-dev.txt
python -m spacy download ja_core_news_sm
cp .env.example .env   # fill in your dev values
pre-commit install
```

## Branch Naming

| Type | Pattern | Example |
|---|---|---|
| Feature | `feat/<ticket>-<description>` | `feat/ISS-42-jp-reranker` |
| Bug fix | `fix/<ticket>-<description>` | `fix/ISS-99-redis-timeout` |
| Hotfix | `hotfix/<description>` | `hotfix/prod-injection-bypass` |
| Chore | `chore/<description>` | `chore/upgrade-langgraph-0.4` |

## Code Standards

- **Formatter / Linter:** `ruff` (config in `pyproject.toml`)
- **Type checker:** `mypy --strict`
- **Docstrings:** Google-style, required on all public functions
- **Async:** all I/O must use `async/await` — no blocking calls in agent nodes
- **Secrets:** never hardcode credentials; always use `SecretsManager`

```bash
# Before committing
ruff check backend/ tests/
mypy backend/ --ignore-missing-imports
pytest tests/unit/ -v
```

## PR Checklist

- [ ] Unit tests added / updated
- [ ] `ruff` and `mypy` pass with no new errors
- [ ] No secrets or `.env` values in code
- [ ] Japanese prompts reviewed by a native speaker (for JP-affecting changes)
- [ ] Evaluation score unchanged or improved (`tests/eval/offline_eval.py`)
- [ ] Relevant documentation updated (`docs/`, `README.md`)
- [ ] PR title follows: `<type>(<scope>): <short description>`

## Knowledge Base Updates

To add or update documents in the RAG knowledge corpus:

1. Add/edit files under `docs/knowledge_base/<domain>/`
2. Run ingestion: `python scripts/ingest_knowledge_base.py --source docs/knowledge_base/`
3. Verify retrieval in `jupyter notebooks/01_hybrid_rag_exploration.ipynb`
4. Update the golden dataset if the new content should affect evaluation answers

## Evaluation

The nightly eval pipeline runs automatically in CI. To run locally:

```bash
python tests/eval/offline_eval.py --lang ja --fail-below 0.80
python tests/eval/offline_eval.py --lang en --fail-below 0.80
```

A PR that drops the weighted eval score below 0.77 will be blocked by CI.
