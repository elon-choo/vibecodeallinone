"""Query Router - 질문 의도 분류기

연구 기반:
- REFINE_INSTRUCTION_v2: Dual Search Router 구현
- LightRAG: Local/Global 이원화 검색

Phase 6.3 업그레이드:
- 자연어 문장 감지 → vector_weight 자동 상향
- 짧은 키워드 → keyword 우선, 자연어 문장 → vector 우선
"""

import re
from enum import Enum
from typing import Tuple
import logging

logger = logging.getLogger(__name__)


class QueryIntent(str, Enum):
    """질문 의도 유형"""
    LOCAL = "local"    # 특정 코드 요소에 대한 구체적 질문
    GLOBAL = "global"  # 전체 구조/아키텍처에 대한 질문
    HYBRID = "hybrid"  # 불확실하거나 복합적인 질문


class QueryRouter:
    """질문 의도 분류기 - 규칙 기반 (LLM 폴백 없음, 비용 절감)"""

    # Local 검색을 선호하는 패턴
    LOCAL_PATTERNS = [
        # 특정 코드 요소 지칭
        r"\b(함수|function|func|메서드|method)\b",
        r"\b(클래스|class|클레스)\b",
        r"\b(변수|variable|var|속성|property|attr)\b",
        r"\b(파라미터|parameter|param|인자|argument|arg)\b",
        # 구체적 질문
        r"\b(뭘|무엇을|어떻게|what|how)\s*(하는|does|do)\b",
        r"\b(코드|code|소스|source)\b.*\b(보여|show|알려|tell)\b",
        r"\b(구현|implement|implementation)\b",
        r"\b(호출|call|calls|calling)\b",
        # 특정 이름 언급 패턴 (snake_case, camelCase)
        r"\b[a-z]+_[a-z]+\b",  # snake_case
        r"\b[a-z]+[A-Z][a-z]+\b",  # camelCase
    ]

    # Global 검색을 선호하는 패턴
    GLOBAL_PATTERNS = [
        # 전체 구조 관련
        r"\b(구조|structure|아키텍처|architecture|설계|design)\b",
        r"\b(전체|overall|전반|all|모든|every)\b",
        r"\b(개요|overview|요약|summary|설명|explain)\b",
        r"\b(흐름|flow|플로우|프로세스|process)\b",
        r"\b(의존성|dependency|dependencies|종속성)\b",
        # 목록/나열 요청
        r"\b(목록|list|리스트|나열|enumerate)\b",
        r"\b(어떤.*있|what.*exist|있는.*뭐)\b",
        r"\b(몇\s*개|how\s*many|개수|count)\b",
        # 패턴/아키텍처 관련
        r"\b(패턴|pattern|디자인패턴|design pattern)\b",
        r"\b(레이어|layer|계층|tier)\b",
        r"\b(모듈|module|컴포넌트|component)\b",
    ]

    # 보안 관련 패턴 (Global 선호)
    SECURITY_PATTERNS = [
        r"\b(보안|security|취약점|vulnerability|vuln)\b",
        r"\b(인젝션|injection|XSS|CSRF|SQL)\b",
        r"\b(인증|authentication|auth|권한|authorization)\b",
        r"\b(OWASP|CWE)\b",
    ]

    def __init__(self, confidence_threshold: float = 0.6):
        """
        Args:
            confidence_threshold: 분류 확신도 임계값 (이하면 HYBRID)
        """
        self.confidence_threshold = confidence_threshold
        self._compile_patterns()

    def _compile_patterns(self):
        """정규식 패턴 미리 컴파일"""
        self.local_compiled = [re.compile(p, re.IGNORECASE) for p in self.LOCAL_PATTERNS]
        self.global_compiled = [re.compile(p, re.IGNORECASE) for p in self.GLOBAL_PATTERNS]
        self.security_compiled = [re.compile(p, re.IGNORECASE) for p in self.SECURITY_PATTERNS]

    def classify(self, query: str) -> Tuple[QueryIntent, float]:
        """
        질문 의도 분류

        Args:
            query: 사용자 질문

        Returns:
            Tuple[QueryIntent, float]: (의도, 확신도)
        """
        if not query or not query.strip():
            return QueryIntent.HYBRID, 0.0

        # 각 패턴 매칭 점수 계산
        local_score = self._calculate_score(query, self.local_compiled)
        global_score = self._calculate_score(query, self.global_compiled)
        security_score = self._calculate_score(query, self.security_compiled)

        # 보안 관련은 Global에 가산
        global_score += security_score * 0.5

        total = local_score + global_score
        if total == 0:
            return QueryIntent.HYBRID, 0.5

        # 정규화된 점수 계산
        local_ratio = local_score / total
        global_ratio = global_score / total

        # 확신도 계산 (차이가 클수록 확신)
        confidence = abs(local_ratio - global_ratio)

        # 확신도가 낮으면 HYBRID
        if confidence < self.confidence_threshold:
            return QueryIntent.HYBRID, 0.5 + confidence / 2

        # 더 높은 쪽으로 분류
        if local_ratio > global_ratio:
            return QueryIntent.LOCAL, 0.5 + confidence / 2
        else:
            return QueryIntent.GLOBAL, 0.5 + confidence / 2

    def _calculate_score(self, query: str, patterns: list) -> float:
        """패턴 매칭 점수 계산"""
        score = 0.0
        for pattern in patterns:
            matches = pattern.findall(query)
            score += len(matches)
        return score

    def is_natural_language(self, query: str) -> bool:
        """Phase 6.3: 쿼리가 자연어 문장인지 판별.

        자연어 문장 → vector 검색 우선, 짧은 키워드 → keyword 검색 우선.

        판별 기준:
        - 3단어 이상이면 자연어로 간주
        - 한국어/영어 문장 패턴 매칭
        """
        words = query.split()
        # 3단어 이상이면 자연어로 간주
        if len(words) >= 3:
            return True

        # 한국어/영어 문장 패턴
        sentence_patterns = [
            r'[가-힣]+\s[가-힣]+\s[가-힣]+',  # 한국어 3단어 이상
            r'\b(how|what|where|when|why|which|find|search|show|get)\b',
            r'(해|하는|되는|인|같은|비슷한|찾|검색)',
        ]
        for pattern in sentence_patterns:
            if re.search(pattern, query, re.IGNORECASE):
                return True
        return False

    def get_search_strategy(self, query: str) -> dict:
        """
        검색 전략 반환

        Args:
            query: 사용자 질문

        Returns:
            dict: 검색 전략 설정
        """
        intent, confidence = self.classify(query)

        strategies = {
            QueryIntent.LOCAL: {
                "intent": "local",
                "confidence": confidence,
                "vector_weight": 0.6,  # 벡터 검색 가중치 높음
                "keyword_weight": 0.3,
                "graph_weight": 0.1,
                "graph_hops": 2,  # 좁은 범위
                "result_limit": 5,
            },
            QueryIntent.GLOBAL: {
                "intent": "global",
                "confidence": confidence,
                "vector_weight": 0.2,
                "keyword_weight": 0.3,
                "graph_weight": 0.5,  # 그래프 탐색 가중치 높음
                "graph_hops": 4,  # 넓은 범위
                "result_limit": 15,
            },
            QueryIntent.HYBRID: {
                "intent": "hybrid",
                "confidence": confidence,
                "vector_weight": 0.4,
                "keyword_weight": 0.3,
                "graph_weight": 0.3,
                "graph_hops": 3,
                "result_limit": 10,
            },
        }

        strategy = strategies[intent]

        # Phase 10.5+: 자연어 문장이면 vector_weight 상향 (0.4 → 0.6)
        # 0.7은 너무 높아 keyword 정확 매칭을 밀어냄 → 0.6으로 조정
        if self.is_natural_language(query):
            strategy["vector_weight"] = max(strategy.get("vector_weight", 0.4), 0.6)
            logger.info(
                f"Natural language detected, vector_weight raised to {strategy['vector_weight']}"
            )

        logger.info(f"Query intent: {intent.value}, confidence: {confidence:.2f}")
        return strategy


# 편의 함수
def classify_query(query: str) -> Tuple[QueryIntent, float]:
    """질문 의도 분류 (편의 함수)"""
    router = QueryRouter()
    return router.classify(query)
