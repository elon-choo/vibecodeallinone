"""Neo4j 그래프 검색 모듈"""
from typing import List, Dict, Any, Optional
from neo4j import GraphDatabase
import logging

logger = logging.getLogger(__name__)


class GraphSearcher:
    """Neo4j 지식그래프 검색"""

    def __init__(self, uri: str, user: str, password: str):
        self.driver = GraphDatabase.driver(uri, auth=(user, password))
        logger.info(f"GraphSearcher connected to {uri}")

    def close(self):
        self.driver.close()

    def search_all(self, query: str, limit: int = 20) -> List[Dict]:
        """전체 검색 (코드 + 패턴)"""
        code_results = self.search_code(query, limit // 2)
        pattern_results = self.search_patterns(query, limit // 2)
        return code_results + pattern_results

    def search_code(self, query: str, limit: int = 10) -> List[Dict]:
        """코드 노드 검색 (Function, Class, Module)"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE (n:Function OR n:Class OR n:Module)
                AND (
                    toLower(n.name) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.docstring, '')) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.qualified_name, '')) CONTAINS toLower($search_term)
                )
                RETURN
                    labels(n)[0] as type,
                    n.name as name,
                    n.qualified_name as qname,
                    n.docstring as doc,
                    n.module as module,
                    n.lineno as lineno,
                    n.args as args
                ORDER BY
                    CASE WHEN toLower(n.name) = toLower($search_term) THEN 0
                         WHEN toLower(n.name) STARTS WITH toLower($search_term) THEN 1
                         ELSE 2 END
                LIMIT $limit
            """, search_term=query, limit=limit)
            return [dict(r) for r in result]

    def search_patterns(self, query: str, limit: int = 10) -> List[Dict]:
        """패턴/지식 노드 검색"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                WHERE (n:DesignPattern OR n:V3Pattern OR n:SecurityPattern
                       OR n:CodeSmell OR n:BestPractice
                       OR n:V3SecurityVulnerability OR n:V3ResearchFinding)
                AND (
                    toLower(n.name) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.description, '')) CONTAINS toLower($search_term)
                    OR toLower(coalesce(n.intent, '')) CONTAINS toLower($search_term)
                )
                RETURN
                    labels(n)[0] as type,
                    n.name as name,
                    n.description as description,
                    n.intent as intent,
                    n.effectiveness_metric as metric,
                    n.category as category,
                    n.cwe_id as cwe_id,
                    n.severity as severity
                LIMIT $limit
            """, search_term=query, limit=limit)
            return [dict(r) for r in result]

    def get_function_context(self, func_name: str, depth: int = 2) -> Dict:
        """함수 컨텍스트 조회 (호출 관계 포함)"""
        with self.driver.session() as session:
            # 1. 함수 기본 정보
            func_result = session.run("""
                MATCH (f:Function)
                WHERE f.name = $name OR f.qualified_name CONTAINS $name
                RETURN
                    f.qualified_name as qname,
                    f.name as name,
                    f.docstring as doc,
                    f.args as args,
                    f.module as module,
                    f.class_name as class_name,
                    f.lineno as lineno
                LIMIT 1
            """, name=func_name)
            func = func_result.single()

            if not func:
                return {"error": f"Function '{func_name}' not found"}

            # 2. 이 함수가 호출하는 함수들
            calls = session.run("""
                MATCH (f:Function)-[:CALLS]->(called:Function)
                WHERE f.name = $name OR f.qualified_name CONTAINS $name
                RETURN called.name as name, called.qualified_name as qname
                LIMIT 10
            """, name=func_name)

            # 3. 이 함수를 호출하는 함수들
            callers = session.run("""
                MATCH (caller:Function)-[:CALLS]->(f:Function)
                WHERE f.name = $name OR f.qualified_name CONTAINS $name
                RETURN caller.name as name, caller.qualified_name as qname
                LIMIT 10
            """, name=func_name)

            # 4. 소속 클래스 정보 (있으면)
            class_info = None
            if func.get('class_name'):
                class_result = session.run("""
                    MATCH (c:Class)
                    WHERE c.name = $class_name
                    RETURN c.name as name, c.docstring as doc, c.bases as bases
                    LIMIT 1
                """, class_name=func['class_name'])
                class_info = class_result.single()

            # 5. 관련 패턴 추천
            patterns = self._find_relevant_patterns(func_name)

            return {
                "function": dict(func),
                "calls": [dict(r) for r in calls],
                "called_by": [dict(r) for r in callers],
                "class_info": dict(class_info) if class_info else None,
                "related_patterns": patterns
            }

    def _find_relevant_patterns(self, keyword: str) -> List[Dict]:
        """키워드 기반 관련 패턴 찾기"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (p)
                WHERE (p:DesignPattern OR p:SecurityPattern OR p:V3Pattern)
                AND (
                    toLower(p.name) CONTAINS toLower($search_term)
                    OR toLower(coalesce(p.description, '')) CONTAINS toLower($search_term)
                )
                RETURN labels(p)[0] as type, p.name as name,
                       p.intent as intent, p.effectiveness_metric as metric
                LIMIT 5
            """, search_term=keyword)
            return [dict(r) for r in result]

    def get_module_structure(self, module_name: str) -> Dict:
        """모듈 구조 조회"""
        with self.driver.session() as session:
            # 모듈 정보
            module = session.run("""
                MATCH (m:Module)
                WHERE m.name CONTAINS $name
                RETURN m.name as name, m.filepath as path,
                       m.class_count as classes, m.function_count as functions
                LIMIT 1
            """, name=module_name).single()

            if not module:
                return {"error": f"Module '{module_name}' not found"}

            # 모듈 내 클래스
            classes = session.run("""
                MATCH (m:Module)-[:DEFINES]->(c:Class)
                WHERE m.name CONTAINS $name
                RETURN c.name as name, c.docstring as doc
            """, name=module_name)

            # 모듈 내 함수
            functions = session.run("""
                MATCH (m:Module)-[:DEFINES]->(f:Function)
                WHERE m.name CONTAINS $name
                RETURN f.name as name, f.docstring as doc
            """, name=module_name)

            # 의존성
            imports = session.run("""
                MATCH (m:Module)-[:IMPORTS]->(dep:Module)
                WHERE m.name CONTAINS $name
                RETURN dep.name as name
            """, name=module_name)

            return {
                "module": dict(module),
                "classes": [dict(r) for r in classes],
                "functions": [dict(r) for r in functions],
                "imports": [dict(r) for r in imports]
            }

    def get_security_recommendations(self, code_type: str = None) -> List[Dict]:
        """보안 추천사항 조회"""
        with self.driver.session() as session:
            # 보안 패턴
            patterns = session.run("""
                MATCH (p:SecurityPattern)
                RETURN 'SecurityPattern' as type, p.name as name, p.intent as description
            """)

            # AI 코드 취약점
            vulns = session.run("""
                MATCH (v:V3SecurityVulnerability)
                RETURN 'Vulnerability' as type,
                       v.name as name,
                       v.cwe_id as cwe_id,
                       v.severity as severity,
                       v.ai_generation_rate as rate,
                       v.remediation as remediation
            """)

            # 보안 자동화 패턴
            automation = session.run("""
                MATCH (p:V3Pattern)
                WHERE p.category = 'SECURITY_AUTOMATION'
                RETURN 'SecurityAutomation' as type,
                       p.name as name,
                       p.description as description,
                       p.effectiveness_metric as metric
            """)

            return (
                [dict(r) for r in patterns] +
                [dict(r) for r in vulns] +
                [dict(r) for r in automation]
            )

    def get_graph_stats(self) -> Dict:
        """그래프 통계"""
        with self.driver.session() as session:
            result = session.run("""
                MATCH (n)
                RETURN labels(n)[0] as label, count(n) as count
                ORDER BY count DESC
            """)
            nodes = {r['label']: r['count'] for r in result}

            result = session.run("""
                MATCH ()-[r]->()
                RETURN type(r) as type, count(r) as count
                ORDER BY count DESC
            """)
            relations = {r['type']: r['count'] for r in result}

            return {
                "nodes": nodes,
                "relations": relations,
                "total_nodes": sum(nodes.values()),
                "total_relations": sum(relations.values())
            }
