"""
Cross-Project Knowledge Transfer (Phase 5.6)
=============================================
프로젝트 간 지식 전이 시스템.

1. 검증된 패턴 (relevance_score > 1.5) → GLOBAL namespace 승격
2. Anti-Pattern Registry: 반복 실패 패턴 전역 경고 등록
3. Global Insights: 모든 프로젝트에서 축적된 베스트 프랙티스 조회
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)

GLOBAL_NAMESPACE = "__GLOBAL__"
PROMOTION_THRESHOLD = 1.5
ANTI_PATTERN_THRESHOLD = 0.3  # relevance < 0.3이면 anti-pattern 후보


class KnowledgeTransfer:
    """프로젝트 간 지식 전이 엔진"""

    def __init__(self, driver):
        self.driver = driver

    def promote_pattern(self, name: str) -> Dict[str, Any]:
        """검증된 패턴을 GLOBAL namespace로 승격.

        조건: relevance_score >= 1.5
        """
        try:
            with self.driver.session() as session:
                # 1. 자격 확인
                check = session.run("""
                    MATCH (n) WHERE n.name = $name
                    RETURN n.name AS name, labels(n)[0] AS type,
                           n.relevance_score AS score,
                           n.namespace AS ns
                """, name=name).single()

                if not check:
                    return {"success": False, "error": f"Node '{name}' not found."}

                score = check["score"] or 0
                if score < PROMOTION_THRESHOLD:
                    return {
                        "success": False,
                        "error": f"Score {score} < {PROMOTION_THRESHOLD}. 더 많은 성공 피드백이 필요합니다.",
                    }

                if check["ns"] == GLOBAL_NAMESPACE:
                    return {"success": False, "error": f"'{name}' is already GLOBAL."}

                # 2. GLOBAL 승격
                session.run("""
                    MATCH (n) WHERE n.name = $name
                    SET n.original_namespace = n.namespace,
                        n.namespace = $global_ns,
                        n.promoted_at = datetime(),
                        n:GlobalPattern
                """, name=name, global_ns=GLOBAL_NAMESPACE)

                return {
                    "success": True,
                    "name": name,
                    "previous_namespace": check["ns"],
                    "score": score,
                    "message": f"'{name}'이(가) GLOBAL namespace로 승격되었습니다."
                }

        except Exception as e:
            logger.error(f"Promotion failed: {e}")
            return {"success": False, "error": str(e)}

    def get_global_insights(self, limit: int = 10) -> Dict[str, Any]:
        """모든 프로젝트에서 축적된 글로벌 인사이트 반환."""
        try:
            with self.driver.session() as session:
                # 1. 고득점 글로벌 패턴
                global_result = session.run("""
                    MATCH (n)
                    WHERE n.namespace = $global_ns OR n:GlobalPattern
                    RETURN n.name AS name, labels(n)[0] AS type,
                           n.relevance_score AS score,
                           n.original_namespace AS origin,
                           LEFT(COALESCE(n.docstring, n.description, ''), 100) AS description
                    ORDER BY n.relevance_score DESC
                    LIMIT $limit
                """, global_ns=GLOBAL_NAMESPACE, limit=limit)
                global_patterns = [dict(r) for r in global_result]

                # 2. 크로스 프로젝트 고성능 노드 (승격 안 됐지만 점수 높은)
                candidates = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class OR n:DesignPattern OR n:BestPractice)
                    AND COALESCE(n.relevance_score, 0.5) >= $threshold
                    AND COALESCE(n.namespace, '') <> $global_ns
                    RETURN n.name AS name, labels(n)[0] AS type,
                           n.relevance_score AS score,
                           n.namespace AS namespace
                    ORDER BY n.relevance_score DESC
                    LIMIT $limit
                """, threshold=PROMOTION_THRESHOLD, global_ns=GLOBAL_NAMESPACE, limit=limit)
                promotion_candidates = [dict(r) for r in candidates]

                # 3. Anti-patterns (반복 실패)
                anti = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class)
                    AND COALESCE(n.relevance_score, 0.5) < $threshold
                    AND n.last_useful IS NOT NULL
                    RETURN n.name AS name, labels(n)[0] AS type,
                           n.relevance_score AS score,
                           n.namespace AS namespace
                    ORDER BY n.relevance_score ASC
                    LIMIT 5
                """, threshold=ANTI_PATTERN_THRESHOLD)
                anti_patterns = [dict(r) for r in anti]

                return {
                    "success": True,
                    "global_patterns": global_patterns,
                    "promotion_candidates": promotion_candidates,
                    "anti_patterns": anti_patterns,
                }

        except Exception as e:
            logger.error(f"Global insights failed: {e}")
            return {"success": False, "error": str(e)}
