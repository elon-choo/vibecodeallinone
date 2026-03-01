#!/usr/bin/env python3
"""
KG Bulk Indexer - 프로젝트 전체를 한 번에 Neo4j에 인덱싱
============================================================
사용법: python3 ~/.claude/hooks/kg-bulk-indexer.py /path/to/project

지원 언어: Python (.py)
제외 경로: venv, node_modules, __pycache__, .git, .next, dist, build
"""

import ast
import sys
import os
from pathlib import Path
from datetime import datetime

EXCLUDE_DIRS = {
    "venv", ".venv", "env", "node_modules", "__pycache__", ".git",
    ".next", "dist", "build", ".tox", ".pytest_cache", ".mypy_cache",
    "egg-info", ".eggs", "site-packages", ".claude"
}

def _load_power_pack_env():
    """Load ~/.claude/power-pack.env into os.environ if keys not already set."""
    env_file = Path.home() / ".claude" / "power-pack.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())

_load_power_pack_env()

NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_AUTH = (os.getenv("NEO4J_USERNAME", "neo4j"), os.getenv("NEO4J_PASSWORD", ""))

SUPPORTED_EXTS = {".py", ".ts", ".tsx", ".js", ".jsx"}


def find_source_files(project_dir: str) -> list:
    """프로젝트의 모든 소스 파일 찾기 (Python + TS/JS)"""
    files = []
    for root, dirs, filenames in os.walk(project_dir):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS and not d.startswith(".")]
        for fn in filenames:
            ext = os.path.splitext(fn)[1]
            if ext in SUPPORTED_EXTS and not fn.startswith("."):
                fp = os.path.join(root, fn)
                files.append(fp)
    return sorted(files)


def parse_python(content: str, file_path: str) -> dict:
    """AST 파싱 → 함수/클래스 추출"""
    try:
        tree = ast.parse(content)
    except SyntaxError:
        return {"functions": [], "classes": [], "imports": []}

    module_name = Path(file_path).stem
    functions, classes, imports = [], [], []

    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            doc = ast.get_docstring(node) or ""
            args = [a.arg for a in node.args.args if a.arg != "self"]
            calls = set()
            for child in ast.walk(node):
                if isinstance(child, ast.Call):
                    if isinstance(child.func, ast.Name):
                        calls.add(child.func.id)
                    elif isinstance(child.func, ast.Attribute):
                        calls.add(child.func.attr)
            functions.append({
                "name": node.name, "module": module_name,
                "lineno": node.lineno, "docstring": doc[:300],
                "args": args[:10], "calls": list(calls)[:20],
                "is_async": isinstance(node, ast.AsyncFunctionDef),
            })
        elif isinstance(node, ast.ClassDef):
            doc = ast.get_docstring(node) or ""
            bases = []
            for b in node.bases:
                if isinstance(b, ast.Name):
                    bases.append(b.id)
                elif isinstance(b, ast.Attribute):
                    bases.append(f"{b.value.id if isinstance(b.value, ast.Name) else ''}.{b.attr}")
            methods = [n.name for n in node.body if isinstance(n, (ast.FunctionDef, ast.AsyncFunctionDef))]
            classes.append({
                "name": node.name, "module": module_name,
                "lineno": node.lineno, "docstring": doc[:300],
                "bases": bases[:5], "methods": methods[:20],
            })
        elif isinstance(node, ast.Import):
            for alias in node.names:
                imports.append(alias.name)
        elif isinstance(node, ast.ImportFrom):
            if node.module:
                imports.append(node.module)

    return {"functions": functions, "classes": classes, "imports": imports}


import re

