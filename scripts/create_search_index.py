"""
Create Azure AI Search index with hybrid vector + BM25 configuration.
Run once before ingesting documents.

Usage:
    python scripts/create_search_index.py
"""
import asyncio
import logging

from azure.identity import DefaultAzureCredential
from azure.search.documents.indexes import SearchIndexClient
from azure.search.documents.indexes.models import (
    HnswAlgorithmConfiguration,
    SearchableField,
    SearchField,
    SearchFieldDataType,
    SearchIndex,
    SemanticConfiguration,
    SemanticField,
    SemanticPrioritizedFields,
    SemanticSearch,
    SimpleField,
    VectorSearch,
    VectorSearchProfile,
)

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

ENDPOINT = "https://<your-search-service>.search.windows.net"
INDEX_NAME = "ichiba-knowledge-base"


def create_index() -> None:
    credential = DefaultAzureCredential()
    client = SearchIndexClient(endpoint=ENDPOINT, credential=credential)

    fields = [
        SimpleField(name="id", type=SearchFieldDataType.String, key=True),
        SearchableField(
            name="content",
            type=SearchFieldDataType.String,
            analyzer_name="ja.microsoft",   # Japanese morphological tokenizer
        ),
        SearchableField(
            name="content_en",
            type=SearchFieldDataType.String,
            analyzer_name="en.microsoft",
        ),
        SimpleField(name="domain", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="language", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="merchant_tier", type=SearchFieldDataType.String, filterable=True),
        SimpleField(name="source", type=SearchFieldDataType.String, retrievable=True),
        SearchField(
            name="content_vector",
            type=SearchFieldDataType.Collection(SearchFieldDataType.Single),
            searchable=True,
            vector_search_dimensions=3072,
            vector_search_profile_name="hnsw-profile",
        ),
    ]

    vector_search = VectorSearch(
        algorithms=[HnswAlgorithmConfiguration(name="hnsw-algo", parameters={"m": 4, "efConstruction": 400})],
        profiles=[VectorSearchProfile(name="hnsw-profile", algorithm_configuration_name="hnsw-algo")],
    )

    semantic_search = SemanticSearch(
        configurations=[
            SemanticConfiguration(
                name="semantic-config",
                prioritized_fields=SemanticPrioritizedFields(
                    content_fields=[SemanticField(field_name="content")]
                ),
            )
        ]
    )

    index = SearchIndex(
        name=INDEX_NAME,
        fields=fields,
        vector_search=vector_search,
        semantic_search=semantic_search,
    )

    result = client.create_or_update_index(index)
    log.info("Index '%s' created/updated ✓", result.name)
    log.info("Fields: %s", [f.name for f in result.fields])


if __name__ == "__main__":
    create_index()
