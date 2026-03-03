"""
Graph-Driven API Docs Generator (Phase 7.4)
=============================================
지식그래프에서 코드 구조를 추출하여 Markdown API 문서 자동 생성.
Mermaid 다이어그램 포함.

MCP 도구: generate_docs(module_name, depth, format)

기능:
- 단일 모듈 문서: 함수/클래스/호출관계/의존성/Bug Radar
- 전체 프로젝트 인덱스: 모듈 목록/통계/아키텍처 다이어그램
- Mermaid call graph + class hierarchy diagram
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class DocGenerator:
    """Graph-Driven API Docs Generator.

    Neo4j 지식그래프에서 모듈/클래스/함수 구조와 관계를 추출하여
    Markdown API 문서를 자동 생성한다.
    """

    def __init__(self, driver):
        """
        Args:
            driver: Neo4j driver instance
        """
        self.driver = driver

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def generate(self, module_name: str, depth: int = 2) -> Dict[str, Any]:
        """메인 문서 생성 엔트리포인트.

        Args:
            module_name: 모듈 이름. "*"이면 전체 프로젝트 인덱스 생성.
            depth: 문서화 깊이 (1=개요, 2=상세, 3=풀)

        Returns:
            {"success": bool, "module": str, "markdown": str, "stats": dict}
        """
        try:
            if module_name == "*":
                markdown = self._generate_project_index()
                stats = self._get_project_stats()
                return {
                    "success": True,
                    "module": "*",
                    "markdown": markdown,
                    "stats": stats,
                }
            else:
                markdown = self._generate_module_doc(module_name, depth)
                if markdown is None:
                    return {
                        "success": False,
                        "error": f"Module '{module_name}' not found in knowledge graph.",
                    }
                stats = self._get_module_stats(module_name)
                return {
                    "success": True,
                    "module": module_name,
                    "markdown": markdown,
                    "stats": stats,
                }
        except Exception as e:
            logger.error(f"DocGenerator.generate failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    # ------------------------------------------------------------------
    # Module-level document
    # ------------------------------------------------------------------

    def _generate_module_doc(self, module_name: str, depth: int) -> Optional[str]:
        """단일 모듈 문서 생성.

        Sections:
        1. 모듈 개요
        2. 클래스 목록 (메서드 포함)
        3. 함수 목록 (시그니처, docstring, 인자)
        4. 호출 관계 Mermaid 다이어그램
        5. 의존성 (imports)
        6. 데이터 의존성 (READS_CONFIG, ACCESSES_TABLE)
        7. Bug Radar 위험도
        """
        info = self._query_module_info(module_name)
        if info is None:
            return None

        name = info["name"]
        path = info["path"] or "N/A"
        functions = info["functions"]
        classes = info["classes"]

        lines: List[str] = []

        # --- 1. Module overview ---
        lines.append(f"# Module: `{name}`")
        lines.append("")
        lines.append(f"- **Path**: `{path}`")
        lines.append(f"- **Functions**: {len(functions)}")
        lines.append(f"- **Classes**: {len(classes)}")
        lines.append("")

        # --- 2. Classes ---
        if classes:
            lines.append("## Classes")
            lines.append("")
            for cls in classes:
                cls_name = cls.get("name", "Unknown")
                cls_doc = cls.get("doc") or ""
                lines.append(f"### `{cls_name}`")
                if cls_doc:
                    lines.append(f"> {cls_doc[:300]}")
                lines.append("")

                # Query methods for this class
                if depth >= 2:
                    methods = self._query_class_methods(cls_name)
                    if methods:
                        lines.append("| Method | Signature | Description |")
                        lines.append("|--------|-----------|-------------|")
                        for m in methods:
                            m_name = m.get("name", "?")
                            m_args = self._format_args(m.get("args"))
                            m_doc = (m.get("doc") or "")[:80].replace("|", "\\|").replace("\n", " ")
                            lines.append(f"| `{m_name}` | `({m_args})` | {m_doc} |")
                        lines.append("")

        # --- 3. Functions ---
        if functions:
            lines.append("## Functions")
            lines.append("")
            for func in functions:
                f_name = func.get("name", "Unknown")
                f_args = self._format_args(func.get("args"))
                f_doc = func.get("doc") or ""
                f_lines = func.get("lines") or 0

                lines.append(f"### `{f_name}({f_args})`")
                if f_doc:
                    lines.append(f"> {f_doc[:300]}")
                if depth >= 3 and f_lines:
                    lines.append(f"- Lines: ~{f_lines}")
                lines.append("")

        # --- 4. Call graph Mermaid ---
        if depth >= 2:
            call_mermaid = self._build_call_graph_mermaid(module_name)
            if call_mermaid:
                lines.append("## Call Graph")
                lines.append("")
                lines.append("```mermaid")
                lines.append(call_mermaid)
                lines.append("```")
                lines.append("")

        # --- 5. Class hierarchy Mermaid ---
        if depth >= 2 and classes:
            hierarchy_mermaid = self._build_class_hierarchy_mermaid(module_name)
            if hierarchy_mermaid:
                lines.append("## Class Hierarchy")
                lines.append("")
                lines.append("```mermaid")
                lines.append(hierarchy_mermaid)
                lines.append("```")
                lines.append("")

        # --- 6. Dependencies (imports) ---
        if depth >= 2:
            imports = self._query_imports(module_name)
            if imports:
                lines.append("## Dependencies (Imports)")
                lines.append("")
                for imp in imports:
                    lines.append(f"- `{imp}`")
                lines.append("")

        # --- 7. Data dependencies ---
        if depth >= 2:
            data_deps = self._query_data_dependencies(module_name)
            if data_deps:
                lines.append("## Data Dependencies")
                lines.append("")
                for dd in data_deps:
                    lines.append(f"- [{dd['rel']}] `{dd['target']}` ({dd['target_type']})")
                lines.append("")

        # --- 8. Bug Radar risk ---
        if depth >= 2:
            risks = self._query_bug_risks(module_name)
            if risks:
                lines.append("## Bug Radar (Risk Hotspots)")
                lines.append("")
                lines.append("| Function | Risk Score | Churn | Fan-in | Fan-out |")
                lines.append("|----------|-----------|-------|--------|---------|")
                for r in risks:
                    lines.append(
                        f"| `{r['name']}` | **{r['risk']:.0f}** | {r['churn']} | {r['fan_in']} | {r['fan_out']} |"
                    )
                lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Project-level index
    # ------------------------------------------------------------------

    def _generate_project_index(self) -> str:
        """전체 프로젝트 문서 인덱스.

        Sections:
        1. 모듈 목록 (함수/클래스 수)
        2. 전체 통계
        3. namespace별 분류
        4. 아키텍처 Mermaid 다이어그램
        """
        lines: List[str] = []

        # Collect all modules
        modules = self._query_all_modules()

        lines.append("# Project API Documentation Index")
        lines.append("")
        lines.append(f"Total modules: **{len(modules)}**")
        lines.append("")

        # --- 1. Module list ---
        lines.append("## Modules")
        lines.append("")
        lines.append("| Module | Path | Functions | Classes |")
        lines.append("|--------|------|-----------|---------|")
        for mod in modules:
            m_name = mod.get("name", "?")
            m_path = mod.get("path") or ""
            m_funcs = mod.get("func_count", 0)
            m_classes = mod.get("class_count", 0)
            lines.append(f"| `{m_name}` | `{m_path}` | {m_funcs} | {m_classes} |")
        lines.append("")

        # --- 2. Overall stats ---
        stats = self._get_project_stats()
        lines.append("## Statistics")
        lines.append("")
        lines.append(f"- **Total Nodes**: {stats.get('total_nodes', 0)}")
        lines.append(f"- **Total Edges**: {stats.get('total_edges', 0)}")
        lines.append(f"- **Functions**: {stats.get('functions', 0)}")
        lines.append(f"- **Classes**: {stats.get('classes', 0)}")
        lines.append(f"- **Modules**: {stats.get('modules', 0)}")
        lines.append("")

        # --- 3. Namespace classification ---
        namespaces = self._query_namespaces()
        if namespaces:
            lines.append("## Namespaces")
            lines.append("")
            for ns, count in namespaces.items():
                lines.append(f"- `{ns}`: {count} modules")
            lines.append("")

        # --- 4. Architecture Mermaid ---
        arch_mermaid = self._build_architecture_mermaid(modules)
        if arch_mermaid:
            lines.append("## Architecture Overview")
            lines.append("")
            lines.append("```mermaid")
            lines.append(arch_mermaid)
            lines.append("```")
            lines.append("")

        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Mermaid diagram builders
    # ------------------------------------------------------------------

    def _build_call_graph_mermaid(self, module_name: str) -> Optional[str]:
        """모듈 내 호출 관계를 Mermaid graph LR로 생성."""
        edges = self._query_call_edges(module_name)
        if not edges:
            return None

        lines = ["graph LR"]
        seen = set()
        for e in edges:
            caller = self._sanitize_mermaid_id(e["caller"])
            callee = self._sanitize_mermaid_id(e["callee"])
            edge_key = f"{caller}-->{callee}"
            if edge_key not in seen:
                seen.add(edge_key)
                lines.append(f"    {caller} --> {callee}")

        if len(lines) <= 1:
            return None
        return "\n".join(lines)

    def _build_class_hierarchy_mermaid(self, module_name: str) -> Optional[str]:
        """클래스 상속 + 메서드 다이어그램 (classDiagram)."""
        hierarchy = self._query_class_hierarchy(module_name)
        if not hierarchy:
            return None

        lines = ["classDiagram"]
        seen_relations = set()
        seen_classes = set()

        for item in hierarchy:
            child = self._sanitize_mermaid_id(item["child"])
            parent = item.get("parent")
            methods = item.get("methods", [])

            # Inheritance relation
            if parent:
                parent_id = self._sanitize_mermaid_id(parent)
                rel_key = f"{parent_id}<|--{child}"
                if rel_key not in seen_relations:
                    seen_relations.add(rel_key)
                    lines.append(f"    {parent_id} <|-- {child}")

            # Methods
            if child not in seen_classes:
                seen_classes.add(child)
                for m in methods[:10]:  # limit to 10 methods per class
                    m_name = self._sanitize_mermaid_id(m)
                    lines.append(f"    {child} : +{m_name}()")

        if len(lines) <= 1:
            return None
        return "\n".join(lines)

    def _build_architecture_mermaid(self, modules: List[Dict]) -> Optional[str]:
        """모듈 간 의존관계 아키텍처 다이어그램."""
        deps = self._query_module_dependencies()
        if not deps:
            return None

        lines = ["graph TD"]
        seen = set()
        for d in deps:
            src = self._sanitize_mermaid_id(d["source"])
            tgt = self._sanitize_mermaid_id(d["target"])
            edge_key = f"{src}-->{tgt}"
            if edge_key not in seen:
                seen.add(edge_key)
                lines.append(f"    {src} --> {tgt}")

        if len(lines) <= 1:
            return None
        return "\n".join(lines)

    # ------------------------------------------------------------------
    # Neo4j queries
    # ------------------------------------------------------------------

    def _query_module_info(self, module_name: str) -> Optional[Dict]:
        """모듈의 함수/클래스 정보 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)
                    WHERE m.name = $module_name
                       OR m.filepath CONTAINS $module_name
                    OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)
                    OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                    WITH m,
                         collect(DISTINCT {
                             name: f.name,
                             args: f.args,
                             doc: f.docstring,
                             lines: CASE WHEN f.end_line IS NOT NULL AND f.start_line IS NOT NULL
                                        THEN f.end_line - f.start_line
                                        ELSE null END
                         }) AS functions,
                         collect(DISTINCT {
                             name: c.name,
                             doc: c.docstring
                         }) AS classes
                    RETURN m.name AS name,
                           m.filepath AS path,
                           functions,
                           classes
                    LIMIT 1
                """, module_name=module_name)

                record = result.single()
                if not record:
                    # Try namespace-based search
                    return self._query_module_by_namespace(module_name)

                functions = [f for f in record["functions"] if f.get("name")]
                classes = [c for c in record["classes"] if c.get("name")]

                return {
                    "name": record["name"],
                    "path": record["path"],
                    "functions": functions,
                    "classes": classes,
                }
        except Exception as e:
            logger.error(f"_query_module_info failed: {e}")
            return None

    def _query_module_by_namespace(self, module_name: str) -> Optional[Dict]:
        """namespace 기반으로 모듈 검색 (fallback)."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)
                    WHERE m.namespace CONTAINS $module_name
                       OR m.qualified_name CONTAINS $module_name
                    OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)
                    OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                    WITH m,
                         collect(DISTINCT {
                             name: f.name,
                             args: f.args,
                             doc: f.docstring,
                             lines: CASE WHEN f.end_line IS NOT NULL AND f.start_line IS NOT NULL
                                        THEN f.end_line - f.start_line
                                        ELSE null END
                         }) AS functions,
                         collect(DISTINCT {
                             name: c.name,
                             doc: c.docstring
                         }) AS classes
                    RETURN m.name AS name,
                           m.filepath AS path,
                           functions,
                           classes
                    LIMIT 1
                """, module_name=module_name)

                record = result.single()
                if not record:
                    return None

                functions = [f for f in record["functions"] if f.get("name")]
                classes = [c for c in record["classes"] if c.get("name")]

                return {
                    "name": record["name"],
                    "path": record["path"],
                    "functions": functions,
                    "classes": classes,
                }
        except Exception as e:
            logger.error(f"_query_module_by_namespace failed: {e}")
            return None

    def _query_class_methods(self, class_name: str) -> List[Dict]:
        """클래스의 메서드 목록 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (c:Class {name: $class_name})-[:HAS_METHOD]->(m:Function)
                    RETURN m.name AS name,
                           m.args AS args,
                           m.docstring AS doc
                    ORDER BY m.name
                """, class_name=class_name)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"_query_class_methods failed: {e}")
            return []

    def _query_call_edges(self, module_name: str) -> List[Dict]:
        """모듈 내 함수 간 호출 관계 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)-[:DEFINES]->(f:Function)-[:CALLS]->(called:Function)
                    WHERE m.name = $module_name
                       OR m.filepath CONTAINS $module_name
                    RETURN f.name AS caller, called.name AS callee
                    LIMIT 50
                """, module_name=module_name)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"_query_call_edges failed: {e}")
            return []

    def _query_class_hierarchy(self, module_name: str) -> List[Dict]:
        """모듈 내 클래스 상속 관계 및 메서드 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)-[:DEFINES]->(c:Class)
                    WHERE m.name = $module_name
                       OR m.filepath CONTAINS $module_name
                    OPTIONAL MATCH (c)-[:INHERITS]->(parent:Class)
                    OPTIONAL MATCH (c)-[:HAS_METHOD]->(method:Function)
                    RETURN c.name AS child,
                           parent.name AS parent,
                           collect(DISTINCT method.name) AS methods
                """, module_name=module_name)
                records = [dict(r) for r in result]
                # Filter out records with no child name
                return [r for r in records if r.get("child")]
        except Exception as e:
            logger.error(f"_query_class_hierarchy failed: {e}")
            return []

    def _query_imports(self, module_name: str) -> List[str]:
        """모듈의 import 대상 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)-[:IMPORTS]->(target)
                    WHERE m.name = $module_name
                       OR m.filepath CONTAINS $module_name
                    RETURN DISTINCT coalesce(target.qualified_name, target.name) AS import_name
                    ORDER BY import_name
                """, module_name=module_name)
                return [r["import_name"] for r in result if r["import_name"]]
        except Exception as e:
            logger.error(f"_query_imports failed: {e}")
            return []

    def _query_data_dependencies(self, module_name: str) -> List[Dict]:
        """READS_CONFIG, ACCESSES_TABLE 등 데이터 의존성 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)-[:DEFINES]->(f:Function)-[r]->(target)
                    WHERE (m.name = $module_name OR m.filepath CONTAINS $module_name)
                      AND type(r) IN ['READS_CONFIG', 'ACCESSES_TABLE', 'WRITES_TO', 'READS_FROM']
                    RETURN f.name AS source,
                           type(r) AS rel,
                           target.name AS target,
                           labels(target)[0] AS target_type
                    LIMIT 30
                """, module_name=module_name)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"_query_data_dependencies failed: {e}")
            return []

    def _query_bug_risks(self, module_name: str) -> List[Dict]:
        """모듈 내 함수의 Bug Radar 위험도 조회."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)-[:DEFINES]->(f:Function)
                    WHERE m.name = $module_name
                       OR m.filepath CONTAINS $module_name
                    OPTIONAL MATCH (f)<-[:CALLS]-(caller:Function)
                    OPTIONAL MATCH (f)-[:CALLS]->(callee:Function)
                    WITH f,
                         count(DISTINCT caller) AS fan_in,
                         count(DISTINCT callee) AS fan_out,
                         coalesce(f.churn_count, 0) AS churn,
                         coalesce(f.end_line, 0) - coalesce(f.start_line, 0) AS line_count
                    WITH f, fan_in, fan_out, churn, line_count,
                         (3.0 * churn + 2.0 * (line_count / 50.0) + 1.5 * fan_in * fan_out) AS risk
                    WHERE risk > 10
                    RETURN f.name AS name,
                           risk,
                           churn,
                           fan_in,
                           fan_out
                    ORDER BY risk DESC
                    LIMIT 10
                """, module_name=module_name)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"_query_bug_risks failed: {e}")
            return []

    def _query_all_modules(self) -> List[Dict]:
        """전체 모듈 목록 (함수/클래스 수 포함)."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)
                    OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)
                    OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                    RETURN m.name AS name,
                           m.filepath AS path,
                           m.namespace AS namespace,
                           count(DISTINCT f) AS func_count,
                           count(DISTINCT c) AS class_count
                    ORDER BY m.name
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"_query_all_modules failed: {e}")
            return []

    def _query_namespaces(self) -> Dict[str, int]:
        """namespace별 모듈 수."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)
                    WHERE m.namespace IS NOT NULL
                    RETURN m.namespace AS namespace, count(m) AS count
                    ORDER BY count DESC
                """)
                return {r["namespace"]: r["count"] for r in result}
        except Exception as e:
            logger.error(f"_query_namespaces failed: {e}")
            return {}

    def _query_module_dependencies(self) -> List[Dict]:
        """모듈 간 IMPORTS 관계."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (src:Module)-[:IMPORTS]->(tgt:Module)
                    RETURN src.name AS source, tgt.name AS target
                    LIMIT 100
                """)
                return [dict(r) for r in result]
        except Exception as e:
            logger.error(f"_query_module_dependencies failed: {e}")
            return []

    # ------------------------------------------------------------------
    # Statistics helpers
    # ------------------------------------------------------------------

    def _get_project_stats(self) -> Dict[str, int]:
        """프로젝트 전체 노드/엣지 통계."""
        try:
            with self.driver.session() as session:
                nodes_result = session.run("""
                    MATCH (n)
                    RETURN count(n) AS total_nodes,
                           count(CASE WHEN 'Function' IN labels(n) THEN 1 END) AS functions,
                           count(CASE WHEN 'Class' IN labels(n) THEN 1 END) AS classes,
                           count(CASE WHEN 'Module' IN labels(n) THEN 1 END) AS modules
                """)
                nr = nodes_result.single()

                edges_result = session.run("""
                    MATCH ()-[r]->()
                    RETURN count(r) AS total_edges
                """)
                er = edges_result.single()

                return {
                    "total_nodes": nr["total_nodes"] if nr else 0,
                    "total_edges": er["total_edges"] if er else 0,
                    "functions": nr["functions"] if nr else 0,
                    "classes": nr["classes"] if nr else 0,
                    "modules": nr["modules"] if nr else 0,
                }
        except Exception as e:
            logger.error(f"_get_project_stats failed: {e}")
            return {"total_nodes": 0, "total_edges": 0, "functions": 0, "classes": 0, "modules": 0}

    def _get_module_stats(self, module_name: str) -> Dict[str, int]:
        """단일 모듈의 함수/클래스/엣지 통계."""
        try:
            with self.driver.session() as session:
                result = session.run("""
                    MATCH (m:Module)
                    WHERE m.name = $module_name OR m.filepath CONTAINS $module_name
                    OPTIONAL MATCH (m)-[:DEFINES]->(f:Function)
                    OPTIONAL MATCH (m)-[:DEFINES]->(c:Class)
                    OPTIONAL MATCH (m)-[:DEFINES]->(f2:Function)-[r:CALLS]->()
                    RETURN count(DISTINCT f) AS functions,
                           count(DISTINCT c) AS classes,
                           count(DISTINCT r) AS edges
                """, module_name=module_name)
                record = result.single()
                if record:
                    return {
                        "functions": record["functions"],
                        "classes": record["classes"],
                        "edges": record["edges"],
                    }
                return {"functions": 0, "classes": 0, "edges": 0}
        except Exception as e:
            logger.error(f"_get_module_stats failed: {e}")
            return {"functions": 0, "classes": 0, "edges": 0}

    # ------------------------------------------------------------------
    # Utility helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _format_args(args) -> str:
        """함수 인자를 문자열로 변환. args가 list이면 join 처리."""
        if args is None:
            return ""
        if isinstance(args, list):
            return ", ".join(str(a) for a in args)
        return str(args)

    @staticmethod
    def _sanitize_mermaid_id(name: str) -> str:
        """Mermaid에서 안전한 ID로 변환.
        특수문자를 제거/치환하여 다이어그램 렌더링 오류를 방지.
        """
        if not name:
            return "unknown"
        # Replace dots and slashes with underscores
        sanitized = name.replace(".", "_").replace("/", "_").replace("-", "_")
        # Remove any remaining problematic characters
        sanitized = "".join(c for c in sanitized if c.isalnum() or c == "_")
        # Ensure it doesn't start with a digit
        if sanitized and sanitized[0].isdigit():
            sanitized = "m_" + sanitized
        return sanitized or "unknown"
