"""
Predictive Bug Radar (Phase 5.3)
=================================
수정 전 버그를 예측하는 "핫 스팟" 감지 시스템.

Risk 공식:
  Risk(node) = α·churn_rate + β·complexity + γ·fan_in·fan_out + δ·rollback_count

핫 스팟 기준:
- 자주 수정되는 노드 (churn rate ↑)
- 높은 복잡도 + 많은 의존성 (fan_in × fan_out ↑)
- hybrid_search 결과에 BUG HOTSPOT 경고 자동 주입
"""

import logging
from typing import Dict, Any, List
from datetime import datetime

logger = logging.getLogger(__name__)

# Risk 계수
ALPHA_CHURN = 3.0       # 수정 빈도 가중치
BETA_COMPLEXITY = 2.0   # 복잡도 가중치 (라인 수 기반)
GAMMA_FAN = 1.5         # 의존성 가중치 (fan_in × fan_out)
DELTA_ROLLBACK = 5.0    # 롤백 가중치

# 핫스팟 임계값
HOTSPOT_THRESHOLD = 40


class BugRadar:
    """Predictive Bug Radar - 코드 핫스팟 감지"""

    def __init__(self, driver):
        self.driver = driver

    def record_modification(self, file_path: str, function_names: List[str]):
        """sync_incremental 호출 시 수정 이력 기록.

        Args:
            file_path: 수정된 파일 경로
            function_names: 수정된 함수/클래스 이름 목록
        """
        if not function_names:
            return

        try:
            with self.driver.session() as session:
                session.run("""
                    UNWIND $names AS name
                    MATCH (n) WHERE n.name = name OR n.qualified_name = name
                    SET n.modification_count = COALESCE(n.modification_count, 0) + 1,
                        n.last_modified = datetime(),
                        n.modification_history = COALESCE(n.modification_history, []) + [$timestamp]
                """, names=function_names, timestamp=datetime.utcnow().isoformat() + "Z")
        except Exception as e:
            logger.warning(f"Failed to record modification: {e}")

    def get_hotspots(self, top_k: int = 10) -> Dict[str, Any]:
        """프로젝트에서 가장 위험한 코드 핫스팟 반환.

        Risk(node) = α·churn + β·complexity + γ·fan_in·fan_out + δ·rollback
        """
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class)
                    AND COALESCE(n.modification_count, 0) > 0

                    // Fan-in: 이 노드를 호출하는 수
                    OPTIONAL MATCH (caller)-[:CALLS]->(n)
                    WITH n, count(DISTINCT caller) AS fan_in

                    // Fan-out: 이 노드가 호출하는 수
                    OPTIONAL MATCH (n)-[:CALLS]->(called)
                    WITH n, fan_in, count(DISTINCT called) AS fan_out

                    // Complexity 근사: 코드 라인 수
                    WITH n, fan_in, fan_out,
                         COALESCE(n.end_line, 0) - COALESCE(n.start_line, 0) AS line_count,
                         COALESCE(n.modification_count, 0) AS churn

                    // Risk Score 계산
                    WITH n, fan_in, fan_out, line_count, churn,
                         ($alpha * churn)
                         + ($beta * CASE WHEN line_count > 50 THEN line_count / 10.0
                                         WHEN line_count > 20 THEN line_count / 20.0
                                         ELSE 0 END)
                         + ($gamma * fan_in * fan_out)
                         AS risk_score

                    WHERE risk_score > 0

                    RETURN
                        n.name AS name,
                        labels(n)[0] AS type,
                        n.module AS module,
                        churn,
                        fan_in, fan_out,
                        line_count,
                        round(risk_score * 10) / 10.0 AS risk_score,
                        n.last_modified AS last_modified,
                        CASE
                            WHEN risk_score >= 80 THEN 'CRITICAL'
                            WHEN risk_score >= 50 THEN 'HIGH'
                            WHEN risk_score >= 25 THEN 'MEDIUM'
                            ELSE 'LOW'
                        END AS severity

                    ORDER BY risk_score DESC
                    LIMIT $top_k
                """, top_k=top_k, alpha=ALPHA_CHURN, beta=BETA_COMPLEXITY, gamma=GAMMA_FAN)

                hotspots = [dict(r) for r in result]

                return {
                    "success": True,
                    "hotspots": hotspots,
                    "total": len(hotspots),
                    "threshold": HOTSPOT_THRESHOLD,
                }

        except Exception as e:
            logger.error(f"Bug radar failed: {e}")
            return {"success": False, "error": str(e)}

    def get_hotspot_warnings(self, node_names: List[str]) -> List[Dict]:
        """주어진 노드 이름 중 핫스팟인 것에 대한 경고 반환.
        hybrid_search 결과에 주입하기 위한 용도.
        """
        if not node_names:
            return []

        try:
            with self.driver.session() as session:
                result = session.run("""
                    UNWIND $names AS name
                    MATCH (n) WHERE n.name = name AND (n:Function OR n:Class)
                    AND COALESCE(n.modification_count, 0) >= 3

                    OPTIONAL MATCH (caller)-[:CALLS]->(n)
                    WITH n, name, count(DISTINCT caller) AS fan_in
                    OPTIONAL MATCH (n)-[:CALLS]->(called)
                    WITH n, name, fan_in, count(DISTINCT called) AS fan_out

                    WITH n, name, fan_in, fan_out,
                         COALESCE(n.modification_count, 0) AS churn,
                         ($alpha * COALESCE(n.modification_count, 0))
                         + ($gamma * fan_in * fan_out) AS risk_score

                    WHERE risk_score >= $threshold

                    RETURN name, labels(n)[0] AS type,
                           round(risk_score * 10) / 10.0 AS risk_score,
                           churn, fan_in, fan_out
                """, names=node_names, alpha=ALPHA_CHURN, gamma=GAMMA_FAN,
                     threshold=HOTSPOT_THRESHOLD)

                return [
                    {
                        "type": "BugHotspot",
                        "name": r["name"],
                        "doc": f"🔥 BUG HOTSPOT: {r['name']} (risk={r['risk_score']}, "
                               f"churn={r['churn']}, fan_in={r['fan_in']}, fan_out={r['fan_out']}). "
                               f"이 코드는 자주 수정되며 의존성이 높아 버그 위험이 큽니다.",
                        "search_mode": "hotspot",
                        "risk_score": r["risk_score"],
                    }
                    for r in result
                ]
        except Exception as e:
            logger.warning(f"Hotspot warning check failed: {e}")
            return []
