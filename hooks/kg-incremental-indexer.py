#!/usr/bin/env python3
"""
KG Incremental Indexer v1.0 (Phase 2-1)
========================================
PostToolUse Hook - Write/Edit 후 자동으로 새 함수/클래스를 Neo4j에 추가.
모든 프로젝트 범용 (프로젝트별 네임스페이스 적용).

작동:
1. Write/Edit된 파일이 .py인지 확인
2. AST 파싱으로 함수/클래스 추출
3. Neo4j에 MERGE (있으면 업데이트, 없으면 생성)
4. 프로젝트 경로를 네임스페이스로 사용
"""

import ast
import os
import sys
import json
from pathlib import Path
from datetime import datetime


def get_written_file():
    """PostToolUse hook: stdin JSON에서 tool_input 추출, env var 폴백"""
    # 1차: stdin에서 읽기 (Claude Code PostToolUse hook 표준)
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                parsed = json.loads(stdin_data)
                tool_input_obj = parsed.get("tool_input", {})
                if isinstance(tool_input_obj, dict):
                    file_path = tool_input_obj.get("file_path", "")
                    content = tool_input_obj.get("content", "") or tool_input_obj.get("new_string", "")
                    if file_path:
                        return file_path, content
    except Exception:
        pass
    # 2차: 환경변수 폴백 (수동 테스트용)
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if not tool_input:
        return "", ""
    try:
        data = json.loads(tool_input)
        file_path = data.get("file_path", "")
        content = data.get("content", "") or data.get("new_string", "")
        return file_path, content
    except Exception:
        return "", ""


