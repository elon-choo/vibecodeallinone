"""Context Pipeline Components v2.0

연구 기반:
- V3_RESEARCH_SYNTHESIS: Graph+Text 하이브리드 100% 합의
- GraphRAG: 29.17% 성능 향상
- LightRAG: Local/Global 이원화
- Zep: 72% 토큰 절감
"""
from .graph_search import GraphSearcher
from .context_builder import ContextBuilder
from .query_router import QueryRouter, QueryIntent, classify_query
from .hybrid_search import HybridSearchEngine
from .cache import (
    LRUCache,
    QueryCache,
    ContextCache,
    query_cache,
    context_cache,
    get_cache_stats,
    clear_all_caches
)

__all__ = [
    # Core (v1)
    "GraphSearcher",
    "ContextBuilder",
    # v2 Components
    "QueryRouter",
    "QueryIntent",
    "classify_query",
    "HybridSearchEngine",
    # Cache
    "LRUCache",
    "QueryCache",
    "ContextCache",
    "query_cache",
    "context_cache",
    "get_cache_stats",
    "clear_all_caches",
]
