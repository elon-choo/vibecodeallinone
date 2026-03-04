import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Any, List, Optional
import logging

import ast

logger = logging.getLogger(__name__)


# ── Lightweight data models (replaces external src.ingestion.parser) ──────────

@dataclass
class FunctionInfo:
    name: str = ""
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    code: str = ""
    docstring: Optional[str] = None
    parameters: List[str] = field(default_factory=list)
    return_type: Optional[str] = None
    decorators: List[str] = field(default_factory=list)
    is_method: bool = False
    parent_class: Optional[str] = None
    calls: List[str] = field(default_factory=list)


@dataclass
class ClassInfo:
    name: str = ""
    file_path: str = ""
    start_line: int = 0
    end_line: int = 0
    code: str = ""
    docstring: Optional[str] = None
    bases: List[str] = field(default_factory=list)


@dataclass
class FileParseResult:
    file_path: str = ""
    language: str = "unknown"
    functions: List[FunctionInfo] = field(default_factory=list)
    classes: List[ClassInfo] = field(default_factory=list)

# tree-sitter 파서 지원 확장자
TS_SUPPORTED_EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs'}


class GraphWriteBack:
    """실시간 그래프 업데이트 시스템"""

    # Max file size for parsing (10 MB) to prevent OOM on malicious files
    MAX_FILE_SIZE = 10 * 1024 * 1024

    def __init__(self, driver):
        self.driver = driver
        self._ts_parser = None
        # Capture allowed base directory at init time (not at request time)
        self._allowed_base = Path.cwd().resolve()

    def _get_ts_parser(self):
        """TreeSitterParser 인스턴스 (lazy init)."""
        if self._ts_parser is None:
            try:
                from mcp_server.pipeline.ts_parser import TreeSitterParser
                self._ts_parser = TreeSitterParser()
            except ImportError:
                logger.debug("tree-sitter parser not available")
        return self._ts_parser

    def _parse_with_tree_sitter(self, file_path: str) -> Optional[Any]:
        """tree-sitter 기반 파서로 파일 파싱 후 FileParseResult로 변환."""
        parser = self._get_ts_parser()
        if parser is None:
            return None

        try:
            file_size = os.path.getsize(file_path)
            if file_size > self.MAX_FILE_SIZE:
                logger.warning(f"File too large to parse ({file_size} bytes): {file_path}")
                return None
        except OSError:
            return None

        entities = parser.parse_file(file_path)
        if not entities:
            return None

        lang = parser.detect_language(file_path) or "unknown"
        result = FileParseResult(file_path=file_path, language=lang)

        for ent in entities:
            if ent.type == "function":
                func = FunctionInfo(
                    name=ent.name,
                    file_path=ent.file_path,
                    start_line=ent.start_line,
                    end_line=ent.end_line,
                    code=ent.body,
                    docstring=ent.docstring or None,
                    parameters=ent.parameters,
                    return_type=ent.return_type or None,
                    decorators=ent.decorators,
                )
                result.functions.append(func)
            elif ent.type == "method":
                func = FunctionInfo(
                    name=ent.name,
                    file_path=ent.file_path,
                    start_line=ent.start_line,
                    end_line=ent.end_line,
                    code=ent.body,
                    docstring=ent.docstring or None,
                    is_method=True,
                    parent_class=ent.parent_class,
                    parameters=ent.parameters,
                    return_type=ent.return_type or None,
                    decorators=ent.decorators,
                )
                result.functions.append(func)
            elif ent.type == "class":
                cls = ClassInfo(
                    name=ent.name,
                    file_path=ent.file_path,
                    start_line=ent.start_line,
                    end_line=ent.end_line,
                    code=ent.body,
                    docstring=ent.docstring or None,
                )
                result.classes.append(cls)

        logger.info(f"tree-sitter parsed {file_path}: {len(result.functions)} funcs, {len(result.classes)} classes")
        return result

    def _parse_python_ast(self, file_path: str, source: str = None):
        """간단한 Python AST 기반 파서 (tree-sitter 에러 우회용)

        Args:
            file_path: 파일 경로
            source: 이미 읽은 소스코드 (None이면 파일에서 읽음)
        """
        if source is None:
            try:
                file_size = os.path.getsize(file_path)
                if file_size > self.MAX_FILE_SIZE:
                    logger.warning(f"File too large to parse ({file_size} bytes): {file_path}")
                    return None
                with open(file_path, 'r', encoding='utf-8', errors='replace') as f:
                    source = f.read()
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot read {file_path}: {e}")
                return None
        code = source

        try:
            tree = ast.parse(code)
        except SyntaxError as e:
            logger.warning(f"SyntaxError parsing {file_path}: {e}")
            return None
        
        result = FileParseResult(file_path=file_path, language="python")

        def _extract_calls(node) -> List[str]:
            """Extract call names from a function body."""
            calls = []
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.append(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.append(child.func.attr)
            return calls

        def _extract_function(node, parent_class=None):
            """Extract a FunctionInfo from a FunctionDef/AsyncFunctionDef node."""
            func = FunctionInfo(
                name=node.name,
                file_path=file_path,
                start_line=node.lineno,
                end_line=node.end_lineno or node.lineno,
                code=ast.unparse(node),
                docstring=ast.get_docstring(node),
                is_method=parent_class is not None,
                parent_class=parent_class,
                calls=_extract_calls(node),
            )
            result.functions.append(func)

        # Only iterate top-level nodes (not ast.walk) to avoid extracting
        # nested/inner functions as top-level entities
        for node in ast.iter_child_nodes(tree):
            if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
                _extract_function(node)

            elif isinstance(node, ast.ClassDef):
                cls = ClassInfo(
                    name=node.name,
                    file_path=file_path,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    code=ast.unparse(node),
                    docstring=ast.get_docstring(node),
                )
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        cls.bases.append(base.id)
                result.classes.append(cls)

                # Extract methods (direct children of class body only)
                for child in ast.iter_child_nodes(node):
                    if isinstance(child, (ast.FunctionDef, ast.AsyncFunctionDef)):
                        _extract_function(child, parent_class=node.name)

        return result
        
    def _upsert_to_neo4j(self, result: FileParseResult, file_path: str, repo_url: str) -> Dict[str, int]:
        """Parse result를 Neo4j에 atomic 트랜잭션으로 MERGE/UPDATE.

        H-5 개선사항:
        1. session.execute_write()로 파일 단위 atomic 트랜잭션
        2. sync 시작 시 해당 file_path의 기존 AST 노드 DETACH DELETE 후 재생성 (ghost node 방지)
        3. CALLS callee 매칭에 (name, file_path) 우선, fallback으로 name-only
        """
        stats = {"functions": 0, "classes": 0, "relationships": 0}
        module_name = Path(file_path).stem

        def _tx_upsert(tx):
            nonlocal stats

            # 1. Collect current entity names for stale node cleanup later
            current_func_names = {func.name for func in result.functions}
            current_class_names = {cls.name for cls in result.classes}

            # 2. Remove stale nodes (entities no longer in file) — preserves external CALLS
            tx.run("""
                MATCH (n:Function {file_path: $fp})
                WHERE NOT n.name IN $keep_names
                DETACH DELETE n
            """, fp=file_path, keep_names=list(current_func_names))
            tx.run("""
                MATCH (n:Class {file_path: $fp})
                WHERE NOT n.name IN $keep_names
                DETACH DELETE n
            """, fp=file_path, keep_names=list(current_class_names))

            # 3. File 노드 MERGE
            tx.run("""
                MERGE (f:File {path: $path})
                SET f.language = $lang, f.repo = $repo, f.updated_at = datetime()
            """, path=file_path, lang=result.language, repo=repo_url)

            # 4. Function 노드 MERGE (preserves incoming CALLS from other files)
            for func in result.functions:
                tx.run("""
                    MERGE (fn:Function {name: $name, file_path: $fp})
                    SET fn.start_line = $sl, fn.end_line = $el,
                        fn.code = $code, fn.docstring = $doc,
                        fn.module = $module, fn.updated_at = datetime()
                """, name=func.name, fp=file_path,
                    sl=func.start_line, el=func.end_line,
                    code=(func.code or "")[:5000], doc=func.docstring or "",
                    module=module_name)
                tx.run("""
                    MATCH (f:File {path: $fp})
                    MATCH (fn:Function {name: $name, file_path: $fp})
                    MERGE (f)-[:DEFINES]->(fn)
                """, fp=file_path, name=func.name)
                stats["functions"] += 1

            # 5. Class 노드 MERGE (preserves external relationships)
            for cls in result.classes:
                tx.run("""
                    MERGE (c:Class {name: $name, file_path: $fp})
                    SET c.start_line = $sl, c.end_line = $el,
                        c.code = $code, c.docstring = $doc,
                        c.module = $module, c.updated_at = datetime()
                """, name=cls.name, fp=file_path,
                    sl=cls.start_line, el=cls.end_line,
                    code=(cls.code or "")[:5000], doc=cls.docstring or "",
                    module=module_name)
                tx.run("""
                    MATCH (f:File {path: $fp})
                    MATCH (c:Class {name: $name, file_path: $fp})
                    MERGE (f)-[:DEFINES]->(c)
                """, fp=file_path, name=cls.name)
                stats["classes"] += 1

            # 6. Remove stale outgoing CALLS from this file's functions, then recreate
            tx.run("""
                MATCH (caller:Function {file_path: $fp})-[r:CALLS]->()
                DELETE r
            """, fp=file_path)

            for func in result.functions:
                for call_name in func.calls:
                    tx.run("""
                        MATCH (caller:Function {name: $caller, file_path: $fp})
                        OPTIONAL MATCH (callee_same_file:Function {name: $callee, file_path: $fp})
                        OPTIONAL MATCH (callee_any:Function {name: $callee})
                        WHERE callee_any <> caller
                        WITH caller, coalesce(callee_same_file, callee_any) AS callee
                        WHERE callee IS NOT NULL
                        MERGE (caller)-[:CALLS]->(callee)
                    """, caller=func.name, fp=file_path, callee=call_name)
                    stats["relationships"] += 1

        try:
            with self.driver.session() as session:
                session.execute_write(_tx_upsert)
        except Exception as e:
            logger.error(f"Neo4j upsert error: {e}")
        return stats

    def sync_file(self, file_path: str, repo_url: str = "local") -> Dict[str, Any]:
        """단일 파일의 변경사항을 구문분석하여 Neo4j에 즉시 반영"""
        path = Path(file_path).resolve()
        base = self._allowed_base
        if not (path == base or path.is_relative_to(base)):
            return {"success": False, "error": f"Path not allowed (outside working directory): {file_path}"}
        if not path.is_file():
            return {"success": False, "error": f"File not found: {file_path}"}
            
        # Read file once upfront to avoid double-read race conditions
        _cached_source = None
        if path.suffix == '.py':
            try:
                file_size = os.path.getsize(str(path))
                if file_size <= self.MAX_FILE_SIZE:
                    with open(str(path), 'r', encoding='utf-8', errors='replace') as f:
                        _cached_source = f.read()
            except (PermissionError, OSError) as e:
                logger.warning(f"Cannot read {file_path}: {e}")

        try:
            # Phase 10: tree-sitter 파서 우선 사용 (지원 언어인 경우)
            result = None
            if path.suffix in TS_SUPPORTED_EXTS:
                try:
                    result = self._parse_with_tree_sitter(str(path))
                except Exception as e:
                    logger.debug(f"tree-sitter parse failed, falling back: {e}")

            # Fallback: Python AST (non-Python files rely on tree-sitter)
            if result is None:
                if path.suffix == '.py':
                    result = self._parse_python_ast(str(path), source=_cached_source)
                else:
                    logger.debug(f"No parser available for {path.suffix} (tree-sitter failed)")
                
            if not result:
                return {"success": False, "error": "Could not parse file (unsupported extension?)"}
            
            # 2. Neo4j 업데이트 (직접 MERGE/UPDATE)
            stats = self._upsert_to_neo4j(result, file_path, repo_url)

            # Phase 5.3: Bug Radar - 수정 이력 기록
            modified_names = (
                [f.name for f in result.functions] +
                [c.name for c in result.classes]
            )
            if modified_names:
                try:
                    from mcp_server.pipeline.bug_radar import BugRadar
                    radar = BugRadar(self.driver)
                    radar.record_modification(file_path, modified_names)
                except Exception as e:
                    logger.debug(f"Bug radar recording skipped: {e}")

            # Phase 10.4: Auto-describe undocumented functions
            if modified_names:
                try:
                    from mcp_server.pipeline.code_describer import CodeDescriber
                    describer = CodeDescriber(self.driver)
                    for func in result.functions:
                        if not func.docstring and func.code and len(func.code) >= 50:
                            desc = describer.describe_on_sync(func.name, func.code)
                            if desc:
                                with self.driver.session() as s:
                                    s.run("""
                                        MATCH (n:Function {name: $name, file_path: $fp})
                                        WHERE n.ai_description IS NULL
                                        SET n.ai_description = $desc, n.ai_described_at = datetime()
                                    """, name=func.name, fp=file_path, desc=desc)
                                logger.debug(f"AI description for {func.name}: {desc[:60]}")
                except Exception as e:
                    logger.debug(f"Auto-describe skipped: {e}")

            # Phase 6.1: Auto-embed new/modified nodes
            if modified_names:
                try:
                    from mcp_server.pipeline.embedding_pipeline import EmbeddingPipeline
                    embedder = EmbeddingPipeline(self.driver)
                    embedded_count = 0
                    for name in modified_names:
                        if embedder.embed_single_node(name):
                            embedded_count += 1
                    if embedded_count > 0:
                        logger.debug(f"Auto-embedded {embedded_count}/{len(modified_names)} nodes")
                except Exception as e:
                    logger.debug(f"Auto-embedding skipped: {e}")

            # Phase 6.4: Data Dependency extraction (optional)
            dep_stats = {}
            try:
                from mcp_server.pipeline.data_dep_extractor import (
                    DataDependencyExtractor,
                    DataDependencyGraphWriter,
                )
                if path.suffix == '.py' and _cached_source is not None:
                    extractor = DataDependencyExtractor(file_path)
                    deps = extractor.extract(_cached_source)
                    if deps:
                        writer = DataDependencyGraphWriter(self.driver)
                        writer.cleanup_stale(file_path)
                        dep_stats = writer.write_dependencies(deps)
                        logger.info(f"Data dependencies for {file_path}: {dep_stats}")
            except ImportError:
                logger.debug("Data dependency extractor not available")
            except Exception as e:
                logger.debug(f"Data dependency extraction skipped: {e}")

            return {
                "success": True,
                "file": file_path,
                "stats": stats,
                "modified_entities": modified_names,
                "data_dependencies": dep_stats,
                "message": f"Successfully updated graph: {stats.get('functions', 0)} functions, {stats.get('classes', 0)} classes synced."
            }
            
        except Exception as e:
            logger.error(f"Error syncing {file_path}: {e}")
            return {"success": False, "error": str(e)}

