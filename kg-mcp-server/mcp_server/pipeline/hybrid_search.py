"""Hybrid Search Engine - 하이브리드 검색 엔진

연구 기반:
- V3_RESEARCH_SYNTHESIS: Graph+Text 하이브리드 100% 합의
- GraphRAG: 29.17% 성능 향상
- LightRAG: Local/Global 이원화

Phase 5.1 업그레이드:
- Fulltext Index 기반 가드레일 검색 (Full Scan 제거)
- 가드레일 결과 5분 TTL 캐시

Phase 6.3 업그레이드:
- Keyword + Vector RRF(Reciprocal Rank Fusion) 병합
- 벡터 검색 fallback 지원

Phase 7.6 업그레이드:
- RRF k=60 → k=20 (벤치마크 기반, 상위 순위 민감도 향상)
- 가드레일/핫스팟을 검색 결과 뒤에 부록으로 배치 (결과 밀림 방지)
- Fulltext Index 기반 _local_search 최적화 (Full Scan 제거)
- vector_weight 0.4 → 0.5 (벤치마크 기반)
"""

from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import logging
import re
import time
import threading
from functools import lru_cache

logger = logging.getLogger(__name__)

# Lucene 특수문자 이스케이프 (한국어 쿼리 + 특수문자 안전)
_LUCENE_SPECIAL = re.compile(r'([+\-&|!(){}[\]^"~*?:\\\/])')

def _escape_lucene(query: str) -> str:
    """Lucene fulltext 쿼리용 특수문자 이스케이프."""
    return _LUCENE_SPECIAL.sub(r'\\\1', query)

# Phase 5.1: Thread-safe 가드레일 캐시 (5분 TTL, max 50 entries)
_guardrail_cache: Dict[str, Any] = {}
_guardrail_cache_lock = threading.Lock()
_GUARDRAIL_CACHE_TTL = 300  # 5 minutes
_GUARDRAIL_CACHE_MAX = 50  # max entries before eviction


