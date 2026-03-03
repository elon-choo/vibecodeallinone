"""
Smart Deduplication Engine (Phase 8.5)
=======================================
여러 프로젝트의 동명 함수를 namespace로 구분하고,
검색 시 현재 프로젝트를 우선 노출.

검색 가중치:
- 현재 프로젝트 (CLAUDE_PROJECT_DIR 매칭): x1.5
- 같은 기술 스택 (같은 언어): x1.2
- GitHub 패턴: x1.0 (참고용)
- 아카이브된 노드: x0.3
"""
import os
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

logger = logging.getLogger(__name__)


class DedupEngine:
    """namespace 기반 검색 결과 중복 제거 및 우선순위 조정"""

    # 가중치 상수
    CURRENT_PROJECT_BOOST = 1.5
    SAME_LANGUAGE_BOOST = 1.2
    GITHUB_WEIGHT = 1.0
    ARCHIVED_PENALTY = 0.3

    def __init__(self, driver):
        self.driver = driver

    def get_current_namespace(self) -> str:
        """현재 프로젝트의 namespace 추출"""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if project_dir:
            return Path(project_dir).name
        return ""

    def deduplicate_results(
        self,
        results: List[Dict],
        current_namespace: str = "",
    ) -> List[Dict]:
        """검색 결과에서 동명 함수를 namespace 기반으로 중복 제거 및 우선순위 조정.

        로직:
        1. 같은 name이 여러 개면 qualified_name으로 구분
        2. 현재 프로젝트 namespace 매칭 -> boost
        3. GitHub 패턴은 항상 포함하되 별도 표시
        4. archived 노드는 penalty

        Args:
            results: 검색 결과 리스트 (rrf_score 또는 relevance_score 포함)
            current_namespace: 현재 프로젝트 namespace (빈 문자열이면 자동 감지)

        Returns:
            중복 제거 및 우선순위 조정된 결과 리스트
        """
        if not results:
            return results

        if not current_namespace:
            current_namespace = self.get_current_namespace()

        # name -> [results] 그룹핑
        name_groups: Dict[str, List[Dict]] = {}
        for r in results:
            name = r.get("name", "")
            if name not in name_groups:
                name_groups[name] = []
            name_groups[name].append(r)

        deduplicated = []

        for name, group in name_groups.items():
            if len(group) == 1:
                # 유일한 결과: 그대로 사용, 가중치만 조정
                item = group[0]
                item["dedup_score"] = self._calc_boost(item, current_namespace)
                deduplicated.append(item)
            else:
                # 동명 함수 여러 개: 우선순위 결정
                scored = []
                for item in group:
                    boost = self._calc_boost(item, current_namespace)
                    item["dedup_score"] = boost
                    scored.append(item)

                # 최고 점수의 결과를 메인으로
                scored.sort(key=lambda x: x["dedup_score"], reverse=True)
                main = scored[0]

                # 나머지는 "alternatives" 정보로 추가
                if len(scored) > 1:
                    main["alternatives"] = [
                        {
                            "name": s.get("qualified_name") or s.get("name"),
                            "namespace": s.get("namespace", ""),
                            "repo": s.get("repo", ""),
                        }
                        for s in scored[1:3]  # 최대 2개 대안
                    ]

                deduplicated.append(main)

        # dedup_score 기준 정렬
        deduplicated.sort(key=lambda x: x.get("dedup_score", 0), reverse=True)

        return deduplicated

    def _calc_boost(self, item: Dict, current_namespace: str) -> float:
        """결과 항목의 우선순위 점수 계산.

        Args:
            item: 검색 결과 항목
            current_namespace: 현재 프로젝트 namespace

        Returns:
            부스트 적용된 점수
        """
        base_score = (
            item.get("rrf_score", 0)
            or item.get("relevance_score", 0)
            or 0.01
        )

        ns = str(item.get("namespace", ""))
        repo = item.get("repo", "")
        archived = item.get("archived", False)
        language = item.get("language", "")

        multiplier = 1.0

        # 현재 프로젝트 매칭
        if current_namespace and current_namespace in ns:
            multiplier *= self.CURRENT_PROJECT_BOOST
            item["_match_reason"] = "current_project"
        # 같은 기술 스택 (같은 언어) 체크
        elif language and self._is_same_language_stack(language):
            multiplier *= self.SAME_LANGUAGE_BOOST
            item["_match_reason"] = "same_language"
        # GitHub 패턴
        elif repo or "github:" in ns:
            multiplier *= self.GITHUB_WEIGHT
            item["_match_reason"] = "github_pattern"

        # 아카이브된 노드
        if archived:
            multiplier *= self.ARCHIVED_PENALTY
            item["_match_reason"] = "archived"

        return round(base_score * multiplier, 6)

    def _is_same_language_stack(self, language: str) -> bool:
        """현재 프로젝트와 같은 언어 스택인지 확인.

        현재 프로젝트 디렉토리의 주요 파일 확장자를 기반으로 판단.
        """
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        if not project_dir:
            return False

        # 프로젝트 디렉토리의 언어 추정 (경량 휴리스틱)
        project_path = Path(project_dir)
        language_lower = language.lower()

        # 파일 존재 여부 기반 빠른 체크
        lang_indicators = {
            "python": ["requirements.txt", "setup.py", "pyproject.toml", "Pipfile"],
            "javascript": ["package.json", "tsconfig.json"],
            "typescript": ["tsconfig.json", "package.json"],
            "go": ["go.mod", "go.sum"],
            "rust": ["Cargo.toml"],
            "java": ["pom.xml", "build.gradle"],
        }

        indicators = lang_indicators.get(language_lower, [])
        for indicator in indicators:
            if (project_path / indicator).exists():
                return True

        return False

    def get_duplicate_stats(self) -> Dict:
        """현재 그래프의 동명 함수 통계.

        Returns:
            동명 함수 통계 딕셔너리:
            - duplicate_names: 동명 함수 이름 수
            - total_duplicate_nodes: 중복 노드 총 수
            - top_duplicates: 상위 10개 동명 함수 상세
        """
        try:
            with self.driver.session() as session:
                # 동명 함수 그룹
                result = session.run("""
                    MATCH (f:Function)
                    WITH f.name AS name, count(f) AS cnt,
                         collect(DISTINCT f.namespace)[0..5] AS namespaces
                    WHERE cnt > 1
                    RETURN name, cnt, namespaces
                    ORDER BY cnt DESC
                    LIMIT 20
                """)
                duplicates = [dict(r) for r in result]

                total_dupes = sum(d["cnt"] for d in duplicates)

                # 전체 함수 수
                total_result = session.run("""
                    MATCH (f:Function)
                    RETURN count(f) AS total
                """)
                total_functions = total_result.single()["total"]

                # namespace별 함수 수
                ns_result = session.run("""
                    MATCH (f:Function)
                    WHERE f.namespace IS NOT NULL
                    WITH f.namespace AS ns, count(f) AS cnt
                    RETURN ns, cnt
                    ORDER BY cnt DESC
                    LIMIT 10
                """)
                ns_distribution = [dict(r) for r in ns_result]

                return {
                    "success": True,
                    "total_functions": total_functions,
                    "duplicate_names": len(duplicates),
                    "total_duplicate_nodes": total_dupes,
                    "duplication_ratio": round(
                        total_dupes / max(total_functions, 1) * 100, 1
                    ),
                    "top_duplicates": duplicates[:10],
                    "namespace_distribution": ns_distribution,
                }
        except Exception as e:
            logger.error(f"Failed to get duplicate stats: {e}")
            return {"success": False, "error": str(e)}

    def resolve_ambiguous(
        self, name: str, current_namespace: str = ""
    ) -> Dict:
        """동명 함수 중 현재 프로젝트에 가장 적합한 것을 선택.

        Args:
            name: 함수 이름
            current_namespace: 현재 프로젝트 namespace

        Returns:
            최적 매칭 결과 및 대안 목록
        """
        if not current_namespace:
            current_namespace = self.get_current_namespace()

        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (f:Function)
                    WHERE f.name = $name
                    RETURN f.name AS name,
                           f.qualified_name AS qualified_name,
                           f.namespace AS namespace,
                           f.module AS module,
                           f.docstring AS docstring,
                           f.lineno AS lineno,
                           f.args AS args,
                           f.repo AS repo,
                           f.archived AS archived
                    ORDER BY f.namespace ASC
                """, name=name)

                candidates = [dict(r) for r in result]

                if not candidates:
                    return {
                        "success": False,
                        "error": f"No function found with name '{name}'",
                    }

                if len(candidates) == 1:
                    return {
                        "success": True,
                        "resolved": candidates[0],
                        "alternatives": [],
                        "ambiguous": False,
                    }

                # 우선순위 계산
                for c in candidates:
                    c["dedup_score"] = self._calc_boost(c, current_namespace)

                candidates.sort(
                    key=lambda x: x.get("dedup_score", 0), reverse=True
                )

                return {
                    "success": True,
                    "resolved": candidates[0],
                    "alternatives": candidates[1:5],
                    "ambiguous": True,
                    "total_matches": len(candidates),
                }
        except Exception as e:
            logger.error(f"Failed to resolve ambiguous function '{name}': {e}")
            return {"success": False, "error": str(e)}
