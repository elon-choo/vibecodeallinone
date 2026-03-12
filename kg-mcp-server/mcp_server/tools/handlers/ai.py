"""AI, vector search, RAG, code-assist, and doc-generation handlers."""


async def semantic_search(reg, args: dict) -> str:
    if not reg.vector_search_engine:
        return "VectorSearchEngine is not initialized."

    query = args.get("query", "")
    limit = args.get("limit", 10)
    threshold = args.get("threshold", 0.7)

    result = reg.vector_search_engine.semantic_search(query, limit, threshold)

    if not result.get("success"):
        return f"검색 실패: {result.get('error', 'Unknown')}"

    lines = [
        f"# Semantic Search Results",
        f"쿼리: {query}",
        f"결과: {result['total']}개 (threshold: {threshold})\n",
    ]

    for i, item in enumerate(result.get("results", []), 1):
        sim = item.get("similarity", 0)
        sim_bar = "█" * int(sim * 10) + "░" * (10 - int(sim * 10))
        lines.append(f"## {i}. [{item.get('type')}] {item.get('name')}")
        lines.append(f"   유사도: {sim_bar} {sim:.3f}")
        if item.get("qname"):
            lines.append(f"   경로: `{item['qname']}`")
        if item.get("docstring"):
            lines.append(f"   설명: {item['docstring'][:150]}")
        if item.get("module"):
            lines.append(f"   모듈: {item['module']}")
        if item.get("calls"):
            lines.append(f"   호출: {', '.join(item['calls'])}")
        if item.get("called_by"):
            lines.append(f"   호출자: {', '.join(item['called_by'])}")
        lines.append("")

    return "\n".join(lines)


async def ask_codebase(reg, args: dict) -> str:
    if not reg.rag_engine:
        return "RAGEngine is not initialized."

    question = args.get("question", "")
    max_tokens = args.get("max_context_tokens", 6000)

    result = reg.rag_engine.ask(question, max_tokens)

    if not result.get("success"):
        return f"RAG 실패: {result.get('error', 'Unknown')}"

    lines = [
        f"# 코드베이스 답변\n",
        result["answer"],
        f"\n---",
        f"**검색된 소스**: {result['sources_count']}개",
        f"**컨텍스트**: ~{result['context_tokens']} tokens",
        f"**검색 전략**: {result.get('search_strategy', 'N/A')}",
    ]

    if result.get("from_cache"):
        lines.append("**캐시**: 캐시된 답변 (5분 TTL)")

    citations = result.get("citations", [])
    if citations:
        lines.append(f"\n**참조된 코드**:")
        for c in citations[:10]:
            lines.append(
                f"- [{c['type']}] {c['name']} ({c.get('module', 'N/A')})"
            )

    return "\n".join(lines)


async def evaluate_code(reg, args: dict) -> str:
    if not reg.llm_judge:
        return "LLMJudge is not initialized."

    file_path = args.get("file_path")
    code_snippet = args.get("code_snippet")

    if not file_path and not code_snippet:
        return "Error: file_path or code_snippet is required."

    result = reg.llm_judge.evaluate_code(file_path, code_snippet)

    if not result.get("success"):
        return f"Evaluation failed: {result.get('error', 'Unknown')}"

    lines = [
        f"# Code Quality Evaluation",
        f"",
        f"**Overall Score: {result['overall_score']}/5**",
        f"",
        "## Criteria Scores",
    ]
    for criterion, score in result.get("criteria", {}).items():
        bar = "█" * score + "░" * (5 - score)
        lines.append(f"- {criterion}: {bar} {score}/5")

    lines.append(f"\n## Feedback")
    lines.append(result.get("feedback", ""))

    suggestions = result.get("suggestions", [])
    if suggestions:
        lines.append(f"\n## Suggestions")
        for i, s in enumerate(suggestions, 1):
            lines.append(f"{i}. {s}")

    if result.get("eval_id"):
        lines.append(f"\n---\nEval ID: {result['eval_id']}")

    return "\n".join(lines)


async def assist_code(reg, args: dict) -> str:
    if not reg.code_assist:
        return "CodeAssist is not initialized."

    target = args.get("target_function", "")
    instruction = args.get("instruction", "")

    result = reg.code_assist.assist(target, instruction)

    if not result.get("success"):
        return f"코드 어시스트 실패: {result.get('error')}"

    lines = [
        f"# Code Assist: {result['function']}",
        f"**Module**: {result.get('module', 'N/A')}",
        f"**Instruction**: {result['instruction']}",
        f"**Original Lines**: {result.get('original_lines', 'N/A')}",
        "",
        "## Changes Summary",
        result.get("changes_summary", ""),
        "",
        "## Modified Code",
        "```python",
        result.get("modified_code", ""),
        "```",
    ]

    imports = result.get("added_imports", [])
    if imports:
        lines.append("\n## Added Imports")
        for imp in imports:
            lines.append(f"- `{imp}`")

    warnings = result.get("warnings", [])
    if warnings:
        lines.append("\n## Warnings")
        for w in warnings:
            lines.append(f"- {w}")

    return "\n".join(lines)


async def generate_docs(reg, args: dict) -> str:
    if not reg.doc_generator:
        return "DocGenerator is not initialized."

    module_name = args.get("module_name", "*")
    depth = args.get("depth", 2)

    result = reg.doc_generator.generate(module_name, depth)

    if not result.get("success"):
        return f"문서 생성 실패: {result.get('error')}"

    return result["markdown"]
