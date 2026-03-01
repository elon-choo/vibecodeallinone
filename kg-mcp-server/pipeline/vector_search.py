"""
Vector Search Engine (Phase 6.2)
================================
OpenAI 임베딩 기반 의미 검색.
"비동기 파일 읽기" 같은 자연어 쿼리로 관련 함수 검색 가능.

MCP 도구: semantic_search(query, limit, threshold)
"""
import logging
import hashlib
import time
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)

# 쿼리 임베딩 캐시 (동일 쿼리 반복 방지)
_query_cache: Dict[str, Any] = {}
_CACHE_TTL = 300  # 5분
_MAX_CACHE = 100


class VectorSearchEngine:
    """임베딩 기반 의미 검색 엔진"""

    def __init__(self, driver):
        self.driver = driver
        self._embedding_pipeline = None

    @property
    def embedding_pipeline(self):
        """Lazy init"""
        if self._embedding_pipeline is None:
            from mcp_server.pipeline.embedding_pipeline import EmbeddingPipeline
            self._embedding_pipeline = EmbeddingPipeline(self.driver)
        return self._embedding_pipeline

    def semantic_search(
        self,
        query: str,
        limit: int = 10,
        threshold: float = 0.7,
        node_type: str = "all"
    ) -> Dict[str, Any]:
        """의미 기반 벡터 검색.

        Args:
            query: 자연어 검색 쿼리
            limit: 최대 결과 수
            threshold: 코사인 유사도 임계값 (0.0~1.0)
            node_type: "function", "class", "all"

        Returns:
            검색 결과 딕셔너리
        """
        if not query or not query.strip():
            return {"success": False, "error": "Query is empty."}

        # 캐시 확인
        cache_key = self._cache_key(query, limit, threshold, node_type)
        cached = self._get_cached(cache_key)
        if cached:
            return cached

        try:
            # 1. 쿼리 임베딩
            query_embedding = self.embedding_pipeline.embed_text(query)
            if not query_embedding:
                return {"success": False, "error": "Failed to embed query."}

            results = []

            # 2. Function 검색
            if node_type in ("function", "all"):
                func_results = self._vector_query(
                    query_embedding, "Function", "code_embeddings", limit, threshold
                )
                results.extend(func_results)

            # 3. Class 검색
            if node_type in ("class", "all"):
                class_results = self._vector_query(
                    query_embedding, "Class", "class_embeddings", limit, threshold
                )
                results.extend(class_results)

            # 4. DesignPattern + Strategy 검색
            if node_type == "all":
                for idx_label, idx_name in [("DesignPattern", "pattern_embeddings"),
                                              ("Strategy", "strategy_embeddings")]:
                    try:
                        extra = self._vector_query(
                            query_embedding, idx_label, idx_name, limit // 2, threshold
                        )
                        results.extend(extra)
                    except Exception:
                        pass  # 인덱스가 없으면 무시

            # 유사도 기준 정렬
            results.sort(key=lambda x: x.get("similarity", 0), reverse=True)
            results = results[:limit]

            result = {
                "success": True,
                "query": query,
                "results": results,
                "total": len(results),
                "threshold": threshold,
            }

            # 캐시 저장
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"Semantic search failed: {e}")
            return {"success": False, "error": str(e)}

    def _vector_query(
        self,
        query_embedding: List[float],
        label: str,
        index_name: str,
        limit: int,
        threshold: float
    ) -> List[Dict]:
        """Neo4j 벡터 인덱스 쿼리"""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    CALL db.index.vector.queryNodes($index_name, $top_k, $embedding)
                    YIELD node, score
                    WHERE score >= $threshold
                    OPTIONAL MATCH (node)-[:CALLS]->(called:Function)
                    OPTIONAL MATCH (caller:Function)-[:CALLS]->(node)
                    RETURN
                        node.name AS name,
                        node.qualified_name AS qname,
                        node.docstring AS docstring,
                        node.module AS module,
                        node.args AS args,
                        node.file_path AS file_path,
                        node.namespace AS namespace,
                        node.repo AS repo,
                        node.category AS category,
                        labels(node)[0] AS type,
                        score AS similarity,
                        collect(DISTINCT called.name)[0..3] AS calls,
                        collect(DISTINCT caller.name)[0..3] AS called_by
                    ORDER BY score DESC
                    LIMIT $limit
                """,
                    index_name=index_name,
                    top_k=limit * 2,  # 넉넉하게 가져온 후 threshold 필터
                    embedding=query_embedding,
                    threshold=threshold,
                    limit=limit
                )
                return [dict(r) for r in result]
        except Exception as e:
            logger.warning(f"Vector query for {label} failed: {e}")
            return []

    def _cache_key(self, query, limit, threshold, node_type) -> str:
        raw = f"{query}:{limit}:{threshold}:{node_type}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict]:
        cached = _query_cache.get(key)
        if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: Dict):
        _query_cache[key] = {"ts": time.time(), "data": data}
        # 캐시 크기 제한
        if len(_query_cache) > _MAX_CACHE:
            oldest = sorted(_query_cache, key=lambda k: _query_cache[k]["ts"])
            for k in oldest[:_MAX_CACHE // 2]:
                del _query_cache[k]