def parse_typescript(content: str, file_path: str) -> dict:
    """Regex 기반 TS/JS 파싱 → 함수/클래스/인터페이스 추출"""
    module_name = Path(file_path).stem
    functions, classes, imports = [], [], []

    lines = content.split("\n")

    # 1. function declarations: function name(...) / async function name(...)
    for m in re.finditer(r'(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)', content):
        name, args = m.group(1), m.group(2)
        lineno = content[:m.start()].count("\n") + 1
        # JSDoc 위 주석 추출
        doc = _extract_jsdoc(content, m.start())
        functions.append({
            "name": name, "module": module_name, "lineno": lineno,
            "docstring": doc[:300], "args": [a.strip().split(":")[0].strip() for a in args.split(",") if a.strip()][:10],
            "calls": [], "is_async": "async" in content[max(0,m.start()-20):m.start()],
        })

    # 2. Arrow functions: const name = (...) => / const name: Type = (...)
    for m in re.finditer(r'(?:export\s+)?(?:const|let|var)\s+(\w+)\s*(?::\s*\w[^=]*)?\s*=\s*(?:async\s+)?\(([^)]*)\)\s*(?::\s*\w[^=]*)?\s*=>', content):
        name, args = m.group(1), m.group(2)
        lineno = content[:m.start()].count("\n") + 1
        doc = _extract_jsdoc(content, m.start())
        functions.append({
            "name": name, "module": module_name, "lineno": lineno,
            "docstring": doc[:300], "args": [a.strip().split(":")[0].strip() for a in args.split(",") if a.strip()][:10],
            "calls": [], "is_async": "async" in content[max(0,m.start()-10):m.end()],
        })

    # 3. Class declarations
    for m in re.finditer(r'(?:export\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([\w,\s]+))?', content):
        name = m.group(1)
        base = m.group(2) or ""
        lineno = content[:m.start()].count("\n") + 1
        doc = _extract_jsdoc(content, m.start())
        # 메서드 추출 (클래스 블록 내)
        methods = _extract_class_methods(content, m.end())
        classes.append({
            "name": name, "module": module_name, "lineno": lineno,
            "docstring": doc[:300], "bases": [base] if base else [],
            "methods": methods[:20],
        })

    # 4. TypeScript interfaces/types as classes
    for m in re.finditer(r'(?:export\s+)?(?:interface|type)\s+(\w+)', content):
        name = m.group(1)
        lineno = content[:m.start()].count("\n") + 1
        doc = _extract_jsdoc(content, m.start())
        classes.append({
            "name": name, "module": module_name, "lineno": lineno,
            "docstring": doc[:300] or f"TypeScript type/interface",
            "bases": [], "methods": [],
        })

    # 5. React components: const Name = () => / const Name: React.FC
    for m in re.finditer(r'(?:export\s+)?(?:const|function)\s+([A-Z]\w+)\s*(?::\s*React\.FC[^=]*)?(?:\s*=\s*\([^)]*\)\s*(?::\s*\w+)?\s*=>)?', content):
        name = m.group(1)
        if not any(f["name"] == name for f in functions) and not any(c["name"] == name for c in classes):
            lineno = content[:m.start()].count("\n") + 1
            functions.append({
                "name": name, "module": module_name, "lineno": lineno,
                "docstring": f"React component", "args": ["props"],
                "calls": [], "is_async": False,
            })

    # imports
    for m in re.finditer(r'import\s+.*?from\s+[\'"]([^\'"]+)[\'"]', content):
        imports.append(m.group(1))

    return {"functions": functions, "classes": classes, "imports": imports}


def _extract_jsdoc(content: str, pos: int) -> str:
    """pos 직전의 JSDoc/주석 추출"""
    before = content[:pos].rstrip()
    if before.endswith("*/"):
        start = before.rfind("/**")
        if start != -1 and pos - start < 500:
            doc = before[start+3:-2].strip()
            doc = re.sub(r'\n\s*\*\s?', ' ', doc).strip()
            return doc
    return ""


def _extract_class_methods(content: str, start_pos: int) -> list:
    """클래스 본문에서 메서드 이름 추출"""
    methods = []
    brace_count = 0
    i = start_pos
    while i < len(content) and content[i] != '{':
        i += 1
    if i >= len(content):
        return methods
    brace_count = 1
    i += 1
    class_body = ""
    while i < len(content) and brace_count > 0:
        if content[i] == '{':
            brace_count += 1
        elif content[i] == '}':
            brace_count -= 1
        class_body += content[i]
        i += 1
    for m in re.finditer(r'(?:async\s+)?(\w+)\s*\([^)]*\)\s*(?::\s*\w+)?\s*\{', class_body):
        name = m.group(1)
        if name not in ('if', 'for', 'while', 'switch', 'catch', 'constructor'):
            methods.append(name)
    return methods