def parse_python_ast(content: str, file_path: str) -> dict:
    """Python 코드를 AST 파싱하여 함수/클래스 추출"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"functions": [], "classes": [], "imports": []}

    # 모듈명 추출 (파일 경로에서)
    module_name = Path(file_path).stem

    functions = []
    classes = []
    imports = []

    for node in ast.walk(tree):
        if isinstance(node, ast.FunctionDef) or isinstance(node, ast.AsyncFunctionDef):
            doc = ast.get_docstring(node) or ""
            args = [a.arg for a in node.args.args if a.arg != "self"]
            # 호출하는 함수 추출
            calls = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.add(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.add(child.func.attr)

            functions.append({
                "name": node.name,
                "module": module_name,
                "lineno": node.lineno,
                "docstring": doc[:300],
                "args": args[:10],
                "calls": list(calls)[:20],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })

        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            bases = [b.id if isinstance(b, ast.Name) else str(b) for b in node.bases]
            methods = [n.name for n in node.body
                       if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]

            classes.append({
                "name": node.name,
                "module": module_name,
                "lineno": node.lineno,
                "docstring": doc[:300],
                "bases": bases[:5],
                "methods": methods[:20],
            })

        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return {"functions": functions, "classes": classes, "imports": imports}


def parse_with_tree_sitter(content: str, file_path: str) -> dict:
    """tree-sitter 기반 다국어 파서 (Python/JS/TS/TSX/Java/Go/Rust).
    Phase 10.5: regex 기반 파서를 tree-sitter로 교체.
    """
    try:
        import sys as _sys
        _sys.path.insert(0, str(Path.home() / "Documents" / "neo4j_knowledgeGraph"))
        from mcp_server.pipeline.ts_parser import TreeSitterParser
    except ImportError:
        # tree-sitter 없으면 regex 폴백
        return parse_typescript_regex(content, file_path)

    module_name = Path(file_path).stem
    parser = TreeSitterParser()
    entities = parser.parse_file(file_path, source=content)

    functions = []
    classes = []
    for ent in entities:
        if ent.type in ("function", "method"):
            functions.append({
                "name": ent.name,
                "module": module_name,
                "lineno": ent.start_line,
                "docstring": (ent.docstring or "")[:300],
                "args": ent.parameters[:10],
                "calls": [],
                "is_async": False,
                "code": (ent.body or "")[:3000],
                "parent_class": ent.parent_class or "",
            })
        elif ent.type == "class":
            classes.append({
                "name": ent.name,
                "module": module_name,
                "lineno": ent.start_line,
                "docstring": (ent.docstring or "")[:300],
                "bases": [],
                "methods": [],
                "code": (ent.body or "")[:5000],
            })

    return {"functions": functions, "classes": classes, "imports": []}


def parse_typescript_regex(content: str, file_path: str) -> dict:
    """Regex 기반 TS/JS 함수/클래스 추출 (tree-sitter 없을 때 폴백)"""
    import re
    module_name = Path(file_path).stem
    functions, classes, imports = [], [], []

    for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', content):
        functions.append({"name": m.group(1), "module": module_name, "lineno": content[:m.start()].count("\n")+1,
            "docstring": "", "args": [a.strip().split(":")[0].strip() for a in m.group(2).split(",") if a.strip()][:10],
            "calls": [], "is_async": "async" in content[max(0,m.start()-20):m.start()]})

    for m in re.finditer(r'(?:export\s+)?(?:const|let)\s+(\w+)\s*(?::[^=]*)?\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::[^=]*)?\s*=>', content):
        if not any(f["name"] == m.group(1) for f in functions):
            functions.append({"name": m.group(1), "module": module_name, "lineno": content[:m.start()].count("\n")+1,
                "docstring": "", "args": [a.strip().split(":")[0].strip() for a in m.group(2).split(",") if a.strip()][:10],
                "calls": [], "is_async": "async" in content[max(0,m.start()-10):m.end()]})

    for m in re.finditer(r'(?:export\s+)?(?:class|interface|type)\s+(\w+)', content):
        classes.append({"name": m.group(1), "module": module_name, "lineno": content[:m.start()].count("\n")+1,
            "docstring": "", "bases": [], "methods": []})

    for m in re.finditer(r'(?:export\s+)?(?:const|function)\s+([A-Z]\w+)\s*(?::\s*React\.FC)?', content):
        name = m.group(1)
        if not any(f["name"] == name for f in functions) and not any(c["name"] == name for c in classes):
            functions.append({"name": name, "module": module_name, "lineno": content[:m.start()].count("\n")+1,
                "docstring": "React component", "args": ["props"], "calls": [], "is_async": False})

    for m in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content):
        imports.append(m.group(1))

    return {"functions": functions, "classes": classes, "imports": imports}


def get_project_namespace(file_path: str) -> str:
    """파일 경로에서 프로젝트 네임스페이스 추출"""
    # /path/to/project/... → project_name
    parts = Path(file_path).parts
    if "Documents" in parts:
        idx = parts.index("Documents")
        if idx + 1 < len(parts):
            return parts[idx + 1]
    # 프로젝트 루트 환경변수
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    if project_dir:
        return Path(project_dir).name
    return "unknown"


def upsert_to_neo4j(parsed: dict, file_path: str, namespace: str):
    """Neo4j에 MERGE (있으면 업데이트, 없으면 생성)"""
    try:
        from neo4j import GraphDatabase
        driver = GraphDatabase.driver(
            "bolt://localhost:7687",
            auth=("neo4j", "password123"),
            connection_timeout=2,
        )
    except Exception:
        return 0

    count = 0
    module_name = Path(file_path).stem
    qualified_module = f"{namespace}.{module_name}"

    try:
        with driver.session() as session:
            # Module 노드
            session.run("""
                MERGE (m:Module {name: $name})
                SET m.filepath = $filepath,
                    m.namespace = $namespace,
                    m.updated_at = datetime(),
                    m.auto_indexed = true
            """, name=qualified_module, filepath=file_path, namespace=namespace)

            # Functions
            for func in parsed["functions"]:
                qname = f"{qualified_module}.{func['name']}"
                session.run("""
                    MERGE (f:Function {qualified_name: $qname})
                    SET f.name = $name,
                        f.module = $module,
                        f.namespace = $namespace,
                        f.lineno = $lineno,
                        f.docstring = $docstring,
                        f.args = $args,
                        f.is_async = $is_async,
                        f.code = $code,
                        f.updated_at = datetime(),
                        f.auto_indexed = true
                """, qname=qname, name=func["name"], module=qualified_module,
                    namespace=namespace, lineno=func["lineno"],
                    docstring=func["docstring"], args=str(func["args"]),
                    is_async=func.get("is_async", False),
                    code=func.get("code", "")[:3000])

                # Module → Function 관계
                session.run("""
                    MATCH (m:Module {name: $module})
                    MATCH (f:Function {qualified_name: $qname})
                    MERGE (m)-[:DEFINES]->(f)
                """, module=qualified_module, qname=qname)

                # CALLS 관계
                for call in func["calls"]:
                    session.run("""
                        MATCH (f:Function {qualified_name: $qname})
                        MATCH (target:Function {name: $call_name})
                        MERGE (f)-[:CALLS]->(target)
                    """, qname=qname, call_name=call)

                count += 1

            # Classes
            for cls in parsed["classes"]:
                qname = f"{qualified_module}.{cls['name']}"
                session.run("""
                    MERGE (c:Class {qualified_name: $qname})
                    SET c.name = $name,
                        c.module = $module,
                        c.namespace = $namespace,
                        c.lineno = $lineno,
                        c.docstring = $docstring,
                        c.bases = $bases,
                        c.updated_at = datetime(),
                        c.auto_indexed = true
                """, qname=qname, name=cls["name"], module=qualified_module,
                    namespace=namespace, lineno=cls["lineno"],
                    docstring=cls["docstring"], bases=str(cls["bases"]))

                # Module → Class 관계
                session.run("""
                    MATCH (m:Module {name: $module})
                    MATCH (c:Class {qualified_name: $qname})
                    MERGE (m)-[:DEFINES]->(c)
                """, module=qualified_module, qname=qname)

                # Class → Method 관계
                for method in cls["methods"]:
                    method_qname = f"{qname}.{method}"
                    session.run("""
                        MATCH (c:Class {qualified_name: $cqname})
                        MATCH (f:Function) WHERE f.qualified_name STARTS WITH $prefix AND f.name = $method
                        MERGE (c)-[:HAS_METHOD]->(f)
                    """, cqname=qname, prefix=qualified_module, method=method)

                count += 1

        driver.close()
    except Exception as e:
        print(f"[KG-Indexer] Neo4j error: {e}", file=sys.stderr)
        try:
            driver.close()
        except:
            pass

    return count


def log_indexing(file_path: str, namespace: str, count: int, parsed: dict):
    """인덱싱 이벤트 기록"""
    try:
        log_file = Path.home() / ".claude" / "mcp-kg-analytics" / "indexing_events.jsonl"
        log_file.parent.mkdir(parents=True, exist_ok=True)
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "incremental_index",
            "file_path": file_path,
            "namespace": namespace,
            "functions_count": len(parsed["functions"]),
            "classes_count": len(parsed["classes"]),
            "imports_count": len(parsed["imports"]),
            "nodes_upserted": count,
        }
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass


def main():
    file_path, content = get_written_file()

    if not file_path or not content:
        sys.exit(0)

    # Phase 10.5: 지원 확장자 (tree-sitter 7개 언어)
    supported_exts = ('.py', '.ts', '.tsx', '.js', '.jsx', '.java', '.go', '.rs')
    if not any(file_path.endswith(ext) for ext in supported_exts):
        sys.exit(0)

    if len(content) < 50:
        sys.exit(0)

    # Phase 10.5: tree-sitter 우선, Python AST 폴백
    if file_path.endswith(".py"):
        # Python: tree-sitter 시도 → AST 폴백
        parsed = parse_with_tree_sitter(content, file_path)
        if not parsed["functions"] and not parsed["classes"]:
            parsed = parse_python_ast(content, file_path)
    else:
        # JS/TS/Java/Go/Rust: tree-sitter 시도 → regex 폴백
        parsed = parse_with_tree_sitter(content, file_path)
        if not parsed["functions"] and not parsed["classes"]:
            parsed = parse_typescript_regex(content, file_path)

    if not parsed["functions"] and not parsed["classes"]:
        sys.exit(0)

    # 프로젝트 네임스페이스
    namespace = get_project_namespace(file_path)

    # Neo4j에 MERGE
    count = upsert_to_neo4j(parsed, file_path, namespace)

    # 로깅
    log_indexing(file_path, namespace, count, parsed)

    funcs = [f["name"] for f in parsed["functions"]]
    classes = [c["name"] for c in parsed["classes"]]
    print(f"[KG-Indexer] {namespace}: +{count} nodes ({len(funcs)}F {len(classes)}C) from {Path(file_path).name}", file=sys.stderr)


if __name__ == "__main__":
    main()
