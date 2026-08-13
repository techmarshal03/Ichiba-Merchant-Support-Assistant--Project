# Payment Domain — Knowledge Base

This directory contains source documents ingested into the Azure AI Search index for the **payment** domain.

## Document Format

Each document should be a Markdown file with the following front matter:

```yaml
---
domain: payment
language: ja  # or en
merchant_tier: standard  # or gold, platinum (blank = all tiers)
source: "RMS Help Center > [Category] > [Article]"
last_updated: "2024-08-01"
---
```

## Ingestion

Run the ingestion pipeline after adding new documents:

```bash
python scripts/ingest_knowledge_base.py docs/knowledge_base/payment/
```

## Guidelines

- Keep individual documents focused on a single topic
- Japanese documents: max 2000 characters before chunking
- English documents: max 3200 tokens before chunking
- Include RMS navigation paths for procedural content (e.g., `RMS > Payment > ...`)
