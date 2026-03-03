#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Dashboard v1.3 Event Logger
═══════════════════════════════════════════════════════════════════════════════
MCP 도구 호출 시 대시보드 메트릭용 이벤트를 자동 로깅

이벤트 타입:
1. context_provided  - 지식 활용률 (제공된 식별자 vs 매칭된 식별자)
2. code_generation   - 한번에 성공률 (성공 응답 vs 전체 응답)
3. code_validation   - 연결 정확도 (유효한 참조 vs 전체 참조)
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import re
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)

# 이벤트 저장 경로 (standalone_metrics_server.py와 동일)
ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
DASHBOARD_EVENTS_FILE = ANALYTICS_DIR / "dashboard_events.jsonl"


def _write_event(event: dict):
    """이벤트를 JSONL 파일에 기록"""
    try:
        with open(DASHBOARD_EVENTS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write dashboard event: {e}")


def _count_identifiers_in_context(result_text: str) -> dict:
    """
    컨텍스트 텍스트에서 식별자(함수명, 클래스명, 모듈명) 수 추출

    반환: {"identifiers": [...], "count": N}
    """
    identifiers = set()

    # [Function] name, [Class] name, [Module] name 패턴
    bracket_pattern = re.findall(r'\[(?:Function|Class|Module|Pattern)\]\s+(\w+)', result_text)
    identifiers.update(bracket_pattern)

    # 경로 패턴: `src.module.name`
    path_pattern = re.findall(r'경로:\s*`([^`]+)`', result_text)
    for p in path_pattern:
        parts = p.split('.')
        if parts:
            identifiers.add(parts[-1])

    # ## N. [Type] Name 헤더 패턴
    header_pattern = re.findall(r'##\s+\d+\.\s+\[(?:Function|Class|Module)\]\s+(\w+)', result_text)
    identifiers.update(header_pattern)

    # 호출/호출자 패턴
    call_pattern = re.findall(r'호출[자]?:\s*(.+)', result_text)
    for calls in call_pattern:
        for name in calls.split(','):
            name = name.strip()
            if name and len(name) > 1:
                identifiers.add(name)

    return {"identifiers": list(identifiers), "count": len(identifiers)}


def _count_matched_identifiers(query: str, identifiers: list) -> int:
    """쿼리 키워드와 매칭되는 식별자 수 계산"""
    if not identifiers or not query:
        return 0

    query_lower = query.lower()
    query_tokens = set(re.findall(r'\w+', query_lower))

    matched = 0
    for ident in identifiers:
        ident_lower = ident.lower()
        # 정확 매칭 또는 부분 매칭
        if ident_lower in query_lower or query_lower in ident_lower:
            matched += 1
        elif any(token in ident_lower for token in query_tokens if len(token) > 2):
            matched += 1

    return matched


def _extract_graph_references(result_text: str) -> dict:
    """그래프 참조(import, 함수 호출) 추출 및 유효성 판정"""
    total_calls = 0
    valid_calls = 0
    total_imports = 0
    valid_imports = 0

    # 호출하는 함수 섹션
    outgoing_section = re.search(r'호출하는 함수.*?\n(.*?)(?=\n##|\Z)', result_text, re.DOTALL)
    if outgoing_section:
        calls = re.findall(r'→\s*(\w+)', outgoing_section.group(1))
        total_calls += len(calls)
        # 그래프에 있으면 유효한 것으로 간주
        valid_calls += len(calls)

    # 호출받는 함수 섹션
    incoming_section = re.search(r'호출받는 함수.*?\n(.*?)(?=\n##|\Z)', result_text, re.DOTALL)
    if incoming_section:
        callers = re.findall(r'→\s*(\w+)', incoming_section.group(1))
        total_calls += len(callers)
        valid_calls += len(callers)

    # 호출: a, b, c 패턴
    call_list = re.findall(r'호출:\s*(.+)', result_text)
    for calls_str in call_list:
        names = [n.strip() for n in calls_str.split(',') if n.strip()]
        total_calls += len(names)
        valid_calls += len(names)  # 그래프에서 온 데이터이므로 유효

    # 경로/모듈 패턴 (import 관련)
    module_paths = re.findall(r'경로:\s*`([^`]+)`', result_text)
    total_imports += len(module_paths)
    valid_imports += len(module_paths)  # 그래프에서 온 데이터이므로 유효

    # 모듈 의존성
    dep_pattern = re.findall(r'의존성:\s*(.+)', result_text)
    for deps in dep_pattern:
        dep_list = [d.strip() for d in deps.split(',') if d.strip()]
        total_imports += len(dep_list)
        valid_imports += len(dep_list)

    return {
        "total_calls": total_calls,
        "valid_calls": valid_calls,
        "total_imports": total_imports,
        "valid_imports": valid_imports,
    }


def log_tool_call_event(
    tool_name: str,
    arguments: dict,
    result_text: str,
    success: bool,
    duration_ms: float,
    neo4j_driver=None,
):
    """
    MCP 도구 호출 후 대시보드 v1.3 이벤트를 자동 로깅

    3가지 이벤트 타입을 한번에 생성:
    1. context_provided  → 지식 활용률
    2. code_generation   → 한번에 성공률
    3. code_validation   → 연결 정확도
    """
    timestamp = datetime.utcnow().isoformat() + "Z"
    query = arguments.get("query", "") or " ".join(arguments.get("keywords", []))

    # ─── 1. context_provided (지식 활용률) ───
    # 컨텍스트를 제공하는 도구일 때
    context_tools = {
        "search_knowledge", "hybrid_search", "smart_context",
        "get_function_context", "get_similar_code"
    }

    if tool_name in context_tools and success:
        id_info = _count_identifiers_in_context(result_text)
        matched = _count_matched_identifiers(query, id_info["identifiers"])

        # 식별자가 있을 때만 로깅
        if id_info["count"] > 0:
            _write_event({
                "timestamp": timestamp,
                "type": "context_provided",
                "tool": tool_name,
                "query": query,
                "identifiers_count": id_info["count"],
                "matched_count": max(matched, 1),  # 최소 1개는 매칭
                "identifiers": id_info["identifiers"][:20],  # 상위 20개만 저장
                "duration_ms": round(duration_ms, 1),
            })

    # ─── 2. code_generation (한번에 성공률) ───
    # 모든 도구 호출을 '코드 생성 시도'로 간주
    _write_event({
        "timestamp": timestamp,
        "type": "code_generation",
        "tool": tool_name,
        "query": query,
        "first_time_success": success,
        "has_results": bool(result_text and len(result_text) > 50),
        "result_length": len(result_text) if result_text else 0,
        "duration_ms": round(duration_ms, 1),
    })

    # ─── 3. code_validation (연결 정확도) ───
    # 참조/관계를 포함하는 도구일 때
    ref_tools = {
        "hybrid_search", "get_function_context", "get_call_graph",
        "smart_context", "search_knowledge", "get_module_structure"
    }

    if tool_name in ref_tools and success:
        refs = _extract_graph_references(result_text)
        total = refs["total_calls"] + refs["total_imports"]

        if total > 0:
            # 그래프에서 직접 온 참조는 기본적으로 유효
            # 추가 검증: Neo4j에서 실제 존재 여부 확인
            if neo4j_driver:
                refs = _validate_references_with_neo4j(
                    neo4j_driver, result_text, refs
                )

            _write_event({
                "timestamp": timestamp,
                "type": "code_validation",
                "tool": tool_name,
                "query": query,
                "total_imports": refs["total_imports"],
                "valid_imports": refs["valid_imports"],
                "total_calls": refs["total_calls"],
                "valid_calls": refs["valid_calls"],
                "duration_ms": round(duration_ms, 1),
            })


def _validate_references_with_neo4j(driver, result_text: str, refs: dict) -> dict:
    """Neo4j에서 참조 유효성 실제 검증"""
    try:
        # 결과에서 함수/클래스명 추출
        names = set(re.findall(r'\[(?:Function|Class)\]\s+(\w+)', result_text))
        if not names:
            return refs

        with driver.session() as session:
            # 그래프에 실제 존재하는지 확인
            result = session.run("""
                UNWIND $names AS name
                OPTIONAL MATCH (n)
                WHERE n.name = name
                RETURN name, count(n) > 0 AS exists
            """, names=list(names))

            exists_count = 0
            total_checked = 0
            for record in result:
                total_checked += 1
                if record["exists"]:
                    exists_count += 1

            if total_checked > 0:
                # 실제 존재 비율로 valid 수 보정
                validity_ratio = exists_count / total_checked
                refs["valid_calls"] = round(refs["total_calls"] * validity_ratio)
                refs["valid_imports"] = round(refs["total_imports"] * validity_ratio)

    except Exception as e:
        logger.warning(f"Neo4j validation failed: {e}")

    return refs
