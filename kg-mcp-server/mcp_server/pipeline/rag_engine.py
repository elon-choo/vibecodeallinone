"""
RAG Answer Engine (Phase 7.1)
=============================
코드베이스에 대한 자연어 질문에 답변을 생성하는 End-to-End RAG 파이프라인.
검색(Retrieval) + 답변생성(Generation) + 인용(Citation).

MCP 도구: ask_codebase(question, max_context_tokens)
"""

import hashlib
import json
import logging
import os
import re
import time
from typing import Dict, List, Optional, Any

import google.generativeai as genai
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

# ~/.claude/power-pack.env에서 API 키 로드 (fallback: ~/.env)
_env_file = os.path.expanduser("~/.claude/power-pack.env")
if not os.path.exists(_env_file):
    _env_file = os.path.expanduser("~/.env")
load_dotenv(_env_file)
genai.configure(api_key=os.environ.get("GEMINI_API_KEY"))

# 답변 캐시 (동일 질문 5분 TTL)
_answer_cache: Dict[str, Any] = {}
_CACHE_TTL = 300  # 5분
_MAX_CACHE = 50


RAG_SYSTEM_PROMPT = """You are a code intelligence assistant. Answer the question based ONLY on the provided codebase context.

Rules:
1. Only use information from the context below
2. When referencing specific functions/classes, use [Function:name] or [Class:name] format
3. If the context doesn't contain enough info, say so explicitly
4. Be concise but thorough
5. Use Korean for the answer when the question is in Korean, otherwise use English
6. Structure your answer with clear sections if the topic is complex

Context:
{context}

Question: {question}

Answer:"""