class HybridSearchEngine:
    """하이브리드 검색 엔진 (키워드 + 그래프 + 벡터)"""

    def __init__(self, driver):
        """
        Args:
            driver: Neo4j 드라이버
        """
        self.driver = driver

    def search(
        self,
        query: str,
        strategy: dict,
        limit: int = 10
    ) -> List[Dict]:
        """
        하이브리드 검색 실행

        Args:
            query: 검색 쿼리
            strategy: 검색 전략 (QueryRouter에서 생성)
            limit: 최대 결과 수

        Returns:
            검색 결과 리스트
        """
        intent = strategy.get("intent", "hybrid")
        vector_weight = strategy.get("vector_weight", 0.4)

        # Phase 7.6+: NL 쿼리(vector_weight >= 0.5)이면 항상 hybrid로 승격
        # local/global도 벡터 검색 병합하여 GitHub 패턴 등 의미 매칭 포함
        if vector_weight >= 0.5:
            return self._hybrid_search(query, strategy, limit)
        elif intent == "local":
            return self._local_search(query, strategy, limit)
        elif intent == "global":
            return self._global_search(query, strategy, limit)
        else:
            return self._hybrid_search(query, strategy, limit)

    def _local_search(self, query: str, strategy: dict, limit: int) -> List[Dict]:
        """
        Local 검색: 특정 코드 요소 중심

        - 키워드 매칭 우선
        - 1-2 hop 그래프 탐색
        - 함수/클래스 레벨 상세 정보

        Phase 7.6: Fulltext Index(code_fulltext) 사용으로 Full Scan 제거.
        Fulltext 실패 시 기존 CONTAINS 쿼리로 자동 fallback.
        """
        hops = strategy.get("graph_hops", 2)

        with self.driver.session() as session:
            # Phase 7.6: Fulltext Index 기반 검색 (Full Scan 제거)
            safe_query = _escape_lucene(query)
            try:
                result = session.run("""
                    // Phase 7.6: Fulltext Index로 후보 노드 검색
                    CALL db.index.fulltext.queryNodes('code_fulltext', $search_term)
                    YIELD node as n, score as ft_score

                    // 1-2 hop 관계 탐색
                    OPTIONAL MATCH (n)-[:CALLS]->(called:Function)
                    OPTIONAL MATCH (caller:Function)-[:CALLS]->(n)
                    OPTIONAL MATCH (n)-[:DEFINES|HAS_METHOD]->(child)
                    OPTIONAL MATCH (parent)-[:DEFINES|HAS_METHOD]->(n)

                    WITH n, ft_score,
                         collect(DISTINCT called.name)[0..3] as calls,
                         collect(DISTINCT caller.name)[0..3] as called_by,
                         collect(DISTINCT child.name)[0..3] as children,
                         parent.name as parent_name

                    // Fulltext score + 이름 정확도 보너스
                    WITH n, ft_score, calls, called_by, children, parent_name,
                         ft_score * 10 +
                         CASE
                             WHEN toLower(n.name) = toLower($search_term) THEN 100
                             WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 80
                             WHEN toLower(n.name) CONTAINS toLower($search_term) THEN 60
                             ELSE 0
                         END as relevance_score

                    RETURN
                        labels(n)[0] as type,
                        n.name as name,
                        n.qualified_name as qname,
                        n.docstring as doc,
                        n.module as module,
                        n.lineno as lineno,
                        n.args as args,
                        calls,
                        called_by,
                        children,
                        parent_name,
                        relevance_score

                    ORDER BY relevance_score DESC
                    LIMIT $limit
                """, search_term=safe_query, limit=limit)

                results = []
                for record in result:
                    item = dict(record)
                    item["search_mode"] = "local"
                    results.append(item)

                if results:
                    return results
                # Fulltext 결과 없으면 fallback
            except Exception as e:
                logger.warning(f"Fulltext search failed, falling back to CONTAINS: {e}")

            # Fallback: 기존 CONTAINS 기반 검색 (Fulltext 실패 또는 결과 없음)
            result = session.run("""
                MATCH (n)
                WHERE (n:Function OR n:Class OR n:DesignPattern OR n:Strategy)
                AND (
                    toLower(n.name) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.docstring, '')) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.qualified_name, '')) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.ai_description, '')) CONTAINS toLower($search_term)
                )

                OPTIONAL MATCH (n)-[:CALLS]->(called:Function)
                OPTIONAL MATCH (caller:Function)-[:CALLS]->(n)
                OPTIONAL MATCH (n)-[:DEFINES|HAS_METHOD]->(child)
                OPTIONAL MATCH (parent)-[:DEFINES|HAS_METHOD]->(n)

                WITH n,
                     collect(DISTINCT called.name)[0..3] as calls,
                     collect(DISTINCT caller.name)[0..3] as called_by,
                     collect(DISTINCT child.name)[0..3] as children,
                     parent.name as parent_name

                WITH n, calls, called_by, children, parent_name,
                     CASE
                         WHEN toLower(n.name) = toLower($search_term) THEN 100
                         WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 80
                         WHEN toLower(n.name) CONTAINS toLower($search_term) THEN 60
                         ELSE 40
                     END as relevance_score

                RETURN
                    labels(n)[0] as type,
                    n.name as name,
                    n.qualified_name as qname,
                    n.docstring as doc,
                    n.module as module,
                    n.lineno as lineno,
                    n.args as args,
                    calls,
                    called_by,
                    children,
                    parent_name,
                    relevance_score

                ORDER BY relevance_score DESC
                LIMIT $limit
            """, search_term=query, limit=limit)

            results = []
            for record in result:
                item = dict(record)
                item["search_mode"] = "local"
                results.append(item)

            return results

    def _global_search(self, query: str, strategy: dict, limit: int) -> List[Dict]:
        """
        Global 검색: 전체 구조/아키텍처 중심

        - 모듈/패키지 레벨 탐색
        - 넓은 범위 그래프 순회
        - 패턴/개념 노드 포함
        """
        hops = strategy.get("graph_hops", 4)
        keywords = self._extract_keywords(query)

        results = []

        with self.driver.session() as session:
            # 1. 모듈 구조 검색
            module_result = session.run("""
                MATCH (m:Module)
                WHERE any(kw IN $keywords WHERE
                    toLower(m.name) CONTAINS toLower(kw)
                    OR toLower(coalesce(m.filepath, '')) CONTAINS toLower(kw)
                )
                OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)

                WITH m,
                     count(DISTINCT c) as class_count,
                     count(DISTINCT f) as function_count,
                     collect(DISTINCT c.name)[0..5] as classes,
                     collect(DISTINCT f.name)[0..5] as functions

                RETURN
                    'Module' as type,
                    m.name as name,
                    m.filepath as path,
                    class_count,
                    function_count,
                    classes,
                    functions

                ORDER BY class_count + function_count DESC
                LIMIT $limit
            """, keywords=keywords, limit=limit // 2)

            for record in module_result:
                item = dict(record)
                item["search_mode"] = "global"
                results.append(item)

            # 2. 패턴/지식 노드 검색
            pattern_result = session.run("""
                MATCH (p)
                WHERE (p:DesignPattern OR p:SecurityPattern OR p:V3Pattern
                       OR p:CodeSmell OR p:BestPractice)
                AND any(kw IN $keywords WHERE
                    toLower(p.name) CONTAINS toLower(kw)
                    OR toLower(coalesce(p.description, '')) CONTAINS toLower(kw)
                    OR toLower(coalesce(p.intent, '')) CONTAINS toLower(kw)
                )

                RETURN
                    labels(p)[0] as type,
                    p.name as name,
                    p.description as description,
                    p.intent as intent,
                    p.effectiveness_metric as metric,
                    p.category as category

                LIMIT $limit
            """, keywords=keywords, limit=limit // 2)

            for record in pattern_result:
                item = dict(record)
                item["search_mode"] = "global"
                results.append(item)

            # 3. 함수 타입별 통계
            type_result = session.run("""
                MATCH (f:Function)
                WHERE f.function_type IS NOT NULL
                WITH f.function_type as func_type, count(f) as count
                RETURN func_type, count
                ORDER BY count DESC
                LIMIT 5
            """)

            type_stats = {record["func_type"]: record["count"] for record in type_result}
            if type_stats:
                results.append({
                    "type": "Statistics",
                    "name": "Function Types Distribution",
                    "data": type_stats,
                    "search_mode": "global"
                })

        return results


    def _inject_guardrails(self, results: List[Dict]) -> List[Dict]:
        """Phase 5.1: Fulltext Index + Cache 기반 가드레일 주입.

        기존 Full Scan → Fulltext Index 쿼리로 전환.
        동일 컨텍스트에 대해 5분 TTL 캐시 적용.
        Thread-safe with lock.
        """
        if not results:
            return results

        # 캐시 키: 결과의 name 목록만 사용 (hit rate 향상)
        names = sorted(set(str(item.get("name", "")) for item in results if item.get("name")))
        if not names:
            return results
        cache_key = "|".join(names)

        # 캐시 히트 확인 (thread-safe)
        now = time.time()
        with _guardrail_cache_lock:
            cached = _guardrail_cache.get(cache_key)
            if cached and (now - cached["ts"]) < _GUARDRAIL_CACHE_TTL:
                injected = cached["data"]
                if injected:
                    return injected + results
                return results

        # Fulltext Index 검색용 쿼리 구성 (주요 키워드 추출)
        text_context = " ".join(names)
        search_terms = self._extract_keywords(text_context)[:5]
        lucene_query = " OR ".join(search_terms) if search_terms else text_context[:100]

        injected = []
        try:
            with self.driver.session() as session:
                guardrail_result = session.run("""
                    CALL db.index.fulltext.queryNodes('guardrail_fulltext', $search_query)
                    YIELD node, score
                    WHERE score > 0.5
                    RETURN node.name as name, labels(node)[0] as type,
                           node.description as description, score
                    ORDER BY score DESC
                    LIMIT 3
                """, search_query=lucene_query)

                for record in guardrail_result:
                    injected.append({
                        "type": record["type"],
                        "name": record["name"],
                        "doc": "🚨 GUARDRAIL: " + (record["description"] or ""),
                        "search_mode": "guardrail",
                    })
                    if len(injected) >= 2:
                        break
        except Exception as e:
            logger.warning(f"Guardrail fulltext search failed, falling back: {e}")
            injected = self._inject_guardrails_fallback(text_context)

        # 캐시 저장 (thread-safe)
        with _guardrail_cache_lock:
            _guardrail_cache[cache_key] = {"ts": now, "data": injected}
            # Evict expired entries first, then oldest if still over limit
            if len(_guardrail_cache) > _GUARDRAIL_CACHE_MAX:
                expired = [k for k, v in _guardrail_cache.items() if (now - v["ts"]) >= _GUARDRAIL_CACHE_TTL]
                for k in expired:
                    _guardrail_cache.pop(k, None)
                # If still over limit, remove oldest entries
                if len(_guardrail_cache) > _GUARDRAIL_CACHE_MAX:
                    oldest = sorted(_guardrail_cache, key=lambda k: _guardrail_cache[k]["ts"])
                    for k in oldest[:len(_guardrail_cache) - _GUARDRAIL_CACHE_MAX // 2]:
                        _guardrail_cache.pop(k, None)

        if injected:
            return injected + results
        return results

    def _inject_hotspot_warnings(self, results: List[Dict]) -> List[Dict]:
        """Phase 5.3: 검색 결과 중 버그 핫스팟이 있으면 경고 주입."""
        if not results:
            return results
        node_names = [r.get("name") for r in results if r.get("name") and r.get("search_mode") != "guardrail"]
        if not node_names:
            return results
        try:
            from mcp_server.pipeline.bug_radar import BugRadar
            radar = BugRadar(self.driver)
            warnings = radar.get_hotspot_warnings(node_names)
            if warnings:
                return warnings + results
        except Exception as e:
            logger.debug(f"Hotspot injection skipped: {e}")
        return results

    def _inject_guardrails_fallback(self, text_context: str) -> List[Dict]:
        """Fulltext 실패 시 keyword 기반 폴백."""
        text_lower = text_context.lower()
        injected = []
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE (n:SecurityPattern OR n:CodeSmell OR n:BestPractice)
                    AND n.keywords IS NOT NULL
                    RETURN n.name as name, labels(n)[0] as type,
                           n.description as description, n.keywords as keywords
                """)
                for record in result:
                    keywords = record["keywords"]
                    if keywords and any(kw.lower() in text_lower for kw in keywords):
                        injected.append({
                            "type": record["type"],
                            "name": record["name"],
                            "doc": "🚨 GUARDRAIL: " + (record["description"] or ""),
                            "search_mode": "guardrail",
                        })
                        if len(injected) >= 2:
                            break
        except Exception as e:
            logger.error(f"Guardrail fallback also failed: {e}")
        return injected

    def _vector_search(self, query: str, limit: int) -> List[Dict]:
        """Phase 6.3: 벡터 기반 의미 검색.

        VectorSearchEngine을 활용하여 코사인 유사도 기반 검색 수행.
        실패 시 빈 리스트 반환 (keyword 검색으로 fallback).
        """
        try:
            from mcp_server.pipeline.vector_search import VectorSearchEngine
            engine = VectorSearchEngine(self.driver)
            result = engine.semantic_search(query, limit=limit, threshold=0.5)
            if result.get("success"):
                items = result.get("results", [])
                for item in items:
                    item["search_mode"] = "vector"
                return items
        except Exception as e:
            logger.warning(f"Vector search failed, falling back to keyword: {e}")
        return []

    def _rrf_merge(
        self,
        keyword_results: List[Dict],
        vector_results: List[Dict],
        k: int = 20,
        vector_weight: float = 0.5
    ) -> List[Dict]:
        """Weighted Reciprocal Rank Fusion으로 두 검색 결과 병합.

        RRF score = kw_weight/(k + rank_keyword) + vec_weight/(k + rank_vector)

        Phase 10.5: Weighted RRF
        - NL 쿼리 시 vector_weight를 동적으로 적용
        - vector_weight=0.7이면 벡터 결과에 70% 가중, 키워드에 30%
        - 양쪽 모두 있는 결과에 상호검증 보너스 (both_bonus)

        Args:
            keyword_results: 키워드 검색 결과 리스트
            vector_results: 벡터 검색 결과 리스트
            k: RRF 상수 (기본 20)
            vector_weight: 벡터 가중치 (0.0~1.0, 기본 0.5)

        Returns:
            RRF 점수 기준 정렬된 병합 결과
        """
        scores: Dict[str, float] = {}
        items_map: Dict[str, Dict] = {}
        kw_weight = 1.0 - vector_weight

        # 키워드 결과 순위 반영 (가중치 적용)
        kw_names = set()
        for rank, item in enumerate(keyword_results, 1):
            name = item.get("name", "")
            if not name:
                continue
            scores[name] = scores.get(name, 0) + kw_weight / (k + rank)
            items_map[name] = item
            kw_names.add(name)

        # 벡터 결과 순위 반영 (가중치 적용)
        vec_names = set()
        for rank, item in enumerate(vector_results, 1):
            name = item.get("name", "")
            if not name:
                continue
            scores[name] = scores.get(name, 0) + vector_weight / (k + rank)
            vec_names.add(name)
            if name not in items_map:
                items_map[name] = item
            else:
                items_map[name]["similarity"] = item.get("similarity", 0)
                items_map[name]["search_mode"] = "hybrid"

        # 상호검증 보너스: 키워드와 벡터 모두에 있으면 신뢰도 높음
        both_bonus = 0.015
        for name in kw_names & vec_names:
            scores[name] += both_bonus

        # 키워드 1위 정확 매칭 보너스: fulltext/CONTAINS에서 1위면 높은 신뢰도
        if keyword_results:
            top_kw = keyword_results[0]
            top_name = top_kw.get("name", "")
            top_score = top_kw.get("relevance_score", 0)
            if top_name and top_score >= 60:  # 이름 CONTAINS 이상 매칭
                scores[top_name] = scores.get(top_name, 0) + 0.02

        # GitHub 인기 레포 패턴 보너스
        GITHUB_BONUS = 0.008
        for name, item in items_map.items():
            if item.get("repo") or "github:" in str(item.get("namespace", "")):
                scores[name] = scores.get(name, 0) + GITHUB_BONUS

        # RRF 점수 기준 내림차순 정렬
        sorted_names = sorted(scores, key=lambda n: scores[n], reverse=True)

        merged = []
        for name in sorted_names:
            item = items_map[name]
            item["rrf_score"] = round(scores[name], 4)
            merged.append(item)

        return merged

    def _hybrid_search(self, query: str, strategy: dict, limit: int) -> List[Dict]:
        """Hybrid 검색 v3: Keyword + Vector + RRF Fusion (Phase 7.6).

        1. 키워드 검색 (local + global) 실행
        2. 벡터 검색 실행 (vector_weight 기반 limit 계산)
        3. RRF로 두 결과 병합
        4. 검색 결과를 limit만큼 먼저 확보
        5. 가드레일 + 핫스팟은 결과 뒤에 부록으로 추가 (결과 밀림 방지)

        Phase 7.6 변경사항:
        - vector_weight 기본값 0.4 → 0.5 (벤치마크 기반)
        - 가드레일/핫스팟이 core 결과를 밀어내지 않도록 분리
        """
        vector_weight = strategy.get("vector_weight", 0.5)

        # 1. 키워드 검색 (local + global)
        local_results = self._local_search(query, strategy, limit)
        global_results = self._global_search(query, strategy, limit // 2)

        # 키워드 결과 병합 (중복 제거)
        seen = set()
        keyword_results = []
        for item in local_results + global_results:
            name = item.get("name")
            if name and name not in seen:
                seen.add(name)
                keyword_results.append(item)

        # 2. 벡터 검색 (vector_weight 0.5 적용)
        vector_limit = max(3, int(limit * vector_weight))
        vector_results = self._vector_search(query, vector_limit)

        # 3. Weighted RRF 병합 (k=20, Phase 10.5)
        if vector_results:
            merged = self._rrf_merge(keyword_results, vector_results,
                                      vector_weight=vector_weight)
        else:
            # 벡터 검색 실패 시 키워드만 사용
            merged = keyword_results

        # 4. Phase 7.6: Core 결과를 limit만큼 먼저 확보
        core_results = merged[:limit]

        # 5. 가드레일은 core 결과 기반으로 생성하되, 결과 뒤에 부록으로 추가
        guardrail_enriched = self._inject_guardrails(core_results)
        guardrail_items = [
            item for item in guardrail_enriched
            if item.get("search_mode") == "guardrail"
        ]

        # 6. 핫스팟 경고도 마찬가지로 부록으로 추가
        core_names = {r.get("name") for r in core_results if r.get("name")}
        hotspot_enriched = self._inject_hotspot_warnings(core_results)
        hotspot_items = [
            item for item in hotspot_enriched
            if item.get("search_mode") not in ("local", "global", "vector", "hybrid", "guardrail")
            and item.get("name") not in core_names
        ]

        # Phase 8.5: Smart Deduplication — namespace 기반 동명 함수 중복 제거 및 우선순위 조정
        try:
            from mcp_server.pipeline.dedup_engine import DedupEngine
            dedup = DedupEngine(self.driver)
            core_results = dedup.deduplicate_results(core_results)
        except Exception as e:
            logger.debug(f"Dedup skipped: {e}")

        # Core 검색 결과 + 가드레일 부록 (최대 2개) + 핫스팟 부록 (최대 2개)
        return core_results + guardrail_items[:2] + hotspot_items[:2]
    def _extract_keywords(self, query: str) -> List[str]:
        """쿼리에서 키워드 추출"""
        # 불용어 제거
        stopwords = {
            "이", "가", "은", "는", "을", "를", "에", "의", "와", "과",
            "the", "a", "an", "is", "are", "was", "were", "be",
            "to", "of", "and", "in", "that", "have", "for", "on",
            "뭐", "어떤", "어떻게", "무엇", "왜", "어디",
        }

        # 단어 추출
        words = re.findall(r'\b\w+\b', query.lower())
        keywords = [w for w in words if w not in stopwords and len(w) > 1]

        # 최대 5개
        return keywords[:5] if keywords else [query.lower()]

    def get_call_graph(self, func_name: str, depth: int = 2) -> Dict:
        """
        함수 호출 그래프 반환

        Args:
            func_name: 함수 이름
            depth: 탐색 깊이

        Returns:
            호출 그래프 데이터
        """
        # Sanitize depth to prevent Cypher injection (must be int 1-4)
        depth = max(1, min(int(depth), 4))

        # Pre-defined safe Cypher templates keyed by validated depth (no interpolation)
        _OUTGOING_QUERIES = {
            1: "MATCH path = (f:Function)-[:CALLS*1..1]->(called:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
            2: "MATCH path = (f:Function)-[:CALLS*1..2]->(called:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
            3: "MATCH path = (f:Function)-[:CALLS*1..3]->(called:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
            4: "MATCH path = (f:Function)-[:CALLS*1..4]->(called:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
        }
        _INCOMING_QUERIES = {
            1: "MATCH path = (caller:Function)-[:CALLS*1..1]->(f:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
            2: "MATCH path = (caller:Function)-[:CALLS*1..2]->(f:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
            3: "MATCH path = (caller:Function)-[:CALLS*1..3]->(f:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
            4: "MATCH path = (caller:Function)-[:CALLS*1..4]->(f:Function) WHERE f.name = $name OR f.qualified_name CONTAINS $name RETURN [node in nodes(path) | node.name] as path, length(path) as depth LIMIT 20",
        }

        with self.driver.session() as session:
            calls_result = session.run(_OUTGOING_QUERIES[depth], name=func_name)
            callers_result = session.run(_INCOMING_QUERIES[depth], name=func_name)

            return {
                "function": func_name,
                "outgoing": [dict(r) for r in calls_result],
                "incoming": [dict(r) for r in callers_result],
            }

    def get_similar_code(self, query: str, limit: int = 5) -> List[Dict]:
        """
        유사 코드 검색 (docstring 기반)

        Args:
            query: 검색 쿼리
            limit: 최대 결과 수

        Returns:
            유사 코드 리스트
        """
        keywords = self._extract_keywords(query)

        with self.driver.session() as session:
            result = session.run("""
                MATCH (f:Function)
                WHERE f.docstring IS NOT NULL
                AND any(kw IN $keywords WHERE
                    toLower(f.docstring) CONTAINS toLower(kw)
                )

                WITH f,
                     reduce(score = 0, kw IN $keywords |
                         score + CASE WHEN toLower(f.docstring) CONTAINS toLower(kw)
                         THEN 1 ELSE 0 END
                     ) as match_score

                RETURN
                    f.name as name,
                    f.qualified_name as qname,
                    f.docstring as doc,
                    f.module as module,
                    match_score

                ORDER BY match_score DESC
                LIMIT $limit
            """, keywords=keywords, limit=limit)

            return [dict(r) for r in result]
