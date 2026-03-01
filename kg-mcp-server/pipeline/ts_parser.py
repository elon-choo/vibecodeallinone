"""
Tree-sitter Code Parser (Phase 10)
====================================
tree-sitter 기반 다국어 코드 파서.
40+ 언어 지원, 증분 파싱, AST 기반 계층적 청킹.

Cursor, Aider, Continue.dev 등이 사용하는 업계 표준 파서.

Supported: Python, JavaScript, TypeScript, Java, Go, Rust
"""

import logging
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, field

import tree_sitter

logger = logging.getLogger(__name__)

# Language grammars
_LANGUAGES = {}


def _get_language(lang_name: str) -> Optional[tree_sitter.Language]:
    """Language grammar을 로드 (캐시)."""
    if lang_name in _LANGUAGES:
        return _LANGUAGES[lang_name]
    try:
        if lang_name == "python":
            import tree_sitter_python
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_python.language())
        elif lang_name == "javascript":
            import tree_sitter_javascript
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_javascript.language())
        elif lang_name == "typescript":
            import tree_sitter_typescript
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_typescript.language_typescript())
        elif lang_name == "tsx":
            import tree_sitter_typescript
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_typescript.language_tsx())
        elif lang_name == "java":
            import tree_sitter_java
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_java.language())
        elif lang_name == "go":
            import tree_sitter_go
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_go.language())
        elif lang_name == "rust":
            import tree_sitter_rust
            _LANGUAGES[lang_name] = tree_sitter.Language(tree_sitter_rust.language())
        else:
            return None
        return _LANGUAGES[lang_name]
    except ImportError:
        logger.warning(f"tree-sitter grammar not installed for: {lang_name}")
        return None


# File extension → language mapping
EXT_TO_LANG = {
    ".py": "python", ".js": "javascript", ".jsx": "javascript",
    ".ts": "typescript", ".tsx": "tsx",
    ".java": "java", ".go": "go", ".rs": "rust",
}


@dataclass
class CodeEntity:
    """파싱된 코드 엔티티 (함수/클래스/메서드)."""
    name: str
    type: str  # "function", "class", "method"
    language: str
    file_path: str
    start_line: int
    end_line: int
    signature: str  # 함수 시그니처
    body: str  # 전체 소스코드
    docstring: str = ""
    parent_class: str = ""  # 메서드인 경우 소속 클래스
    decorators: List[str] = field(default_factory=list)
    parameters: List[str] = field(default_factory=list)
    return_type: str = ""
    imports: List[str] = field(default_factory=list)


