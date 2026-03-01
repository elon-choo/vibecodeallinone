from typing import Dict, Any, List
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)

# Phase 5.1: 확장된 영향 추적 관계 타입
IMPACT_EDGE_TYPES = "CALLS|INHERITS|READS_CONFIG|ACCESSES_TABLE|SHARES_STATE"


class ImpactSimulator:
    """폭발 반경 시뮬레이터 (Impact Blast Radius Simulator)

    Phase 5.1 업그레이드:
    - READS_CONFIG: 같은 설정 파일/환경변수를 읽는 코드 추적
    - ACCESSES_TABLE: 같은 DB 테이블에 접근하는 코드 추적
    - SHARES_STATE: 공유 상태(전역 변수, 싱글톤)를 사용하는 코드 추적
    - data_dependencies 별도 분석 추가
    """

    def __init__(self, driver):
        self.driver = driver

    def simulate_impact(self, target_name: str, depth: int = 3) -> Dict[str, Any]:
        """
        특정 함수/클래스를 수정했을 때 직/간접적으로 영향받는 노드 계산

        Args:
            target_name: 수정하려는 대상 이름 (함수/클래스)
            depth: 파급을 추적할 최대 깊이 (기본 3)

        Returns:
            영향 분석 리포트
        """
        try:
            with self.driver.session() as session:
                # 1. 대상 노드 찾기
                target_result = session.run("""
                    MATCH (t)
                    WHERE (t:Function OR t:Class) AND (toLower(t.name) = toLower($name) OR t.qualified_name = $name)
                    RETURN t.name as name, labels(t)[0] as type, t.module as module
                    LIMIT 1
                """, name=target_name).single()

                if not target_result:
                    return {
                        "success": False,
                        "error": f"Target '{target_name}' not found in the Knowledge Graph."
                    }

                target_info = dict(target_result)

                # 2. 폭발 반경 시뮬레이션 (Phase 5.1: 확장된 엣지 타입)
                impact_query = f"""
                    MATCH path = (dependent)-[:{IMPACT_EDGE_TYPES}*1..{depth}]->(t)
                    WHERE t.name = $name
                    WITH dependent, length(path) as distance,
                         [node in nodes(path) | node.name] as chain,
                         [r in relationships(path) | type(r)] as rel_types
                    RETURN
                        dependent.name as name,
                        labels(dependent)[0] as type,
                        dependent.module as module,
                        min(distance) as min_distance,
                        collect(chain)[0] as sample_chain,
                        collect(rel_types)[0] as relationship_types
                    ORDER BY min_distance ASC, dependent.name ASC
                """

                impact_result = session.run(impact_query, name=target_info["name"])

                dependents = []
                modules_affected = set()
                data_deps = []  # Phase 5.1: 데이터 의존성 별도 추적

                for record in impact_result:
                    item = dict(record)
                    dependents.append(item)
                    if item.get("module"):
                        modules_affected.add(item.get("module"))
                    # 데이터 의존성 분류
                    rel_types = item.get("relationship_types", [])
                    if rel_types and any(rt in ("READS_CONFIG", "ACCESSES_TABLE", "SHARES_STATE") for rt in rel_types):
                        data_deps.append(item)

                # 3. 리스크 스코어 계산 (Phase 5.1: 데이터 의존성 가중치 추가)
                total_dependents = len(dependents)
                direct_dependents = sum(1 for d in dependents if d["min_distance"] == 1)
                indirect_dependents = total_dependents - direct_dependents
                data_dep_count = len(data_deps)

                risk_score = min(100,
                    (direct_dependents * 15) +
                    (indirect_dependents * 5) +
                    (len(modules_affected) * 10) +
                    (data_dep_count * 8)  # 데이터 의존성은 높은 가중치
                )

                if risk_score >= 80:
                    risk_level = "CRITICAL"
                    warning = "이 코드는 시스템 핵심 컴포넌트입니다. 수정 시 대규모 사이드 이펙트가 발생할 수 있습니다."
                elif risk_score >= 50:
                    risk_level = "HIGH"
                    warning = "이 코드는 여러 모듈에서 사용 중입니다. 수정 후 연관 테스트를 반드시 수행하세요."
                elif risk_score >= 20:
                    risk_level = "MEDIUM"
                    warning = "국지적인 영향이 예상됩니다."
                else:
                    risk_level = "LOW"
                    warning = "영향도가 낮아 안전하게 수정 가능합니다."

                result = {
                    "success": True,
                    "target": target_info,
                    "metrics": {
                        "total_affected_nodes": total_dependents,
                        "direct_dependents": direct_dependents,
                        "indirect_dependents": indirect_dependents,
                        "modules_affected": len(modules_affected),
                        "data_dependencies": data_dep_count,
                        "risk_score": risk_score,
                        "risk_level": risk_level
                    },
                    "warning": warning,
                    "affected_modules": list(modules_affected)[:10],
                    "critical_dependents": [d for d in dependents if d["min_distance"] == 1][:5],
                }

                # Phase 5.1: 데이터 의존성 경고
                if data_deps:
                    result["data_dependency_warning"] = (
                        f"⚠️ {data_dep_count}개의 데이터 의존성 감지 "
                        "(같은 config/table/state 사용). 수정 시 이들도 영향받을 수 있습니다."
                    )
                    result["data_dependents"] = [
                        {"name": d["name"], "type": d["type"], "module": d.get("module", ""),
                         "via": d.get("relationship_types", [])}
                        for d in data_deps[:5]
                    ]

                return result

        except Exception as e:
            logger.error(f"Error simulating impact: {e}")
            return {"success": False, "error": str(e)}

