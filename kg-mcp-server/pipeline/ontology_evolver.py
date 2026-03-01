"""
Ontology Auto-Refactor (Phase 5.5)
====================================
지식그래프의 구조적 이상을 감지하고 자가 치유하는 시스템.

감지 항목:
1. Orphan Node: 엣지가 없는 고립 노드
2. God Module: 50+ 함수를 가진 모듈
3. Circular Dependency: 순환 참조
4. Stale Node: 30일+ 미사용 & relevance < 0.3
5. Schema Drift: 실제 파일 삭제됐지만 그래프에 남은 노드
"""

import logging
from typing import Dict, Any, List

logger = logging.getLogger(__name__)


class OntologyEvolver:
    """지식그래프 자가 치유 시스템"""

    def __init__(self, driver):
        self.driver = driver

    def evolve(self, auto_fix: bool = False) -> Dict[str, Any]:
        """온톨로지 전체 분석 및 리팩토링 제안.

        Args:
            auto_fix: True이면 자동 수정 (orphan 삭제, stale 아카이브 등)
        """
        report = {
            "success": True,
            "orphans": self._detect_orphans(auto_fix),
            "god_modules": self._detect_god_modules(),
            "circular_deps": self._detect_circular_deps(),
            "stale_nodes": self._detect_stale_nodes(auto_fix),
            "schema_drift": self._detect_schema_drift(),
        }

        total_issues = sum(
            len(v) if isinstance(v, list) else 0
            for v in report.values()
        )
        report["total_issues"] = total_issues
        report["auto_fixed"] = auto_fix

        return report

    def _detect_orphans(self, auto_fix: bool) -> List[Dict]:
        """엣지가 하나도 없는 고립 노드 감지."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class)
                    AND NOT (n)-[]-()
                    RETURN n.name AS name, labels(n)[0] AS type,
                           n.module AS module
                    LIMIT 20
                """)
                orphans = [dict(r) for r in result]

                if auto_fix and orphans:
                    session.run("""
                        MATCH (n)
                        WHERE (n:Function OR n:Class)
                        AND NOT (n)-[]-()
                        DELETE n
                    """)
                    logger.info(f"Auto-deleted {len(orphans)} orphan nodes")

                return orphans
        except Exception as e:
            logger.error(f"Orphan detection failed: {e}")
            return []

    def _detect_god_modules(self) -> List[Dict]:
        """50+ 함수를 가진 God Module 감지."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)-[:DEFINES]->(f:Function)
                    WITH m, count(f) AS func_count
                    WHERE func_count >= 50
                    RETURN m.name AS name, m.filepath AS path, func_count
                    ORDER BY func_count DESC
                    LIMIT 10
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"God module detection failed: {e}")
            return []

    def _detect_circular_deps(self) -> List[Dict]:
        """모듈 간 순환 의존성 감지."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (a:Module)-[:IMPORTS]->(b:Module)-[:IMPORTS]->(a)
                    WHERE id(a) < id(b)
                    RETURN a.name AS module_a, b.name AS module_b
                    LIMIT 10
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"Circular dependency detection failed: {e}")
            return []

    def _detect_stale_nodes(self, auto_fix: bool) -> List[Dict]:
        """30일+ 미사용 & relevance_score < 0.3 노드."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (n)
                    WHERE (n:Function OR n:Class)
                    AND n.last_useful IS NOT NULL
                    AND duration.between(n.last_useful, datetime()).days > 30
                    AND COALESCE(n.relevance_score, 0.5) < 0.3
                    RETURN n.name AS name, labels(n)[0] AS type,
                           n.module AS module,
                           n.relevance_score AS score,
                           duration.between(n.last_useful, datetime()).days AS days_stale
                    ORDER BY n.relevance_score ASC
                    LIMIT 20
                """)
                stale = [dict(r) for r in result]

                if auto_fix and stale:
                    names = [s["name"] for s in stale]
                    session.run("""
                        UNWIND $names AS name
                        MATCH (n) WHERE n.name = name
                        SET n:ArchivedNode
                        REMOVE n:Function, n:Class
                    """, names=names)
                    logger.info(f"Auto-archived {len(stale)} stale nodes")

                return stale
        except Exception as e:
            logger.error(f"Stale node detection failed: {e}")
            return []

    def _detect_schema_drift(self) -> List[Dict]:
        """filepath가 존재하지 않는 Module 노드 감지."""
        try:
            import os
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)
                    WHERE m.filepath IS NOT NULL
                    RETURN m.name AS name, m.filepath AS filepath
                    LIMIT 100
                """)
                drifted = []
                for r in result:
                    fp = r["filepath"]
                    if fp and not os.path.exists(fp):
                        drifted.append({"name": r["name"], "filepath": fp})
                return drifted[:20]
        except Exception as e:
            logger.error(f"Schema drift detection failed: {e}")
            return []
