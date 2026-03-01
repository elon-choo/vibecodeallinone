#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Knowledge Graph Analytics Module
═══════════════════════════════════════════════════════════════════════════════
지식그래프 사용 분석, 품질 모니터링, 변경 추적 기능 제공

주요 기능:
1. 노드 참조 추적 - 어떤 지식이 언제, 얼마나 참조되었는지
2. 변경 이력 추적 - 노드 생성/수정 타임스탬프
3. 품질 메트릭 - 검색 정확도, 편향 감지
4. 컨텍스트 주입 검증 - 올바른 컨텍스트가 추가되었는지
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from pathlib import Path
import os

logger = logging.getLogger(__name__)

# ═══════════════════════════════════════════════════════════════════════════════
# Data Classes
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class NodeReference:
    """노드 참조 기록"""
    node_id: str
    node_type: str
    node_name: str
    timestamp: str
    tool_used: str
    query: str
    session_id: Optional[str] = None

@dataclass
class ChangeEvent:
    """노드 변경 이벤트"""
    node_id: str
    node_type: str
    node_name: str
    change_type: str  # created, updated, deleted
    timestamp: str
    changed_fields: List[str] = field(default_factory=list)

@dataclass
class QualityMetrics:
    """품질 메트릭"""
    search_precision: float = 0.0  # 검색 정확도
    search_recall: float = 0.0  # 검색 재현율
    context_relevance: float = 0.0  # 컨텍스트 관련성
    type_distribution_entropy: float = 0.0  # 노드 타입 분포 균형
    bias_indicators: Dict[str, float] = field(default_factory=dict)

# ═══════════════════════════════════════════════════════════════════════════════
# Analytics Storage
# ═══════════════════════════════════════════════════════════════════════════════

