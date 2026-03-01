"""컨텍스트 빌더 모듈"""
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


class ContextBuilder:
    """검색 결과를 LLM 컨텍스트로 변환"""

    def __init__(self, max_tokens: int = 4000):
        self.max_tokens = max_tokens
        # 간단한 토큰 추정 (문자 수 / 4)
        self.chars_per_token = 4

    def build(self, items: List[Dict], query: str = None) -> str:
        """컨텍스트 문자열 생성"""
        if not items:
            return "관련 정보를 찾을 수 없습니다."

        sections = []
        current_chars = 0
        max_chars = self.max_tokens * self.chars_per_token

        # 1. 코드 노드 섹션
        code_items = [i for i in items if i.get('type') in ['Function', 'Class', 'Module']]
        if code_items:
            code_section = self._build_code_section(code_items)
            if current_chars + len(code_section) <= max_chars:
                sections.append(code_section)
                current_chars += len(code_section)

        # 2. 패턴/지식 섹션
        pattern_items = [i for i in items if i.get('type') not in ['Function', 'Class', 'Module', None]]
        if pattern_items:
            pattern_section = self._build_pattern_section(pattern_items)
            if current_chars + len(pattern_section) <= max_chars:
                sections.append(pattern_section)
                current_chars += len(pattern_section)

        # 3. 보안 경고 섹션 (있으면)
        security_items = [i for i in items if i.get('cwe_id') or i.get('severity')]
        if security_items:
            security_section = self._build_security_section(security_items)
            if current_chars + len(security_section) <= max_chars:
                sections.append(security_section)

        return "\n\n".join(sections) if sections else "관련 정보를 찾을 수 없습니다."

    def build_function_context(self, func_data: Dict) -> str:
        """함수 컨텍스트 빌드"""
        if func_data.get('error'):
            return f"오류: {func_data['error']}"

        sections = []

        # 함수 정보
        func = func_data.get('function', {})
        if func:
            section = f"""## 함수: {func.get('name')}
- 전체 경로: `{func.get('qname')}`
- 모듈: `{func.get('module')}`
- 라인: {func.get('lineno')}
- 인자: {func.get('args', [])}"""
            if func.get('doc'):
                section += f"\n- 설명: {func.get('doc')[:300]}"
            if func.get('class_name'):
                section += f"\n- 소속 클래스: `{func.get('class_name')}`"
            sections.append(section)

        # 호출 관계
        calls = func_data.get('calls', [])
        called_by = func_data.get('called_by', [])
        if calls or called_by:
            rel_section = "## 호출 관계"
            if calls:
                rel_section += f"\n### 호출하는 함수 ({len(calls)}개)"
                for c in calls[:5]:
                    rel_section += f"\n- `{c.get('name')}`"
            if called_by:
                rel_section += f"\n### 호출되는 곳 ({len(called_by)}개)"
                for c in called_by[:5]:
                    rel_section += f"\n- `{c.get('name')}`"
            sections.append(rel_section)

        # 클래스 정보
        class_info = func_data.get('class_info')
        if class_info:
            class_section = f"""## 소속 클래스: {class_info.get('name')}
- 상속: {class_info.get('bases', [])}"""
            if class_info.get('doc'):
                class_section += f"\n- 설명: {class_info.get('doc')[:200]}"
            sections.append(class_section)

        # 관련 패턴
        patterns = func_data.get('related_patterns', [])
        if patterns:
            pattern_section = "## 관련 패턴"
            for p in patterns:
                pattern_section += f"\n### {p.get('type')}: {p.get('name')}"
                if p.get('intent'):
                    pattern_section += f"\n- 의도: {p.get('intent')[:150]}"
                if p.get('metric'):
                    pattern_section += f"\n- 효과: {p.get('metric')}"
            sections.append(pattern_section)

        return "\n\n".join(sections)

    def build_module_context(self, module_data: Dict) -> str:
        """모듈 컨텍스트 빌드"""
        if module_data.get('error'):
            return f"오류: {module_data['error']}"

        sections = []

        # 모듈 정보
        module = module_data.get('module', {})
        if module:
            sections.append(f"""## 모듈: {module.get('name')}
- 경로: `{module.get('path')}`
- 클래스: {module.get('classes')}개
- 함수: {module.get('functions')}개""")

        # 클래스 목록
        classes = module_data.get('classes', [])
        if classes:
            class_section = "## 클래스"
            for c in classes:
                class_section += f"\n### {c.get('name')}"
                if c.get('doc'):
                    class_section += f"\n{c.get('doc')[:100]}"
            sections.append(class_section)

        # 함수 목록
        functions = module_data.get('functions', [])
        if functions:
            func_section = "## 함수"
            for f in functions[:10]:
                func_section += f"\n- `{f.get('name')}`"
                if f.get('doc'):
                    func_section += f": {f.get('doc')[:50]}"
            if len(functions) > 10:
                func_section += f"\n... 외 {len(functions) - 10}개"
            sections.append(func_section)

        # 의존성
        imports = module_data.get('imports', [])
        if imports:
            import_section = "## 의존성"
            for imp in imports:
                import_section += f"\n- `{imp.get('name')}`"
            sections.append(import_section)

        return "\n\n".join(sections)

    def _build_code_section(self, items: List[Dict]) -> str:
        """코드 섹션 생성"""
        lines = ["## 관련 코드"]
        for item in items[:10]:
            item_type = item.get('type', 'Unknown')
            name = item.get('name', 'unknown')
            lines.append(f"\n### {item_type}: `{name}`")

            if item.get('qname'):
                lines.append(f"- 경로: `{item.get('qname')}`")
            if item.get('module'):
                lines.append(f"- 모듈: `{item.get('module')}`")
            if item.get('doc'):
                doc = item.get('doc')[:200]
                lines.append(f"- 설명: {doc}")
            if item.get('args'):
                lines.append(f"- 인자: {item.get('args')}")
            if item.get('lineno'):
                lines.append(f"- 라인: {item.get('lineno')}")

        return "\n".join(lines)

    def _build_pattern_section(self, items: List[Dict]) -> str:
        """패턴 섹션 생성"""
        lines = ["## 관련 패턴/지식"]
        for item in items[:8]:
            item_type = item.get('type', 'Pattern')
            name = item.get('name', 'unknown')
            lines.append(f"\n### {item_type}: {name}")

            if item.get('category'):
                lines.append(f"- 카테고리: {item.get('category')}")
            if item.get('description'):
                lines.append(f"- 설명: {item.get('description')[:200]}")
            if item.get('intent'):
                lines.append(f"- 의도: {item.get('intent')[:200]}")
            if item.get('metric'):
                lines.append(f"- 효과: {item.get('metric')}")

        return "\n".join(lines)

    def _build_security_section(self, items: List[Dict]) -> str:
        """보안 섹션 생성"""
        lines = ["## ⚠️ 보안 주의사항"]
        for item in items[:5]:
            if item.get('cwe_id'):
                lines.append(f"\n### {item.get('cwe_id')}: {item.get('name')}")
                if item.get('severity'):
                    lines.append(f"- 심각도: **{item.get('severity')}**")
                if item.get('rate'):
                    lines.append(f"- AI 생성 코드 발생률: {item.get('rate')}")
                if item.get('remediation'):
                    lines.append(f"- 해결책: {item.get('remediation')}")
        return "\n".join(lines)