def upsert_batch(driver, parsed: dict, file_path: str, namespace: str):
    """Neo4j에 MERGE"""
    module_name = Path(file_path).stem
    qualified_module = f"{namespace}.{module_name}"
    count = 0

    with driver.session() as session:
        session.run("""
            MERGE (m:Module {name: $name})
            SET m.filepath = $filepath, m.namespace = $namespace,
                m.updated_at = datetime(), m.auto_indexed = true
        """, name=qualified_module, filepath=file_path, namespace=namespace)

        for func in parsed["functions"]:
            qname = f"{qualified_module}.{func['name']}"
            session.run("""
                MERGE (f:Function {qualified_name: $qname})
                SET f.name = $name, f.module = $module, f.namespace = $namespace,
                    f.lineno = $lineno, f.docstring = $docstring,
                    f.args = $args, f.is_async = $is_async,
                    f.updated_at = datetime(), f.auto_indexed = true
            """, qname=qname, name=func["name"], module=qualified_module,
                namespace=namespace, lineno=func["lineno"],
                docstring=func["docstring"], args=str(func["args"]),
                is_async=func["is_async"])

            session.run("""
                MATCH (m:Module {name: $module})
                MATCH (f:Function {qualified_name: $qname})
                MERGE (m)-[:DEFINES]->(f)
            """, module=qualified_module, qname=qname)

            for call in func["calls"]:
                session.run("""
                    MATCH (f:Function {qualified_name: $qname})
                    MATCH (target:Function {name: $call_name})
                    WHERE target.namespace = $namespace
                    MERGE (f)-[:CALLS]->(target)
                """, qname=qname, call_name=call, namespace=namespace)
            count += 1

        for cls in parsed["classes"]:
            qname = f"{qualified_module}.{cls['name']}"
            session.run("""
                MERGE (c:Class {qualified_name: $qname})
                SET c.name = $name, c.module = $module, c.namespace = $namespace,
                    c.lineno = $lineno, c.docstring = $docstring,
                    c.bases = $bases, c.updated_at = datetime(), c.auto_indexed = true
            """, qname=qname, name=cls["name"], module=qualified_module,
                namespace=namespace, lineno=cls["lineno"],
                docstring=cls["docstring"], bases=str(cls["bases"]))

            session.run("""
                MATCH (m:Module {name: $module})
                MATCH (c:Class {qualified_name: $qname})
                MERGE (m)-[:DEFINES]->(c)
            """, module=qualified_module, qname=qname)
            count += 1

    return count


def main():
    if len(sys.argv) < 2:
        print("Usage: python3 kg-bulk-indexer.py /path/to/project")
        print("       python3 kg-bulk-indexer.py /path/to/project --dry-run")
        sys.exit(1)

    project_dir = os.path.abspath(sys.argv[1])
    dry_run = "--dry-run" in sys.argv

    if not os.path.isdir(project_dir):
        print(f"Error: {project_dir} is not a directory")
        sys.exit(1)

    namespace = Path(project_dir).name
    print(f"\n{'[DRY RUN] ' if dry_run else ''}KG Bulk Indexer")
    print(f"  Project: {project_dir}")
    print(f"  Namespace: {namespace}")
    print(f"  Neo4j: {NEO4J_URI}")
    print()

    # 파일 찾기
    py_files = find_source_files(project_dir)
    print(f"  Found {len(py_files)} source files (.py/.ts/.tsx/.js/.jsx)")

    if not py_files:
        print("  No source files found. Exiting.")
        sys.exit(0)

    # Neo4j 연결
    driver = None
    if not dry_run:
        try:
            from neo4j import GraphDatabase
            driver = GraphDatabase.driver(NEO4J_URI, auth=NEO4J_AUTH, connection_timeout=5)
            driver.verify_connectivity()
        except Exception as e:
            print(f"  Error connecting to Neo4j: {e}")
            sys.exit(1)

    total_funcs = 0
    total_classes = 0
    total_nodes = 0
    errors = 0

    for fp in py_files:
        try:
            content = open(fp, encoding="utf-8", errors="ignore").read()
            if len(content) < 30:
                continue

            ext = os.path.splitext(fp)[1]
            if ext == ".py":
                parsed = parse_python(content, fp)
            else:
                parsed = parse_typescript(content, fp)
            nf = len(parsed["functions"])
            nc = len(parsed["classes"])

            if nf == 0 and nc == 0:
                continue

            total_funcs += nf
            total_classes += nc

            if not dry_run and driver:
                count = upsert_batch(driver, parsed, fp, namespace)
                total_nodes += count

            rel_path = os.path.relpath(fp, project_dir)
            print(f"  {'[scan]' if dry_run else '[index]'} {rel_path}: {nf}F {nc}C")

        except Exception as e:
            errors += 1
            rel_path = os.path.relpath(fp, project_dir)
            print(f"  [error] {rel_path}: {e}")

    if driver:
        driver.close()

    print(f"\n  {'Scan' if dry_run else 'Index'} complete:")
    print(f"    Files processed: {len(py_files)}")
    print(f"    Functions: {total_funcs}")
    print(f"    Classes: {total_classes}")
    if not dry_run:
        print(f"    Nodes upserted: {total_nodes}")
    print(f"    Errors: {errors}")
    print(f"    Namespace: {namespace}")


if __name__ == "__main__":
    main()
