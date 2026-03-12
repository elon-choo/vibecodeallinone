"""Core search and hybrid search handlers."""

from mcp_server.pipeline.cache import query_cache, context_cache
from mcp_server.observability.analytics import (
    track_node_references_batch,
    update_neo4j_access_count,
)
from ._util import _run_sync


async def search_knowledge(reg, args: dict) -> str:
    query = args.get("query", "")
    search_type = args.get("type", "all")
    limit = args.get("limit", 10)

    if search_type == "code":
        results = await _run_sync(reg.searcher.search_code, query, limit * 2)
    elif search_type == "pattern":
        results = await _run_sync(reg.searcher.search_patterns, query, limit * 2)
    else:
        results = await _run_sync(reg.searcher.search_all, query, limit * 2)

    reranked = reg.reranker.rerank(query, results, limit)
    track_node_references_batch(reranked, "search_knowledge", query)
    context = reg.builder.build(reranked, query)
    return context


async def get_function_context(reg, args: dict) -> str:
    func_name = args.get("function_name", "")
    func_data = await _run_sync(reg.searcher.get_function_context, func_name)

    if func_data:
        track_node_references_batch(
            [{"name": func_name, "type": "Function", **func_data}],
            "get_function_context",
            func_name
        )

    return reg.builder.build_function_context(func_data)


async def get_module_structure(reg, args: dict) -> str:
    module_name = args.get("module_name", "")
    module_data = await _run_sync(reg.searcher.get_module_structure, module_name)
    return reg.builder.build_module_context(module_data)


async def get_security_patterns(reg, _args: dict) -> str:
    security_data = await _run_sync(reg.searcher.get_security_recommendations)
    return reg.builder._build_security_section(security_data)


async def get_graph_stats(reg, _args: dict) -> str:
    stats = await _run_sync(reg.searcher.get_graph_stats)

    lines = ["# 지식그래프 통계\n"]

    lines.append("## 노드")
    for label, count in stats.get('nodes', {}).items():
        lines.append(f"- {label}: {count}개")
    lines.append(f"- **총계: {stats.get('total_nodes', 0)}개**")

    lines.append("\n## 관계")
    for rel_type, count in stats.get('relations', {}).items():
        lines.append(f"- {rel_type}: {count}개")
    lines.append(f"- **총계: {stats.get('total_relations', 0)}개**")

    return "\n".join(lines)


async def smart_context(reg, args: dict) -> str:
    keywords = args.get("keywords", [])
    max_tokens = args.get("max_tokens", 4000)

    if not keywords:
        return "키워드를 입력해주세요."

    all_results = []
    for keyword in keywords:
        code_results = await _run_sync(reg.searcher.search_code, keyword, 5)
        pattern_results = await _run_sync(reg.searcher.search_patterns, keyword, 3)
        all_results.extend(code_results)
        all_results.extend(pattern_results)

    seen = set()
    unique_results = []
    for r in all_results:
        key = (r.get('name'), r.get('type'))
        if key not in seen:
            seen.add(key)
            unique_results.append(r)

    combined_query = " ".join(keywords)
    reranked = reg.reranker.rerank(combined_query, unique_results, 15)
    track_node_references_batch(reranked, "smart_context", combined_query)

    reg.builder.max_tokens = max_tokens
    context = reg.builder.build(reranked, combined_query)

    header = f"# 스마트 컨텍스트\n키워드: {', '.join(keywords)}\n결과: {len(reranked)}개\n\n"
    return header + context


async def hybrid_search(reg, args: dict) -> str:
    query = args.get("query", "")
    limit = args.get("limit", 10)

    cache_key = f"hybrid:{query}:{limit}"
    cached = query_cache.get(cache_key)
    if cached:
        return cached

    strategy = reg.query_router.get_search_strategy(query)
    results = await _run_sync(reg.hybrid_search.search, query, strategy, limit)

    lines = [
        f"# 하이브리드 검색 결과",
        f"쿼리: {query}",
        f"모드: {strategy['intent']} (신뢰도: {strategy['confidence']:.1%})",
        f"결과: {len(results)}개\n"
    ]

    for i, item in enumerate(results, 1):
        item_type = item.get("type", "Unknown")
        name = item.get("name", "N/A")
        lines.append(f"## {i}. [{item_type}] {name}")

        if item_type in ("Function", "Class"):
            if item.get("qname"):
                lines.append(f"- 경로: `{item['qname']}`")
            if item.get("doc"):
                lines.append(f"- 설명: {item['doc'][:100]}...")
            if item.get("calls"):
                lines.append(f"- 호출: {', '.join(item['calls'])}")
            if item.get("called_by"):
                lines.append(f"- 호출자: {', '.join(item['called_by'])}")
        elif item_type == "Module":
            if item.get("path"):
                lines.append(f"- 경로: `{item['path']}`")
            if item.get("classes"):
                lines.append(f"- 클래스: {', '.join(item['classes'])}")
            if item.get("functions"):
                lines.append(f"- 함수: {', '.join(item['functions'])}")
        elif item_type == "Statistics":
            for k, v in item.get("data", {}).items():
                lines.append(f"- {k}: {v}")
        else:
            if item.get("description"):
                lines.append(f"- 설명: {item['description']}")

        lines.append("")

    result = "\n".join(lines)
    query_cache.set(cache_key, result)
    track_node_references_batch(results, "hybrid_search", query)

    if reg.hybrid_search and reg.hybrid_search.driver:
        for item in results[:5]:
            update_neo4j_access_count(
                reg.hybrid_search.driver,
                item.get("name", ""),
                item.get("type", "Function")
            )

    return result


async def get_call_graph(reg, args: dict) -> str:
    func_name = args.get("function_name", "")
    depth = min(args.get("depth", 2), 4)

    cache_key = f"callgraph:{func_name}:{depth}"
    cached = context_cache.get(cache_key)
    if cached:
        return cached

    graph_data = reg.hybrid_search.get_call_graph(func_name, depth)

    lines = [
        f"# 함수 호출 그래프: {func_name}",
        f"탐색 깊이: {depth}\n"
    ]

    outgoing = graph_data.get("outgoing", [])
    lines.append(f"## 호출하는 함수 ({len(outgoing)}개)")
    for item in outgoing:
        path = " → ".join(item.get("path", []))
        lines.append(f"- {path}")

    lines.append("")

    incoming = graph_data.get("incoming", [])
    lines.append(f"## 호출받는 함수 ({len(incoming)}개)")
    for item in incoming:
        path = " → ".join(item.get("path", []))
        lines.append(f"- {path}")

    result = "\n".join(lines)
    context_cache.set(cache_key, result)
    return result


async def get_similar_code(reg, args: dict) -> str:
    query = args.get("query", "")
    limit = args.get("limit", 5)

    cache_key = f"similar:{query}:{limit}"
    cached = query_cache.get(cache_key)
    if cached:
        return cached

    results = reg.hybrid_search.get_similar_code(query, limit)

    lines = [
        f"# 유사 코드 검색",
        f"쿼리: {query}",
        f"결과: {len(results)}개\n"
    ]

    for i, item in enumerate(results, 1):
        lines.append(f"## {i}. {item.get('name', 'N/A')}")
        if item.get("qname"):
            lines.append(f"- 경로: `{item['qname']}`")
        if item.get("doc"):
            lines.append(f"- 설명: {item['doc']}")
        if item.get("module"):
            lines.append(f"- 모듈: {item['module']}")
        lines.append(f"- 매칭 점수: {item.get('match_score', 0)}")
        lines.append("")

    result = "\n".join(lines)
    query_cache.set(cache_key, result)
    return result