class SimpleReranker:
    """간단한 키워드 기반 리랭커 (외부 모델 없이)"""

    def __init__(self, bm25_weight: float = 0.5):
        self.bm25_weight = bm25_weight

    def rerank(self, query: str, candidates: List[Dict], top_k: int = 10) -> List[Dict]:
        """키워드 기반 리랭킹"""
        if not candidates:
            return []

        query_terms = set(query.lower().split())

        scored = []
        for cand in candidates:
            score = self._compute_score(query_terms, cand)
            scored.append((cand, score))

        scored.sort(key=lambda x: x[1], reverse=True)
        return [item[0] for item in scored[:top_k]]

    def _compute_score(self, query_terms: set, candidate: Dict) -> float:
        """점수 계산"""
        score = 0.0

        # 이름 매칭
        name = (candidate.get('name') or '').lower()
        name_terms = set(name.split('_'))  # snake_case 분리
        name_match = len(query_terms & name_terms) / max(len(query_terms), 1)
        score += name_match * 3.0  # 이름 매칭 가중치

        # 설명/문서 매칭
        doc = (candidate.get('doc') or candidate.get('description') or '').lower()
        doc_terms = set(doc.split())
        doc_match = len(query_terms & doc_terms) / max(len(query_terms), 1)
        score += doc_match * 1.0

        # 타입별 부스팅
        cand_type = candidate.get('type', '')
        if cand_type == 'Function':
            score *= 1.2
        elif cand_type in ['DesignPattern', 'SecurityPattern']:
            score *= 1.1
        elif cand_type == 'V3SecurityVulnerability':
            score *= 1.3  # 보안 우선

        return score
