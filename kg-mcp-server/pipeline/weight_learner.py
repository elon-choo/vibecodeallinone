from neo4j import GraphDatabase
from typing import List, Dict, Any, Optional
import logging
from datetime import datetime
import json
import os
from pathlib import Path

logger = logging.getLogger(__name__)


def _get_project_namespace() -> str:
    """현재 프로젝트의 namespace 추출 (CLAUDE_PROJECT_DIR 기반)."""
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir).name
    return ""


class NodeWeightLearner:
    """노드 가중치 기반 강화 학습 파이프라인 (Phase 5.1: namespace 스코핑)"""

    def __init__(self, driver):
        self.driver = driver

    def _build_ns_filter(self, alias: str = "n") -> str:
        """Phase 5.1: 프로젝트 namespace 필터 생성.
        동명 함수(main, init 등)가 다른 프로젝트의 가중치에 영향 주지 않도록 격리."""
        ns = _get_project_namespace()
        if not ns:
            return ""
        return f" AND ({alias}.namespace IS NULL OR {alias}.namespace = $ns)"

    def process_feedback(self, session_id: str, success: bool, injected_names: List[str],
                         namespace: Optional[str] = None):
        """
        주입되었던 컨텍스트 노드들의 가중치를 조정.
        Phase 5.1: namespace 스코핑으로 프로젝트 간 가중치 격리.
        """
        if not injected_names:
            return {"success": False, "message": "No identifiers to process"}

        ns = namespace or _get_project_namespace()
        ns_filter = self._build_ns_filter("n")

        try:
            with self.driver.session() as session:
                if success:
                    query = f"""
                    UNWIND $names AS name
                    MATCH (n) WHERE (n.name = name OR n.qualified_name = name){ns_filter}

                    SET n.relevance_score = CASE
                        WHEN n.relevance_score IS NULL THEN 1.2
                        WHEN n.relevance_score + 0.2 > 2.0 THEN 2.0
                        ELSE n.relevance_score + 0.2
                    END

                    SET n.last_useful = datetime()

                    RETURN count(n) as updated
                    """
                    result = session.run(query, names=injected_names, ns=ns)
                    updated = result.single()["updated"]
                    return {"success": True, "updated": updated, "score_change": "+0.2"}

                else:
                    query = f"""
                    UNWIND $names AS name
                    MATCH (n) WHERE (n.name = name OR n.qualified_name = name){ns_filter}

                    SET n.relevance_score = CASE
                        WHEN n.relevance_score IS NULL THEN 0.9
                        WHEN n.relevance_score - 0.1 < 0.1 THEN 0.1
                        ELSE n.relevance_score - 0.1
                    END

                    RETURN count(n) as updated
                    """
                    result = session.run(query, names=injected_names, ns=ns)
                    updated = result.single()["updated"]
                    return {"success": True, "updated": updated, "score_change": "-0.1"}

        except Exception as e:
            logger.error(f"Error in weight learning: {e}")
            return {"success": False, "error": str(e)}

    def get_top_weighted_nodes(self, limit: int = 10):
        """가장 높은 가중치를 가진 (검증된) 노드 반환"""
        with self.driver.session() as session:
            result = session.run("""
            MATCH (n)
            WHERE n.relevance_score > 1.0
            RETURN n.name as name, labels(n)[0] as type, n.relevance_score as score
            ORDER BY n.relevance_score DESC, n.last_useful DESC
            LIMIT $limit
            """, limit=limit)
            return [dict(r) for r in result]