class AnalyticsStore:
    """분석 데이터 저장소 (파일 기반)"""

    def __init__(self, storage_dir: Optional[str] = None):
        self.storage_dir = Path(storage_dir or os.path.expanduser("~/.claude/mcp-kg-analytics"))
        self.storage_dir.mkdir(parents=True, exist_ok=True)

        self.references_file = self.storage_dir / "references.jsonl"
        self.changes_file = self.storage_dir / "changes.jsonl"
        self.metrics_file = self.storage_dir / "metrics.json"

        # 메모리 캐시 (최근 1000개)
        self.recent_references: List[NodeReference] = []
        self.recent_changes: List[ChangeEvent] = []
        self.max_cache_size = 1000

        # 집계 통계
        self.reference_counts: Dict[str, int] = defaultdict(int)
        self.type_counts: Dict[str, int] = defaultdict(int)
        self.tool_usage: Dict[str, int] = defaultdict(int)

        self._load_cached_stats()

    def _load_cached_stats(self):
        """저장된 통계 로드"""
        try:
            if self.metrics_file.exists():
                with open(self.metrics_file, "r", encoding="utf-8") as f:
                    data = json.load(f)
                    self.reference_counts = defaultdict(int, data.get("reference_counts", {}))
                    self.type_counts = defaultdict(int, data.get("type_counts", {}))
                    self.tool_usage = defaultdict(int, data.get("tool_usage", {}))
        except Exception as e:
            logger.warning(f"Failed to load cached stats: {e}")

    def _save_cached_stats(self):
        """통계 저장"""
        try:
            with open(self.metrics_file, "w", encoding="utf-8") as f:
                json.dump({
                    "reference_counts": dict(self.reference_counts),
                    "type_counts": dict(self.type_counts),
                    "tool_usage": dict(self.tool_usage),
                    "last_updated": datetime.now().isoformat()
                }, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save cached stats: {e}")

    def log_reference(self, ref: NodeReference):
        """참조 기록 추가"""
        # 메모리 캐시에 추가
        self.recent_references.append(ref)
        if len(self.recent_references) > self.max_cache_size:
            self.recent_references.pop(0)

        # 집계 업데이트
        self.reference_counts[ref.node_name] += 1
        self.type_counts[ref.node_type] += 1
        self.tool_usage[ref.tool_used] += 1

        # 파일에 추가
        try:
            with open(self.references_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(ref), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log reference: {e}")

        # 주기적으로 통계 저장
        if len(self.recent_references) % 100 == 0:
            self._save_cached_stats()

    def log_change(self, change: ChangeEvent):
        """변경 이벤트 기록"""
        self.recent_changes.append(change)
        if len(self.recent_changes) > self.max_cache_size:
            self.recent_changes.pop(0)

        try:
            with open(self.changes_file, "a", encoding="utf-8") as f:
                f.write(json.dumps(asdict(change), ensure_ascii=False) + "\n")
        except Exception as e:
            logger.warning(f"Failed to log change: {e}")

    def get_top_referenced(self, limit: int = 20) -> List[Dict]:
        """가장 많이 참조된 노드"""
        sorted_refs = sorted(
            self.reference_counts.items(),
            key=lambda x: x[1],
            reverse=True
        )[:limit]
        return [{"name": name, "count": count} for name, count in sorted_refs]

    def get_recent_references(self, hours: int = 24) -> List[NodeReference]:
        """최근 N시간 내 참조"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            ref for ref in self.recent_references
            if datetime.fromisoformat(ref.timestamp) > cutoff
        ]

    def get_recent_changes(self, hours: int = 24) -> List[ChangeEvent]:
        """최근 N시간 내 변경"""
        cutoff = datetime.now() - timedelta(hours=hours)
        return [
            change for change in self.recent_changes
            if datetime.fromisoformat(change.timestamp) > cutoff
        ]

    def get_type_distribution(self) -> Dict[str, int]:
        """노드 타입별 참조 분포"""
        return dict(self.type_counts)

    def get_tool_distribution(self) -> Dict[str, int]:
        """도구별 사용 분포"""
        return dict(self.tool_usage)


# 전역 인스턴스
_analytics_store: Optional[AnalyticsStore] = None

def get_analytics_store() -> AnalyticsStore:
    """분석 저장소 싱글톤"""
    global _analytics_store
    if _analytics_store is None:
        _analytics_store = AnalyticsStore()
    return _analytics_store

# ═══════════════════════════════════════════════════════════════════════════════
# Reference Tracking
# ═══════════════════════════════════════════════════════════════════════════════

def track_node_reference(
    node_id: str,
    node_type: str,
    node_name: str,
    tool_used: str,
    query: str,
    session_id: Optional[str] = None
):
    """노드 참조 추적"""
    ref = NodeReference(
        node_id=node_id,
        node_type=node_type,
        node_name=node_name,
        timestamp=datetime.now().isoformat(),
        tool_used=tool_used,
        query=query,
        session_id=session_id
    )
    get_analytics_store().log_reference(ref)
    logger.debug(f"Tracked reference: {node_type}:{node_name} via {tool_used}")

def track_node_references_batch(
    results: List[Dict],
    tool_used: str,
    query: str,
    session_id: Optional[str] = None
):
    """배치로 노드 참조 추적"""
    store = get_analytics_store()
    timestamp = datetime.now().isoformat()

    for result in results:
        ref = NodeReference(
            node_id=result.get("id", result.get("name", "unknown")),
            node_type=result.get("type", "Unknown"),
            node_name=result.get("name", "Unknown"),
            timestamp=timestamp,
            tool_used=tool_used,
            query=query,
            session_id=session_id
        )
        store.log_reference(ref)

# ═══════════════════════════════════════════════════════════════════════════════
# Quality Metrics
# ═══════════════════════════════════════════════════════════════════════════════

def calculate_type_bias(type_distribution: Dict[str, int]) -> Dict[str, float]:
    """
    노드 타입 편향 계산

    특정 타입이 과도하게 참조되면 편향 점수가 높아짐
    """
    if not type_distribution:
        return {}

    total = sum(type_distribution.values())
    if total == 0:
        return {}

    # 각 타입의 비율 계산
    ratios = {t: count / total for t, count in type_distribution.items()}

    # 이상적 분포 (균등)와의 차이
    ideal_ratio = 1.0 / len(type_distribution)

    bias = {}
    for node_type, ratio in ratios.items():
        # 편향 점수: 이상적 분포에서 얼마나 벗어났는지
        deviation = abs(ratio - ideal_ratio) / ideal_ratio
        bias[node_type] = round(deviation, 3)

    return bias

def calculate_recency_bias(references: List[NodeReference]) -> float:
    """
    최신성 편향 계산

    최근 추가된 노드가 과도하게 참조되면 편향 점수가 높아짐
    """
    if not references:
        return 0.0

    # 최근 24시간 vs 이전 비율
    now = datetime.now()
    day_ago = now - timedelta(days=1)
    week_ago = now - timedelta(days=7)

    recent_count = sum(
        1 for ref in references
        if datetime.fromisoformat(ref.timestamp) > day_ago
    )
    older_count = sum(
        1 for ref in references
        if day_ago >= datetime.fromisoformat(ref.timestamp) > week_ago
    )

    if older_count == 0:
        return 1.0 if recent_count > 0 else 0.0

    # 비율 기반 편향 (1.0 = 최근에만 집중)
    ratio = recent_count / (recent_count + older_count)
    return round(ratio, 3)

def get_quality_metrics() -> QualityMetrics:
    """품질 메트릭 계산"""
    store = get_analytics_store()

    type_dist = store.get_type_distribution()
    type_bias = calculate_type_bias(type_dist)

    recent_refs = store.get_recent_references(hours=168)  # 1주일
    recency_bias = calculate_recency_bias(recent_refs)

    # 엔트로피 계산 (분포 균형)
    import math
    total = sum(type_dist.values()) if type_dist else 1
    entropy = 0.0
    for count in type_dist.values():
        if count > 0:
            p = count / total
            entropy -= p * math.log2(p)
    max_entropy = math.log2(len(type_dist)) if type_dist else 1
    normalized_entropy = entropy / max_entropy if max_entropy > 0 else 0

    return QualityMetrics(
        type_distribution_entropy=round(normalized_entropy, 3),
        bias_indicators={
            "type_bias": type_bias,
            "recency_bias": recency_bias,
            "entropy_score": round(normalized_entropy, 3)
        }
    )

# ═══════════════════════════════════════════════════════════════════════════════
# Neo4j Integration - 참조 카운트 업데이트
# ═══════════════════════════════════════════════════════════════════════════════

def update_neo4j_access_count(driver, node_name: str, node_type: str):
    """Neo4j 노드의 access_count 업데이트"""
    try:
        with driver.session() as session:
            session.run(f"""
                MATCH (n:{node_type})
                WHERE n.name = $name
                SET n.access_count = coalesce(n.access_count, 0) + 1,
                    n.last_accessed = datetime()
            """, name=node_name)
    except Exception as e:
        logger.warning(f"Failed to update Neo4j access count: {e}")

def get_neo4j_recently_accessed(driver, limit: int = 20) -> List[Dict]:
    """Neo4j에서 최근 접근된 노드 조회"""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.last_accessed IS NOT NULL
                RETURN labels(n)[0] as type,
                       n.name as name,
                       n.access_count as access_count,
                       n.last_accessed as last_accessed
                ORDER BY n.last_accessed DESC
                LIMIT $limit
            """, limit=limit)
            return [dict(r) for r in result]
    except Exception as e:
        logger.warning(f"Failed to get recently accessed nodes: {e}")
        return []

def get_neo4j_top_accessed(driver, limit: int = 20) -> List[Dict]:
    """Neo4j에서 가장 많이 접근된 노드 조회"""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.access_count IS NOT NULL AND n.access_count > 0
                RETURN labels(n)[0] as type,
                       n.name as name,
                       n.access_count as access_count,
                       n.last_accessed as last_accessed
                ORDER BY n.access_count DESC
                LIMIT $limit
            """, limit=limit)
            return [dict(r) for r in result]
    except Exception as e:
        logger.warning(f"Failed to get top accessed nodes: {e}")
        return []

def get_neo4j_recent_changes(driver, hours: int = 24) -> List[Dict]:
    """Neo4j에서 최근 변경된 노드 조회"""
    try:
        with driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE n.updated_at IS NOT NULL
                  AND n.updated_at > datetime() - duration({hours: $hours})
                RETURN labels(n)[0] as type,
                       n.name as name,
                       n.created_at as created_at,
                       n.updated_at as updated_at
                ORDER BY n.updated_at DESC
                LIMIT 50
            """, hours=hours)
            return [dict(r) for r in result]
    except Exception as e:
        logger.warning(f"Failed to get recent changes: {e}")
        return []

