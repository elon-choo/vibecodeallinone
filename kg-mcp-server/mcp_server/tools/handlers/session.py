"""Session and conversation context handlers."""

import os

from mcp_server.pipeline.adaptive_context import ConversationMemory


async def get_session_context(_reg, args: dict) -> str:
    project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
    memory = ConversationMemory(project_dir)

    if args.get("reset"):
        memory.reset()
        return "대화 컨텍스트가 초기화되었습니다."

    summary = memory.get_context_summary()
    refinement = memory.get_search_refinement()

    lines = [
        "# 대화 세션 컨텍스트 (Phase 5.2)\n",
        f"- 대화 ID: {summary['conversation_id']}",
        f"- 턴 수: {summary['turn_count']}",
        f"- 현재 Intent: {summary['current_intent'] or 'N/A'}",
        f"- Intent 흐름: {' -> '.join(summary['intent_flow']) if summary['intent_flow'] else 'N/A'}",
        f"- 집중 범위: {summary['focus_scope'] or '전체'}",
        f"- Narrowing 레벨: {summary['narrowing_level']} (0=광범위, 3=핀포인트)",
        f"- 누적 주입 노드: {summary['total_injected']}개",
    ]

    transition = summary.get("intent_transition")
    if transition:
        lines.append(f"\nIntent 전환 감지: {transition['from']} -> {transition['to']}")

    if summary["top_entities"]:
        lines.append("\n## 핵심 엔티티 (언급 빈도순)")
        for e in summary["top_entities"]:
            lines.append(f"  - {e['name']}: {e['count']}회 ({e['type']})")

    lines.append("\n## 검색 최적화 힌트")
    if refinement["boost_entities"]:
        lines.append(f"  - Boost: {', '.join(refinement['boost_entities'])}")
    if refinement["suppress_entities"]:
        lines.append(f"  - Suppress: {', '.join(refinement['suppress_entities'])}")
    lines.append(f"  - 권장 결과 수: {refinement['max_items']}개")

    return "\n".join(lines)