class TreeSitterParser:
    """tree-sitter 기반 다국어 코드 파서."""

    def __init__(self):
        self._parsers = {}

    def _get_parser(self, lang_name: str) -> Optional[tree_sitter.Parser]:
        """언어별 Parser 인스턴스 (캐시)."""
        if lang_name in self._parsers:
            return self._parsers[lang_name]
        language = _get_language(lang_name)
        if not language:
            return None
        parser = tree_sitter.Parser(language)
        self._parsers[lang_name] = parser
        return parser

    def detect_language(self, file_path: str) -> Optional[str]:
        """파일 확장자로 언어 감지."""
        ext = Path(file_path).suffix.lower()
        return EXT_TO_LANG.get(ext)

    def parse_file(self, file_path: str, source: Optional[str] = None) -> List[CodeEntity]:
        """파일을 파싱하여 함수/클래스/메서드 목록 반환."""
        lang = self.detect_language(file_path)
        if not lang:
            return []

        if source is None:
            try:
                source = Path(file_path).read_text(encoding="utf-8")
            except Exception as e:
                logger.warning(f"Cannot read {file_path}: {e}")
                return []

        parser = self._get_parser(lang)
        if not parser:
            return []

        source_bytes = source.encode("utf-8")
        tree = parser.parse(source_bytes)
        entities = []

        if lang == "python":
            entities = self._extract_python(tree, source_bytes, file_path, lang)
        elif lang in ("javascript", "typescript", "tsx"):
            entities = self._extract_js_ts(tree, source_bytes, file_path, lang)
        elif lang == "java":
            entities = self._extract_java(tree, source_bytes, file_path, lang)
        elif lang == "go":
            entities = self._extract_go(tree, source_bytes, file_path, lang)
        elif lang == "rust":
            entities = self._extract_rust(tree, source_bytes, file_path, lang)

        return entities

    def _node_text(self, node, source_bytes: bytes) -> str:
        """AST 노드의 소스 텍스트 (UTF-8 바이트 오프셋 기반)."""
        return source_bytes[node.start_byte:node.end_byte].decode("utf-8", errors="replace")

    def _find_children(self, node, type_name: str) -> list:
        """특정 타입의 자식 노드 검색."""
        return [c for c in node.children if c.type == type_name]

    # ── Python ──
    def _extract_python(self, tree, source_bytes: bytes, file_path: str, lang: str) -> List[CodeEntity]:
        entities = []
        root = tree.root_node

        # Top-level imports
        imports = []
        for child in root.children:
            if child.type in ("import_statement", "import_from_statement"):
                imports.append(self._node_text(child, source_bytes).strip())

        # Functions and classes
        for child in root.children:
            if child.type == "function_definition":
                entities.append(self._parse_python_function(child, source_bytes, file_path, lang, imports))
            elif child.type == "class_definition":
                cls = self._parse_python_class(child, source_bytes, file_path, lang, imports)
                entities.append(cls)
                # Methods
                body = next((c for c in child.children if c.type == "block"), None)
                if body:
                    for stmt in body.children:
                        if stmt.type == "function_definition":
                            method = self._parse_python_function(stmt, source_bytes, file_path, lang, imports)
                            method.type = "method"
                            method.parent_class = cls.name
                            entities.append(method)
            elif child.type == "decorated_definition":
                inner = next((c for c in child.children if c.type in ("function_definition", "class_definition")), None)
                if inner:
                    decorators = [self._node_text(d, source_bytes) for d in child.children if d.type == "decorator"]
                    if inner.type == "function_definition":
                        ent = self._parse_python_function(inner, source_bytes, file_path, lang, imports)
                        ent.decorators = decorators
                        entities.append(ent)
                    elif inner.type == "class_definition":
                        ent = self._parse_python_class(inner, source_bytes, file_path, lang, imports)
                        ent.decorators = decorators
                        entities.append(ent)

        return entities

    def _parse_python_function(self, node, source_bytes, file_path, lang, imports) -> CodeEntity:
        name_node = next((c for c in node.children if c.type == "identifier"), None)
        name = self._node_text(name_node, source_bytes) if name_node else "anonymous"
        params_node = next((c for c in node.children if c.type == "parameters"), None)
        params_text = self._node_text(params_node, source_bytes) if params_node else "()"
        return_node = next((c for c in node.children if c.type == "type"), None)
        return_type = self._node_text(return_node, source_bytes) if return_node else ""
        body = self._node_text(node, source_bytes)
        sig = f"def {name}{params_text}" + (f" -> {return_type}" if return_type else "")
        # Docstring
        doc = ""
        block = next((c for c in node.children if c.type == "block"), None)
        if block and block.children:
            first = block.children[0]
            if first.type == "expression_statement":
                inner = first.children[0] if first.children else None
                if inner and inner.type == "string":
                    doc = self._node_text(inner, source_bytes).strip("\"'")

        return CodeEntity(
            name=name, type="function", language=lang, file_path=file_path,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            signature=sig, body=body, docstring=doc,
            parameters=params_text.strip("()").split(", ") if params_text != "()" else [],
            return_type=return_type, imports=imports,
        )

    def _parse_python_class(self, node, source_bytes, file_path, lang, imports) -> CodeEntity:
        name_node = next((c for c in node.children if c.type == "identifier"), None)
        name = self._node_text(name_node, source_bytes) if name_node else "AnonymousClass"
        body = self._node_text(node, source_bytes)
        return CodeEntity(
            name=name, type="class", language=lang, file_path=file_path,
            start_line=node.start_point[0] + 1, end_line=node.end_point[0] + 1,
            signature=f"class {name}", body=body, imports=imports,
        )

    # ── JavaScript/TypeScript ──
    def _extract_js_ts(self, tree, source_bytes: bytes, file_path: str, lang: str) -> List[CodeEntity]:
        entities = []
        root = tree.root_node
        imports = []

        for child in root.children:
            if child.type in ("import_statement", "import_declaration"):
                imports.append(self._node_text(child, source_bytes).strip())

        self._walk_js_ts(root, source_bytes, file_path, lang, imports, entities, parent_class="")
        return entities

    def _walk_js_ts(self, node, source_bytes, file_path, lang, imports, entities, parent_class):
        for child in node.children:
            if child.type in ("function_declaration", "function"):
                name_node = next((c for c in child.children if c.type == "identifier"), None)
                name = self._node_text(name_node, source_bytes) if name_node else "anonymous"
                entities.append(CodeEntity(
                    name=name, type="function", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=f"function {name}(...)", body=self._node_text(child, source_bytes),
                    imports=imports,
                ))
            elif child.type == "class_declaration":
                name_node = next((c for c in child.children if c.type == "identifier"), None)
                cls_name = self._node_text(name_node, source_bytes) if name_node else "AnonymousClass"
                entities.append(CodeEntity(
                    name=cls_name, type="class", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=f"class {cls_name}", body=self._node_text(child, source_bytes),
                    imports=imports,
                ))
                # Walk class body for methods
                body = next((c for c in child.children if c.type == "class_body"), None)
                if body:
                    self._walk_js_ts(body, source_bytes, file_path, lang, imports, entities, parent_class=cls_name)
            elif child.type == "method_definition":
                name_node = next((c for c in child.children if c.type == "property_identifier"), None)
                name = self._node_text(name_node, source_bytes) if name_node else "anonymous"
                entities.append(CodeEntity(
                    name=name, type="method", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=f"{name}(...)", body=self._node_text(child, source_bytes),
                    parent_class=parent_class, imports=imports,
                ))
            elif child.type in ("export_statement", "lexical_declaration", "variable_declaration"):
                # Arrow functions: const foo = () => {}
                self._walk_js_ts(child, source_bytes, file_path, lang, imports, entities, parent_class)
            elif child.type == "variable_declarator":
                name_node = next((c for c in child.children if c.type == "identifier"), None)
                value_node = next((c for c in child.children if c.type in ("arrow_function", "function")), None)
                if name_node and value_node:
                    name = self._node_text(name_node, source_bytes)
                    entities.append(CodeEntity(
                        name=name, type="function", language=lang, file_path=file_path,
                        start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                        signature=f"const {name} = (...) =>", body=self._node_text(child, source_bytes),
                        imports=imports,
                    ))

    # ── Java ──
    def _extract_java(self, tree, source_bytes: bytes, file_path: str, lang: str) -> List[CodeEntity]:
        entities = []
        root = tree.root_node
        for child in root.children:
            if child.type == "class_declaration":
                name_node = next((c for c in child.children if c.type == "identifier"), None)
                cls_name = self._node_text(name_node, source_bytes) if name_node else "?"
                entities.append(CodeEntity(
                    name=cls_name, type="class", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=f"class {cls_name}", body=self._node_text(child, source_bytes)[:500],
                ))
                body = next((c for c in child.children if c.type == "class_body"), None)
                if body:
                    for member in body.children:
                        if member.type == "method_declaration":
                            mname = next((c for c in member.children if c.type == "identifier"), None)
                            entities.append(CodeEntity(
                                name=self._node_text(mname, source_bytes) if mname else "?",
                                type="method", language=lang, file_path=file_path,
                                start_line=member.start_point[0]+1, end_line=member.end_point[0]+1,
                                signature=self._node_text(member, source_bytes).split("{")[0].strip(),
                                body=self._node_text(member, source_bytes),
                                parent_class=cls_name,
                            ))
        return entities

    # ── Go ──
    def _extract_go(self, tree, source_bytes: bytes, file_path: str, lang: str) -> List[CodeEntity]:
        entities = []
        root = tree.root_node
        for child in root.children:
            if child.type == "function_declaration":
                name_node = next((c for c in child.children if c.type == "identifier"), None)
                name = self._node_text(name_node, source_bytes) if name_node else "?"
                entities.append(CodeEntity(
                    name=name, type="function", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=f"func {name}(...)", body=self._node_text(child, source_bytes),
                ))
            elif child.type == "method_declaration":
                name_node = next((c for c in child.children if c.type == "field_identifier"), None)
                name = self._node_text(name_node, source_bytes) if name_node else "?"
                entities.append(CodeEntity(
                    name=name, type="method", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=self._node_text(child, source_bytes).split("{")[0].strip(),
                    body=self._node_text(child, source_bytes),
                ))
        return entities

    # ── Rust ──
    def _extract_rust(self, tree, source_bytes: bytes, file_path: str, lang: str) -> List[CodeEntity]:
        entities = []
        root = tree.root_node
        for child in root.children:
            if child.type == "function_item":
                name_node = next((c for c in child.children if c.type == "identifier"), None)
                name = self._node_text(name_node, source_bytes) if name_node else "?"
                entities.append(CodeEntity(
                    name=name, type="function", language=lang, file_path=file_path,
                    start_line=child.start_point[0]+1, end_line=child.end_point[0]+1,
                    signature=f"fn {name}(...)", body=self._node_text(child, source_bytes),
                ))
            elif child.type == "impl_item":
                type_node = next((c for c in child.children if c.type == "type_identifier"), None)
                cls_name = self._node_text(type_node, source_bytes) if type_node else "?"
                body = next((c for c in child.children if c.type == "declaration_list"), None)
                if body:
                    for member in body.children:
                        if member.type == "function_item":
                            mname = next((c for c in member.children if c.type == "identifier"), None)
                            entities.append(CodeEntity(
                                name=self._node_text(mname, source_bytes) if mname else "?",
                                type="method", language=lang, file_path=file_path,
                                start_line=member.start_point[0]+1, end_line=member.end_point[0]+1,
                                signature=f"fn {self._node_text(mname, source_bytes) if mname else '?'}(...)",
                                body=self._node_text(member, source_bytes),
                                parent_class=cls_name,
                            ))
        return entities
