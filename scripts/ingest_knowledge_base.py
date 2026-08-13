"""
Batch ingestion script — indexes knowledge base documents into Azure AI Search.
Supports JP and EN documents with language-aware chunking.

Usage:
    python scripts/ingest_knowledge_base.py \\
        --source docs/knowledge_base/ \\
        --index ichiba-knowledge-base
"""
from __future__ import annotations
import argparse, asyncio, hashlib, json, logging, pathlib
from datetime import datetime, UTC

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

DOMAIN_MAP = {
    "01_store_management":  "store",
    "02_product_catalog":   "store",
    "03_orders_logistics":  "order",
    "04_payment_settlement":"payment",
    "05_campaigns":         "campaign",
    "06_api_rms":           "api",
    "07_policy_compliance": "policy",
}

def detect_language(filename: str, content: str) -> str:
    if "_ja" in filename or "ja.md" in filename:
        return "ja"
    if "_en" in filename or "en.md" in filename:
        return "en"
    has_cjk = any(0x3000 <= ord(c) <= 0x9FFF for c in content[:500])
    return "ja" if has_cjk else "en"

def chunk_document(content: str, language: str, chunk_size: int | None = None) -> list[str]:
    size = chunk_size or (512 if language == "ja" else 800)
    overlap = 64 if language == "ja" else 100
    separators = ["。\n", "。", "\n\n", "\n"] if language == "ja" else ["\n\n", "\n", ". "]
    # Simple recursive splitting
    chunks, start = [], 0
    while start < len(content):
        end = min(start + size, len(content))
        chunks.append(content[start:end])
        start += size - overlap
    return chunks

async def ingest_directory(source_dir: str, index_name: str) -> None:
    from azure.identity.aio import WorkloadIdentityCredential
    from azure.search.documents.aio import SearchClient
    from openai import AsyncAzureOpenAI
    from backend.config import settings

    credential   = WorkloadIdentityCredential()
    search_client = SearchClient(
        endpoint=settings.AZURE_SEARCH_ENDPOINT,
        index_name=index_name,
        credential=credential,
    )
    aoai_client  = AsyncAzureOpenAI(
        azure_endpoint=settings.AZURE_OPENAI_ENDPOINT,
        azure_ad_token_provider=lambda: credential.get_token(
            "https://cognitiveservices.azure.com/.default"),
        api_version=settings.AZURE_OPENAI_API_VERSION,
    )

    source = pathlib.Path(source_dir)
    docs   = []

    for domain_dir in sorted(source.iterdir()):
        if not domain_dir.is_dir():
            continue
        domain = DOMAIN_MAP.get(domain_dir.name, "store")
        for doc_file in sorted(domain_dir.glob("**/*.md")):
            content  = doc_file.read_text(encoding="utf-8")
            language = detect_language(doc_file.name, content)
            chunks   = chunk_document(content, language)
            logger.info("Ingesting %s — %d chunks (%s)", doc_file.name, len(chunks), language)

            for i, chunk in enumerate(chunks):
                # Embed the chunk
                emb_resp = await aoai_client.embeddings.create(
                    model="embed-3-large-ichiba", input=chunk, dimensions=3072)
                embedding = emb_resp.data[0].embedding

                doc_id = hashlib.md5(f"{doc_file}:{i}".encode()).hexdigest()
                docs.append({
                    "id":              doc_id,
                    "content":         chunk,
                    "content_en":      chunk if language == "en" else "",
                    "domain":          domain,
                    "language":        language,
                    "merchant_tier":   "all",
                    "section_heading": doc_file.stem,
                    "source_url":      str(doc_file),
                    "last_updated":    datetime.now(UTC).isoformat(),
                    "policy_version":  "2026-01",
                    "content_vector":  embedding,
                })

                if len(docs) >= 100:
                    await search_client.upload_documents(documents=docs)
                    logger.info("Uploaded batch of %d documents", len(docs))
                    docs.clear()

    if docs:
        await search_client.upload_documents(documents=docs)
        logger.info("Uploaded final batch of %d documents", len(docs))

    logger.info("✅ Ingestion complete")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source",  default="docs/knowledge_base/")
    parser.add_argument("--index",   default="ichiba-knowledge-base")
    args = parser.parse_args()
    asyncio.run(ingest_directory(args.source, args.index))
