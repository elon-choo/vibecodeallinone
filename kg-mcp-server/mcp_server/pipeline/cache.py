"""Cache Layer - 검색 결과 캐싱

연구 기반:
- Zep: 72% 토큰 절감
- 응답 시간 최소화

Phase 7.6 업그레이드:
- QueryCache TTL: 30분 → 10분 (코드 변경 빈도 고려, 신선도 우선)
- QueryCache max_size: 500 → 1000 (다양한 쿼리 패턴 커버)
- ContextCache max_size: 200 → 500 (함수/모듈 상세 정보 캐시 확대)
- ContextCache TTL: 1시간 유지 (코드 구조는 비교적 안정적)
"""

import time
import hashlib
from typing import Any, Optional, Callable
from collections import OrderedDict
import logging
import json

logger = logging.getLogger(__name__)


class LRUCache:
    """LRU (Least Recently Used) 캐시"""

    def __init__(self, max_size: int = 1000, ttl: int = 3600):
        """
        Args:
            max_size: 최대 캐시 항목 수
            ttl: 캐시 유효 시간 (초)
        """
        self.max_size = max_size
        self.ttl = ttl
        self.cache: OrderedDict = OrderedDict()
        self.timestamps: dict = {}
        self.stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
        }

    def _make_key(self, key: str) -> str:
        """캐시 키 생성 (해시)"""
        return hashlib.md5(key.encode()).hexdigest()

    def _is_expired(self, key: str) -> bool:
        """만료 여부 확인"""
        if key not in self.timestamps:
            return True
        return time.time() - self.timestamps[key] > self.ttl

    def get(self, key: str) -> Optional[Any]:
        """
        캐시에서 값 조회

        Args:
            key: 캐시 키

        Returns:
            캐시된 값 또는 None
        """
        cache_key = self._make_key(key)

        if cache_key not in self.cache:
            self.stats["misses"] += 1
            return None

        if self._is_expired(cache_key):
            self._remove(cache_key)
            self.stats["misses"] += 1
            return None

        # LRU 업데이트 (가장 최근 사용으로 이동)
        self.cache.move_to_end(cache_key)
        self.stats["hits"] += 1
        return self.cache[cache_key]

    def set(self, key: str, value: Any) -> None:
        """
        캐시에 값 저장

        Args:
            key: 캐시 키
            value: 저장할 값
        """
        cache_key = self._make_key(key)

        # 이미 존재하면 업데이트
        if cache_key in self.cache:
            self.cache.move_to_end(cache_key)
            self.cache[cache_key] = value
            self.timestamps[cache_key] = time.time()
            return

        # 용량 초과 시 가장 오래된 항목 제거
        while len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            self._remove(oldest_key)
            self.stats["evictions"] += 1

        # 새 항목 추가
        self.cache[cache_key] = value
        self.timestamps[cache_key] = time.time()

    def _remove(self, cache_key: str) -> None:
        """캐시 항목 제거"""
        if cache_key in self.cache:
            del self.cache[cache_key]
        if cache_key in self.timestamps:
            del self.timestamps[cache_key]

    def get_or_compute(self, key: str, compute_fn: Callable) -> Any:
        """
        캐시 조회 또는 계산

        Args:
            key: 캐시 키
            compute_fn: 캐시 미스 시 실행할 함수

        Returns:
            캐시된 값 또는 계산된 값
        """
        cached = self.get(key)
        if cached is not None:
            return cached

        result = compute_fn()
        self.set(key, result)
        return result

    def clear(self) -> None:
        """캐시 전체 초기화"""
        self.cache.clear()
        self.timestamps.clear()
        logger.info("Cache cleared")

    def get_stats(self) -> dict:
        """캐시 통계 반환"""
        total = self.stats["hits"] + self.stats["misses"]
        hit_rate = self.stats["hits"] / total if total > 0 else 0

        return {
            **self.stats,
            "size": len(self.cache),
            "max_size": self.max_size,
            "hit_rate": f"{hit_rate:.2%}",
            "ttl_seconds": self.ttl,
        }


class QueryCache(LRUCache):
    """쿼리 결과 전용 캐시"""

    def __init__(self, max_size: int = 1000, ttl: int = 600):
        """
        Args:
            max_size: 최대 캐시 쿼리 수 (Phase 7.6: 500 → 1000)
            ttl: 캐시 유효 시간 (Phase 7.6: 30분 → 10분, 코드 변경 빈도 고려)

        Phase 7.6 근거:
        - TTL 10분: 코드 수정 후 즉시 반영 필요. 30분은 stale 결과 위험.
          MCP 서버 사용 패턴상 10분 내 동일 쿼리 반복이 대부분.
        - max_size 1000: 다양한 쿼리 패턴 + search_type 조합 커버.
          500에서 eviction이 빈번하면 히트율 하락.
        """
        super().__init__(max_size, ttl)

    def make_query_key(self, query: str, search_type: str = "all", limit: int = 10) -> str:
        """쿼리 캐시 키 생성"""
        key_data = {
            "query": query.lower().strip(),
            "type": search_type,
            "limit": limit,
        }
        return json.dumps(key_data, sort_keys=True)

    def get_query_result(self, query: str, search_type: str = "all", limit: int = 10) -> Optional[Any]:
        """쿼리 결과 조회"""
        key = self.make_query_key(query, search_type, limit)
        return self.get(key)

    def set_query_result(self, query: str, result: Any, search_type: str = "all", limit: int = 10) -> None:
        """쿼리 결과 저장"""
        key = self.make_query_key(query, search_type, limit)
        self.set(key, result)


class ContextCache(LRUCache):
    """컨텍스트 캐시 (함수/모듈 상세 정보)"""

    def __init__(self, max_size: int = 500, ttl: int = 3600):
        """
        Args:
            max_size: 최대 캐시 항목 수 (Phase 7.6: 200 → 500)
            ttl: 캐시 유효 시간 (기본 1시간, 코드 구조는 안정적이므로 유지)

        Phase 7.6 근거:
        - max_size 500: smart_context 호출 시 함수/모듈 상세 정보를 빈번히 조회.
          200개 제한에서 eviction 발생 시 재조회 비용이 큼 (Neo4j round-trip).
        """
        super().__init__(max_size, ttl)

    def get_function_context(self, func_name: str) -> Optional[dict]:
        """함수 컨텍스트 조회"""
        return self.get(f"func:{func_name}")

    def set_function_context(self, func_name: str, context: dict) -> None:
        """함수 컨텍스트 저장"""
        self.set(f"func:{func_name}", context)

    def get_module_context(self, module_name: str) -> Optional[dict]:
        """모듈 컨텍스트 조회"""
        return self.get(f"module:{module_name}")

    def set_module_context(self, module_name: str, context: dict) -> None:
        """모듈 컨텍스트 저장"""
        self.set(f"module:{module_name}", context)


# 전역 캐시 인스턴스
query_cache = QueryCache()
context_cache = ContextCache()


def get_cache_stats() -> dict:
    """전체 캐시 통계"""
    return {
        "query_cache": query_cache.get_stats(),
        "context_cache": context_cache.get_stats(),
    }


def clear_all_caches() -> None:
    """모든 캐시 초기화"""
    query_cache.clear()
    context_cache.clear()
    logger.info("All caches cleared")