# ═══════════════════════════════════════════════════════════════════════════════
# Export Functions for API
# ═══════════════════════════════════════════════════════════════════════════════

def get_analytics_summary() -> Dict:
    """분석 요약 데이터 (대시보드용)"""
    store = get_analytics_store()
    quality = get_quality_metrics()

    return {
        "top_referenced": store.get_top_referenced(10),
        "recent_references_count": len(store.get_recent_references(24)),
        "recent_changes_count": len(store.get_recent_changes(24)),
        "type_distribution": store.get_type_distribution(),
        "tool_distribution": store.get_tool_distribution(),
        "quality_metrics": {
            "entropy_score": quality.type_distribution_entropy,
            "bias_indicators": quality.bias_indicators
        },
        "total_references": sum(store.reference_counts.values()),
        "unique_nodes_referenced": len(store.reference_counts)
    }

def get_reference_timeline(hours: int = 24, interval_minutes: int = 60) -> List[Dict]:
    """시간대별 참조 타임라인"""
    store = get_analytics_store()
    refs = store.get_recent_references(hours)

    # 시간 구간별 집계
    now = datetime.now()
    buckets = defaultdict(int)

    for ref in refs:
        ref_time = datetime.fromisoformat(ref.timestamp)
        # 구간으로 반올림
        bucket = ref_time.replace(
            minute=(ref_time.minute // interval_minutes) * interval_minutes,
            second=0,
            microsecond=0
        )
        buckets[bucket.isoformat()] += 1

    # 빈 구간 채우기
    timeline = []
    current = now - timedelta(hours=hours)
    while current <= now:
        bucket_key = current.replace(
            minute=(current.minute // interval_minutes) * interval_minutes,
            second=0,
            microsecond=0
        ).isoformat()
        timeline.append({
            "time": bucket_key,
            "count": buckets.get(bucket_key, 0)
        })
        current += timedelta(minutes=interval_minutes)

    return timeline