class RAGEngine:
    """코드베이스 자연어 질의응답 엔진.

    검색(HybridSearch + VectorSearch) -> 컨텍스트 구성 -> Gemini Flash 답변 생성 -> Citation 추출.
    """

    def __init__(self, driver):
        """
        Args:
            driver: Neo4j driver 인스턴스
        """
        self.driver = driver
        self.model = genai.GenerativeModel("gemini-3-flash-preview")

        # Lazy init으로 순환 임포트 방지
        self._hybrid_search = None
        self._vector_search = None
        self._query_router = None

    @property
    def hybrid_search(self):
        if self._hybrid_search is None:
            from mcp_server.pipeline.hybrid_search import HybridSearchEngine
            self._hybrid_search = HybridSearchEngine(self.driver)
        return self._hybrid_search

    @property
    def vector_search(self):
        if self._vector_search is None:
            from mcp_server.pipeline.vector_search import VectorSearchEngine
            self._vector_search = VectorSearchEngine(self.driver)
        return self._vector_search

    @property
    def query_router(self):
        if self._query_router is None:
            from mcp_server.pipeline.query_router import QueryRouter
            self._query_router = QueryRouter()
        return self._query_router

    def ask(self, question: str, max_context_tokens: int = 6000) -> Dict:
        """메인 RAG 파이프라인.

        1. QueryRouter로 의도 분류
        2. HybridSearchEngine.search() 실행 (keyword+vector RRF)
        3. VectorSearchEngine.semantic_search() 병렬 실행
        4. 두 결과 병합 + 중복 제거
        5. 컨텍스트 구성 (max_context_tokens 제한)
        6. Gemini Flash에 질문 + 컨텍스트 -> 답변 생성
        7. 답변에 citation 삽입

        Args:
            question: 코드베이스에 대한 자연어 질문
            max_context_tokens: 컨텍스트 최대 토큰 수 (기본 6000)

        Returns:
            RAG 결과 딕셔너리
        """
        if not question or not question.strip():
            return {"success": False, "error": "Question is empty."}

        # 캐시 확인
        cache_key = self._cache_key(question, max_context_tokens)
        cached = self._get_cached(cache_key)
        if cached:
            cached["from_cache"] = True
            return cached

        try:
            # 1. 의도 분류 및 검색 전략 결정
            strategy = self.query_router.get_search_strategy(question)
            logger.info(
                f"RAG query intent: {strategy['intent']}, "
                f"confidence: {strategy['confidence']:.2f}"
            )

            # 2. 하이브리드 검색 (keyword + vector RRF)
            hybrid_results = self.hybrid_search.search(
                question, strategy, limit=15
            )

            # 3. 벡터 시맨틱 검색
            vector_result = self.vector_search.semantic_search(
                question, limit=10, threshold=0.5
            )
            vector_items = (
                vector_result.get("results", [])
                if vector_result.get("success")
                else []
            )

            # 4. 결과 병합 + 중복 제거
            merged = self._merge_and_deduplicate(hybrid_results, vector_items)

            if not merged:
                return {
                    "success": True,
                    "question": question,
                    "answer": "검색 결과가 없습니다. 질문을 다른 키워드로 시도해 주세요.",
                    "citations": [],
                    "sources_count": 0,
                    "context_tokens": 0,
                }

            # 5. 컨텍스트 구성
            context = self._build_context(merged, max_context_tokens)
            context_tokens = self._estimate_tokens(context)

            # 6. Gemini Flash로 답변 생성
            answer_data = self._generate_answer(question, context)

            if not answer_data.get("success"):
                return {
                    "success": False,
                    "error": answer_data.get("error", "Answer generation failed."),
                }

            answer_text = answer_data["answer"]

            # 7. Citation 추출
            citations = self._extract_citations(answer_text, merged)

            result = {
                "success": True,
                "question": question,
                "answer": answer_text,
                "citations": citations,
                "sources_count": len(merged),
                "context_tokens": context_tokens,
                "search_strategy": strategy["intent"],
            }

            # 캐시 저장
            self._set_cache(cache_key, result)

            return result

        except Exception as e:
            logger.error(f"RAG pipeline failed: {e}", exc_info=True)
            return {"success": False, "error": str(e)}

    def _merge_and_deduplicate(
        self,
        hybrid_results: List[Dict],
        vector_results: List[Dict],
    ) -> List[Dict]:
        """두 검색 결과를 병합하고 중복을 제거한다.

        동일 name이 양쪽에 있으면 hybrid 결과를 우선하되 vector 유사도를 병합한다.

        Args:
            hybrid_results: 하이브리드 검색 결과
            vector_results: 벡터 검색 결과

        Returns:
            중복 제거된 병합 결과
        """
        seen: Dict[str, Dict] = {}

        for item in hybrid_results:
            name = item.get("name")
            if name and name not in seen:
                seen[name] = item

        for item in vector_results:
            name = item.get("name")
            if not name:
                continue
            if name in seen:
                # 벡터 유사도 정보 병합
                if item.get("similarity"):
                    seen[name]["similarity"] = item["similarity"]
            else:
                seen[name] = item

        return list(seen.values())

    def _build_context(self, results: List[Dict], max_tokens: int) -> str:
        """검색 결과를 구조화된 컨텍스트 문자열로 변환.

        각 노드를 "[Node:name] ..." 형태로 포맷팅하고,
        max_tokens를 초과하지 않도록 잘라낸다.

        Args:
            results: 검색 결과 리스트
            max_tokens: 최대 토큰 수

        Returns:
            구조화된 컨텍스트 문자열
        """
        context_parts: List[str] = []
        current_tokens = 0

        for item in results:
            node_type = item.get("type", "Unknown")
            name = item.get("name", "N/A")

            lines = [f"[{node_type}:{name}]"]

            # 경로 정보
            qname = item.get("qname") or item.get("qualified_name")
            if qname:
                lines.append(f"  Path: {qname}")

            # 모듈 정보
            module = item.get("module")
            if module:
                lines.append(f"  Module: {module}")

            # 파일 경로
            file_path = item.get("file_path") or item.get("path")
            if file_path:
                lines.append(f"  File: {file_path}")

            # docstring / 설명
            doc = item.get("doc") or item.get("docstring") or item.get("description")
            if doc:
                # 긴 docstring은 300자로 제한
                doc_text = str(doc)[:300]
                lines.append(f"  Description: {doc_text}")

            # 시그니처 / 인자
            args = item.get("args")
            if args:
                lines.append(f"  Arguments: {args}")

            # 호출 관계
            calls = item.get("calls")
            if calls and isinstance(calls, list) and calls:
                lines.append(f"  Calls: {', '.join(str(c) for c in calls)}")

            called_by = item.get("called_by")
            if called_by and isinstance(called_by, list) and called_by:
                lines.append(f"  Called by: {', '.join(str(c) for c in called_by)}")

            # 자식 요소 (클래스의 메서드 등)
            children = item.get("children")
            if children and isinstance(children, list) and children:
                lines.append(f"  Contains: {', '.join(str(c) for c in children)}")

            # 클래스 / 함수 목록 (Module 노드)
            classes = item.get("classes")
            if classes and isinstance(classes, list) and classes:
                lines.append(f"  Classes: {', '.join(str(c) for c in classes)}")

            functions = item.get("functions")
            if functions and isinstance(functions, list) and functions:
                lines.append(f"  Functions: {', '.join(str(c) for c in functions)}")

            # 유사도 점수
            similarity = item.get("similarity")
            if similarity:
                lines.append(f"  Similarity: {similarity:.3f}")

            # RRF 점수
            rrf = item.get("rrf_score")
            if rrf:
                lines.append(f"  RRF Score: {rrf}")

            node_text = "\n".join(lines) + "\n"
            node_tokens = self._estimate_tokens(node_text)

            # 토큰 제한 체크
            if current_tokens + node_tokens > max_tokens:
                # 남은 공간이 있으면 잘라서 넣기
                remaining = max_tokens - current_tokens
                if remaining > 50:
                    # 대략적으로 잘라넣기
                    truncated = node_text[: remaining * 4]  # 1 token ~= 4 chars
                    context_parts.append(truncated + "\n  [... truncated]")
                break

            context_parts.append(node_text)
            current_tokens += node_tokens

        return "\n".join(context_parts)

    def _generate_answer(self, question: str, context: str) -> Dict:
        """Gemini Flash로 답변을 생성한다.

        Args:
            question: 사용자 질문
            context: 구조화된 컨텍스트

        Returns:
            {"success": True, "answer": "..."} 또는 {"success": False, "error": "..."}
        """
        prompt = RAG_SYSTEM_PROMPT.format(context=context, question=question)

        try:
            response = self.model.generate_content(prompt)
            answer_text = response.text

            if not answer_text or not answer_text.strip():
                return {"success": False, "error": "Gemini returned empty response."}

            return {"success": True, "answer": answer_text.strip()}

        except Exception as e:
            logger.error(f"Gemini API call failed: {e}")
            return {"success": False, "error": f"Gemini API error: {e}"}

    def _extract_citations(
        self, answer: str, nodes: List[Dict]
    ) -> List[Dict[str, str]]:
        """답변에서 [Function:name] 또는 [Class:name] 형식의 인용을 추출한다.

        추가로, 답변에 노드 이름이 직접 언급된 경우도 citation에 포함한다.

        Args:
            answer: 생성된 답변 텍스트
            nodes: 검색 결과 노드 리스트

        Returns:
            citation 리스트: [{"name": ..., "type": ..., "module": ...}, ...]
        """
        citations: List[Dict[str, str]] = []
        cited_names: set = set()

        # 1. [Type:Name] 형식의 명시적 인용 추출
        explicit_pattern = re.compile(r"\[(Function|Class|Module|Method):([^\]]+)\]")
        for match in explicit_pattern.finditer(answer):
            node_type = match.group(1)
            node_name = match.group(2).strip()
            if node_name not in cited_names:
                cited_names.add(node_name)
                # 노드 리스트에서 모듈 정보 찾기
                module = self._find_module_for_name(node_name, nodes)
                citations.append({
                    "name": node_name,
                    "type": node_type,
                    "module": module,
                })

        # 2. 답변에 직접 언급된 노드 이름 (backtick 안에 있는 경우)
        backtick_pattern = re.compile(r"`([^`]+)`")
        backtick_names = set(backtick_pattern.findall(answer))

        for node in nodes:
            name = node.get("name", "")
            if not name or name in cited_names:
                continue

            # backtick으로 언급된 이름이거나 답변 본문에 직접 언급된 경우
            if name in backtick_names or (
                len(name) > 3 and name in answer
            ):
                cited_names.add(name)
                citations.append({
                    "name": name,
                    "type": node.get("type", "Unknown"),
                    "module": node.get("module", "N/A"),
                })

        return citations

    def _find_module_for_name(
        self, name: str, nodes: List[Dict]
    ) -> str:
        """노드 리스트에서 이름에 해당하는 모듈을 찾는다."""
        for node in nodes:
            if node.get("name") == name:
                return node.get("module", "N/A")
        return "N/A"

    def _estimate_tokens(self, text: str) -> int:
        """텍스트의 대략적인 토큰 수를 추정한다.

        영어 기준 ~4 chars/token, 한국어 기준 ~2 chars/token.
        혼합 텍스트를 고려하여 ~3 chars/token으로 추정.
        """
        if not text:
            return 0
        return max(1, len(text) // 3)

    # ── 캐시 관련 ──────────────────────────────────────────────

    def _cache_key(self, question: str, max_tokens: int) -> str:
        raw = f"{question.strip().lower()}:{max_tokens}"
        return hashlib.md5(raw.encode()).hexdigest()

    def _get_cached(self, key: str) -> Optional[Dict]:
        cached = _answer_cache.get(key)
        if cached and (time.time() - cached["ts"]) < _CACHE_TTL:
            return cached["data"]
        return None

    def _set_cache(self, key: str, data: Dict):
        _answer_cache[key] = {"ts": time.time(), "data": data}
        # 캐시 크기 제한
        if len(_answer_cache) > _MAX_CACHE:
            oldest = sorted(_answer_cache, key=lambda k: _answer_cache[k]["ts"])
            for k in oldest[: _MAX_CACHE // 2]:
                del _answer_cache[k]
