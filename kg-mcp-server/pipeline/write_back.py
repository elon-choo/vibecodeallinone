from pathlib import Path
from typing import Dict, Any, List, Optional
import logging
import os

from src.indexing.graph_builder import KnowledgeGraphBuilder
from neo4j import GraphDatabase
import ast

logger = logging.getLogger(__name__)

# tree-sitter 파서 지원 확장자
TS_SUPPORTED_EXTS = {'.py', '.js', '.jsx', '.ts', '.tsx', '.java', '.go', '.rs'}


class GraphWriteBack:
    """실시간 그래프 업데이트 시스템"""

    def __init__(self, driver):
        self.driver = driver
        self._ts_parser = None

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
        from src.ingestion.parser import FileParseResult, FunctionInfo, ClassInfo

        parser = self._get_ts_parser()
        if parser is None:
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

    def _parse_python_ast(self, file_path: str):
        """간단한 Python AST 기반 파서 (tree-sitter 에러 우회용)"""
        from src.ingestion.parser import FileParseResult, FunctionInfo, ClassInfo, ImportInfo
        
        with open(file_path, 'r', encoding='utf-8') as f:
            code = f.read()
            
        tree = ast.parse(code)
        
        result = FileParseResult(file_path=file_path, language="python")
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
                func = FunctionInfo(
                    name=node.name,
                    file_path=file_path,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    code=ast.unparse(node),
                    
                    docstring=ast.get_docstring(node),
                    
                    
                )
                
                # 매우 간단한 호출 추출
                for child in ast.walk(node):
                    if isinstance(child, ast.Call):
                        if isinstance(child.func, ast.Name):
                            func.calls.append(child.func.id)
                        elif isinstance(child.func, ast.Attribute):
                            func.calls.append(child.func.attr)
                            
                result.functions.append(func)
                
            elif isinstance(node, ast.ClassDef):
                cls = ClassInfo(
                    name=node.name,
                    file_path=file_path,
                    start_line=node.lineno,
                    end_line=node.end_lineno or node.lineno,
                    code=ast.unparse(node),
                    
                    docstring=ast.get_docstring(node),
                    
                )
                
                # 베이스 클래스
                for base in node.bases:
                    if isinstance(base, ast.Name):
                        cls.bases.append(base.id)
                        
                result.classes.append(cls)
                
        return result
        
    def sync_file(self, file_path: str, repo_url: str = "local") -> Dict[str, Any]:
        """단일 파일의 변경사항을 구문분석하여 Neo4j에 즉시 반영"""
        path = Path(file_path)
        if not path.exists():
            return {"success": False, "error": f"File not found: {file_path}"}
            
        try:
            # Phase 10: tree-sitter 파서 우선 사용 (지원 언어인 경우)
            result = None
            if path.suffix in TS_SUPPORTED_EXTS:
                try:
                    result = self._parse_with_tree_sitter(str(path))
                except Exception as e:
                    logger.debug(f"tree-sitter parse failed, falling back: {e}")

            # Fallback: Python AST 또는 기존 CodeParser
            if result is None:
                if path.suffix == '.py':
                    result = self._parse_python_ast(str(path))
                else:
                    from src.ingestion.parser import CodeParser
                    parser = CodeParser()
                    result = parser.parse_file(str(path))
                
            if not result:
                return {"success": False, "error": "Could not parse file (unsupported extension?)"}
            
            # 2. Neo4j 업데이트 (기존 노드를 MERGE/UPDATE)
            class DummyConnector:
                def __init__(self, driver):
                    self.driver = driver
                def run_query(self, query, params=None, fetch=True):
                    with self.driver.session() as session:
                        res = session.run(query, params or {})
                        if fetch:
                            try:
                                return [dict(r) for r in res]
                            except Exception:
                                return []
                        return []
                def create_constraints(self): pass
                def create_indexes(self): pass
            
            connector = DummyConnector(self.driver)
            builder = KnowledgeGraphBuilder(connector=connector)
            
            # 파일 노드와 내부 요소 업데이트
            stats = builder.process_file_result(result, repo_url)

            # 내부 관계 업데이트
            builder.build_relationships([result])

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

            # Phase 6.4: Data Dependency extraction
            dep_stats = {}
            try:
                from src.ingestion.data_dep_extractor import (
                    DataDependencyExtractor,
                    DataDependencyGraphWriter,
                )
                if path.suffix == '.py':
                    extractor = DataDependencyExtractor(file_path)
                    with open(file_path, 'r', encoding='utf-8') as f:
                        source = f.read()
                    deps = extractor.extract(source)
                    if deps:
                        writer = DataDependencyGraphWriter(self.driver)
                        # 기존 stale 엣지 정리 후 새로 기록
                        writer.cleanup_stale(file_path)
                        dep_stats = writer.write_dependencies(deps)
                        logger.info(f"Data dependencies for {file_path}: {dep_stats}")
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

