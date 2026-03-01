"""
Graph-Driven Auto Test Generator (Phase 5.4 → 6.5 Multi-Language)
==================================================================
지식그래프에서 함수 시그니처, 호출 관계, 유사 함수의 패턴을 분석하여
테스트 스켈레톤을 자동 생성.

지원 언어:
  - Python → pytest 스켈레톤
  - TypeScript (.ts/.tsx) → Jest 스켈레톤
  - JavaScript (.js/.jsx) → Jest 스켈레톤

MCP 도구: suggest_tests(function_name)
"""

import logging
from typing import Dict, Any, List, Optional

logger = logging.getLogger(__name__)


class AutoTestGenerator:
    """그래프 기반 자동 테스트 제안 엔진 (Multi-Language)"""

    def __init__(self, driver):
        self.driver = driver

    def suggest_tests(self, function_name: str) -> Dict[str, Any]:
        """함수에 대한 테스트 스켈레톤을 지식그래프 기반으로 생성.

        1단계: 대상 함수 정보 (시그니처, 모듈, docstring) 수집
        2단계: 호출하는 함수들 → mock 후보 추출
        3단계: 유사 함수 검색 → 테스트 패턴 참고
        4단계: 언어 감지 → 적절한 프레임워크 선택
        5단계: 테스트 스켈레톤 조립
        """
        try:
            with self.driver.session() as session:
                # 1. 대상 함수 정보 (file_path, language 포함)
                target = session.run("""
                    MATCH (f:Function)
                    WHERE toLower(f.name) = toLower($name) OR f.qualified_name CONTAINS $name
                    RETURN f.name AS name, f.qualified_name AS qname,
                           f.args AS args, f.docstring AS docstring,
                           f.module AS module, f.code AS code,
                           f.start_line AS start_line, f.end_line AS end_line,
                           f.file_path AS file_path, f.language AS language
                    LIMIT 1
                """, name=function_name).single()

                if not target:
                    return {"success": False, "error": f"Function '{function_name}' not found."}

                func_info = dict(target)

                # 2. 호출하는 함수들 (mock 후보)
                deps = session.run("""
                    MATCH (f:Function)-[:CALLS]->(dep:Function)
                    WHERE toLower(f.name) = toLower($name)
                    RETURN dep.name AS name, dep.module AS module,
                           dep.args AS args
                    LIMIT 10
                """, name=function_name)
                mock_candidates = [dict(r) for r in deps]

                # 3. 호출되는 곳 (사용 패턴 참고)
                callers = session.run("""
                    MATCH (caller:Function)-[:CALLS]->(f:Function)
                    WHERE toLower(f.name) = toLower($name)
                    RETURN caller.name AS name, caller.module AS module
                    LIMIT 5
                """, name=function_name)
                usage_patterns = [dict(r) for r in callers]

                # 4. 같은 모듈의 다른 함수 (테스트 커버리지 후보)
                siblings = []
                if func_info.get("module"):
                    sib_result = session.run("""
                        MATCH (m:Module)-[:DEFINES]->(f:Function)
                        WHERE m.name = $module AND f.name <> $name
                        RETURN f.name AS name, f.args AS args
                        LIMIT 5
                    """, module=func_info["module"], name=function_name)
                    siblings = [dict(r) for r in sib_result]

            # 5. 언어 감지 및 테스트 스켈레톤 생성
            language = self._detect_language(func_info)
            skeleton = self._build_test_skeleton(func_info, mock_candidates, usage_patterns, siblings)

            return {
                "success": True,
                "function": func_info,
                "language": language,
                "test_framework": "jest" if language in ("typescript", "javascript") else "pytest",
                "mock_candidates": mock_candidates,
                "usage_patterns": usage_patterns,
                "siblings": siblings,
                "test_skeleton": skeleton,
            }

        except Exception as e:
            logger.error(f"Auto test gen failed: {e}")
            return {"success": False, "error": str(e)}

    # ──────────────────────────────────────────────
    # Language Detection
    # ──────────────────────────────────────────────

    def _detect_language(self, func_info: Dict) -> str:
        """노드의 file_path 또는 language 프로퍼티 기반 언어 감지."""
        # 1. language 프로퍼티 직접 확인
        lang = func_info.get("language") or ""
        if lang:
            lang_lower = lang.lower()
            if lang_lower in ("typescript", "javascript", "python"):
                return lang_lower
            # 축약형 매핑
            lang_map = {"ts": "typescript", "js": "javascript", "py": "python"}
            if lang_lower in lang_map:
                return lang_map[lang_lower]

        # 2. file_path 확장자 확인
        file_path = func_info.get("file_path") or func_info.get("qname") or ""
        if file_path:
            if file_path.endswith(".ts") or file_path.endswith(".tsx"):
                return "typescript"
            elif file_path.endswith(".js") or file_path.endswith(".jsx"):
                return "javascript"
            elif file_path.endswith(".py"):
                return "python"

        # 3. module 이름으로 추론
        module = func_info.get("module") or ""
        if module:
            if any(ext in module for ext in [".ts", ".tsx"]):
                return "typescript"
            elif any(ext in module for ext in [".js", ".jsx"]):
                return "javascript"

        return "python"  # default

    # ──────────────────────────────────────────────
    # Skeleton Router
    # ──────────────────────────────────────────────

    def _build_test_skeleton(
        self,
        func_info: Dict,
        mock_candidates: List[Dict],
        usage_patterns: List[Dict],
        siblings: List[Dict],
    ) -> str:
        """언어에 따라 적절한 테스트 스켈레톤을 생성."""
        language = self._detect_language(func_info)

        if language == "typescript":
            return self._build_jest_skeleton(func_info, mock_candidates, usage_patterns, siblings, use_ts=True)
        elif language == "javascript":
            return self._build_jest_skeleton(func_info, mock_candidates, usage_patterns, siblings, use_ts=False)
        else:
            return self._build_pytest_skeleton(func_info, mock_candidates, usage_patterns, siblings)

    # ──────────────────────────────────────────────
    # Python / pytest Skeleton
    # ──────────────────────────────────────────────

    def _build_pytest_skeleton(
        self,
        func_info: Dict,
        mock_candidates: List[Dict],
        usage_patterns: List[Dict],
        siblings: List[Dict],
    ) -> str:
        """pytest 테스트 스켈레톤 코드 생성 (Python)."""
        name = func_info["name"]
        args_str = func_info.get("args") or ""
        module = func_info.get("module") or "module"
        docstring = func_info.get("docstring") or ""

        # 파라미터 파싱 (간단한 구현)
        params = self._parse_params(args_str)

        lines = [
            f'"""Auto-generated test skeleton for {name}',
            f'Module: {module}',
        ]
        if docstring:
            lines.append(f'Description: {docstring[:100]}')
        lines.append('"""')
        lines.append(f'import pytest')

        # Mock imports
        if mock_candidates:
            mock_modules = set()
            for mc in mock_candidates:
                if mc.get("module"):
                    mock_modules.add(mc["module"])
            if mock_modules:
                lines.append('from unittest.mock import patch, MagicMock')

        lines.append('')

        # Import 추정
        module_path = module.replace(".", "/") if module else "module"
        lines.append(f'# from {module} import {name}')
        lines.append('')

        # 기본 테스트: Happy path
        lines.append('')
        lines.append(f'class Test{name.replace("_", " ").title().replace(" ", "")}:')
        lines.append(f'    """Tests for {name}"""')
        lines.append('')

        # Test 1: Basic call
        lines.append(f'    def test_{name}_basic(self):')
        lines.append(f'        """기본 동작 테스트"""')
        if params:
            param_examples = ", ".join(self._suggest_param_value(p) for p in params)
            lines.append(f'        result = {name}({param_examples})')
        else:
            lines.append(f'        result = {name}()')
        lines.append(f'        assert result is not None')
        lines.append('')

        # Test 2: Edge cases
        if params:
            lines.append(f'    def test_{name}_edge_cases(self):')
            lines.append(f'        """엣지 케이스 테스트"""')
            for p in params[:3]:
                edge = self._suggest_edge_case(p)
                if edge:
                    lines.append(f'        # Edge case: {p["name"]} = {edge}')
            lines.append(f'        pass  # Fill in edge case assertions')
            lines.append('')

        # Test 3: Error handling
        lines.append(f'    def test_{name}_error_handling(self):')
        lines.append(f'        """에러 처리 테스트"""')
        lines.append(f'        with pytest.raises(Exception):')
        lines.append(f'            {name}(None)  # Invalid input')
        lines.append('')

        # Test 4: Mock dependencies
        if mock_candidates:
            dep = mock_candidates[0]
            dep_name = dep["name"]
            dep_module = dep.get("module") or module
            lines.append(f'    @patch("{dep_module}.{dep_name}")')
            lines.append(f'    def test_{name}_with_mocked_{dep_name}(self, mock_{dep_name}):')
            lines.append(f'        """의존성 격리 테스트: {dep_name} mock"""')
            lines.append(f'        mock_{dep_name}.return_value = None  # Configure mock')
            if params:
                param_examples = ", ".join(self._suggest_param_value(p) for p in params)
                lines.append(f'        result = {name}({param_examples})')
            else:
                lines.append(f'        result = {name}()')
            lines.append(f'        mock_{dep_name}.assert_called_once()')
            lines.append('')

        return "\n".join(lines)

    # ──────────────────────────────────────────────
    # TypeScript / JavaScript / Jest Skeleton
    # ──────────────────────────────────────────────

    def _build_jest_skeleton(
        self,
        func_info: Dict,
        mock_candidates: List[Dict],
        usage_patterns: List[Dict],
        siblings: List[Dict],
        use_ts: bool = True,
    ) -> str:
        """Jest 테스트 스켈레톤 코드 생성 (TypeScript/JavaScript)."""
        name = func_info["name"]
        args_str = func_info.get("args") or ""
        module = func_info.get("module") or "module"
        docstring = func_info.get("docstring") or ""
        params = self._parse_params(args_str)

        ext = "ts" if use_ts else "js"
        lang_label = "TypeScript" if use_ts else "JavaScript"

        lines = [
            f"/**",
            f" * Auto-generated test skeleton for {name}",
            f" * Module: {module}",
            f" * Language: {lang_label}",
        ]
        if docstring:
            lines.append(f" * Description: {docstring[:100]}")
        lines.append(f" */")
        lines.append(f"")

        # Import target function
        module_path = module.replace(".", "/") if module else "./module"
        lines.append(f"import {{ {name} }} from '{module_path}';")
        lines.append(f"")

        # Mock imports
        if mock_candidates:
            for mc in mock_candidates[:3]:
                mc_module = mc.get("module", "").replace(".", "/") or "./deps"
                lines.append(f"jest.mock('{mc_module}');")
            lines.append(f"")

        # describe block
        lines.append(f"describe('{name}', () => {{")

        # Test 1: Basic call
        lines.append(f"  it('should work with basic input', () => {{")
        if params:
            param_examples = ", ".join(self._suggest_js_param_value(p) for p in params)
            lines.append(f"    const result = {name}({param_examples});")
        else:
            lines.append(f"    const result = {name}();")
        lines.append(f"    expect(result).toBeDefined();")
        lines.append(f"  }});")
        lines.append(f"")

        # Test 2: Edge cases
        if params:
            lines.append(f"  it('should handle edge cases', () => {{")
            for p in params[:3]:
                edge = self._suggest_js_edge_case(p)
                if edge:
                    lines.append(f"    // Edge case: {p['name']} = {edge}")
            lines.append(f"    // Fill in edge case assertions")
            lines.append(f"  }});")
            lines.append(f"")

        # Test 3: Error handling
        lines.append(f"  it('should throw on invalid input', () => {{")
        if use_ts:
            lines.append(f"    expect(() => {name}(null as any)).toThrow();")
        else:
            lines.append(f"    expect(() => {name}(null)).toThrow();")
        lines.append(f"  }});")
        lines.append(f"")

        # Test 4: Mock dependency
        if mock_candidates:
            dep = mock_candidates[0]
            dep_name = dep["name"]
            dep_title = dep_name[0].upper() + dep_name[1:] if dep_name else "Dep"
            lines.append(f"  it('should call {dep_name} dependency', () => {{")
            lines.append(f"    const mock{dep_title} = jest.fn();")
            if params:
                param_examples = ", ".join(self._suggest_js_param_value(p) for p in params)
                lines.append(f"    {name}({param_examples});")
            else:
                lines.append(f"    {name}();")
            lines.append(f"    // expect(mock{dep_title}).toHaveBeenCalled();")
            lines.append(f"  }});")

        lines.append(f"}});")

        return "\n".join(lines)

    # ──────────────────────────────────────────────
    # Parameter Parsing (Shared)
    # ──────────────────────────────────────────────

    def _parse_params(self, args_input) -> List[Dict]:
        """인자 문자열(또는 리스트)을 파싱하여 파라미터 목록 반환.

        제네릭 타입(예: Record<string, any>, Array<Map<K, V>>)의 내부 콤마를
        파라미터 구분자로 오인하지 않도록 angle-bracket depth를 추적.
        """
        if not args_input:
            return []

        # Neo4j에서 list로 저장된 경우
        if isinstance(args_input, list):
            return [
                {"name": a, "type": "", "default": None}
                for a in args_input if a not in ("self", "cls", "this")
            ]

        args_str = str(args_input)
        if args_str == "()":
            return []

        # "self, query: str, limit: int = 10" 같은 문자열 파싱
        args_str = args_str.strip("()")

        # 제네릭 타입 내부 콤마를 보호하기 위해 angle-bracket aware split
        parts = self._split_params_aware(args_str)

        params = []
        for part in parts:
            part = part.strip()
            if not part or part in ("self", "cls", "this"):
                continue

            name = part.split(":")[0].split("=")[0].strip()
            type_hint = ""
            default = None

            if ":" in part:
                # 첫 번째 콜론 이후, = 이전까지가 타입
                after_colon = part.split(":", 1)[1]
                if "=" in after_colon:
                    type_hint = after_colon.split("=")[0].strip()
                    default = after_colon.split("=", 1)[1].strip()
                else:
                    type_hint = after_colon.strip()
            elif "=" in part:
                default = part.split("=", 1)[1].strip()

            params.append({"name": name, "type": type_hint, "default": default})

        return params

    @staticmethod
    def _split_params_aware(args_str: str) -> List[str]:
        """콤마로 파라미터를 분리하되 <> 내부의 콤마는 무시.

        예: "items: Array<string>, config: Record<string, any>, limit: number"
        → ["items: Array<string>", "config: Record<string, any>", "limit: number"]
        """
        parts = []
        depth = 0
        current = []
        for ch in args_str:
            if ch == "<":
                depth += 1
                current.append(ch)
            elif ch == ">":
                depth -= 1
                current.append(ch)
            elif ch == "," and depth == 0:
                parts.append("".join(current))
                current = []
            else:
                current.append(ch)
        if current:
            parts.append("".join(current))
        return parts

    # ──────────────────────────────────────────────
    # Python Parameter Helpers
    # ──────────────────────────────────────────────

    def _suggest_param_value(self, param: Dict) -> str:
        """파라미터 타입에 따른 예시 값 제안 (Python)."""
        type_map = {
            "str": '"test_value"',
            "int": "42",
            "float": "3.14",
            "bool": "True",
            "list": "[]",
            "dict": "{}",
            "List": "[]",
            "Dict": "{}",
            "Optional": "None",
        }
        t = param.get("type", "")
        for key, val in type_map.items():
            if key in t:
                return val
        if param.get("default"):
            return param["default"]
        return '"test"'

    def _suggest_edge_case(self, param: Dict) -> Optional[str]:
        """파라미터 타입별 엣지 케이스 제안 (Python)."""
        t = param.get("type", "")
        if "str" in t:
            return '""  # empty string'
        if "int" in t:
            return "0, -1, sys.maxsize"
        if "list" in t or "List" in t:
            return "[]  # empty list"
        if "dict" in t or "Dict" in t:
            return "{}  # empty dict"
        return None

    # ──────────────────────────────────────────────
    # JS/TS Parameter Helpers
    # ──────────────────────────────────────────────

    def _suggest_js_param_value(self, param: Dict) -> str:
        """JS/TS 파라미터 타입에 따른 예시 값 제안.

        Note: 검사 순서가 중요 -- 복합 타입(Array, Record, Promise)을
        단순 타입(string, number)보다 먼저 검사하여 Array<string> 등이
        string으로 잘못 매핑되는 것을 방지.
        """
        t_lower = (param.get("type") or "").lower()

        # 복합 타입 먼저 검사 (string/number 등의 부분 매칭 방지)
        compound_map = [
            ("array", "[]"),
            ("record", "{}"),
            ("promise", "Promise.resolve()"),
            ("map", "new Map()"),
            ("set", "new Set()"),
        ]
        for key, val in compound_map:
            if key in t_lower:
                return val

        # 단순 타입
        simple_map = [
            ("string", "'test_value'"),
            ("number", "42"),
            ("boolean", "true"),
            ("object", "{}"),
            ("void", "undefined"),
            ("null", "null"),
            ("undefined", "undefined"),
            ("any", "'test'"),
        ]
        for key, val in simple_map:
            if key in t_lower:
                return val

        if param.get("default"):
            return param["default"]
        return "'test'"

    def _suggest_js_edge_case(self, param: Dict) -> Optional[str]:
        """JS/TS 파라미터별 엣지 케이스 제안.

        Note: 검사 순서가 중요 -- 복합 타입을 먼저 검사.
        """
        t_lower = (param.get("type") or "").lower()

        # 복합 타입 먼저
        if "array" in t_lower:
            return "[]  // empty array"
        if "record" in t_lower or "object" in t_lower:
            return "{}  // empty object"
        if "map" in t_lower:
            return "new Map()  // empty map"
        if "set" in t_lower:
            return "new Set()  // empty set"

        # 단순 타입
        if "string" in t_lower:
            return "''  // empty string"
        if "number" in t_lower:
            return "0, -1, Number.MAX_SAFE_INTEGER"
        if "boolean" in t_lower:
            return "false"
        return None
