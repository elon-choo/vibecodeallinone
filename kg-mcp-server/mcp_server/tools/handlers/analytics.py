"""Cache, analytics, and quality report handlers."""

from mcp_server.pipeline.cache import get_cache_stats
from mcp_server.observability.analytics import (
    get_analytics_summary,
    get_reference_timeline,
    get_quality_metrics,
    get_neo4j_recently_accessed,
    get_neo4j_top_accessed,
)


async def get_cache_stats_v2(_reg, _args: dict) -> str:
    stats = get_cache_stats()

    lines = ["# 캐시 통계 (v2)\n"]

    for cache_name, cache_stats in stats.items():
        lines.append(f"## {cache_name}")
        lines.append(f"- 히트: {cache_stats.get('hits', 0)}")
        lines.append(f"- 미스: {cache_stats.get('misses', 0)}")
        lines.append(f"- 히트율: {cache_stats.get('hit_rate', '0%')}")
        lines.append(f"- 크기: {cache_stats.get('size', 0)}/{cache_stats.get('max_size', 0)}")
        lines.append(f"- TTL: {cache_stats.get('ttl_seconds', 0)}초")
        lines.append(f"- 퇴출: {cache_stats.get('evictions', 0)}")
        lines.append("")

    return "\n".join(lines)


async def get_analytics_summary_handler(_reg, _args: dict) -> str:
    summary = get_analytics_summary()

    lines = [
        "# 지식그래프 분석 요약\n",
        f"## 참조 통계",
        f"- 총 참조 횟수: {summary.get('total_references', 0):,}",
        f"- 참조된 고유 노드: {summary.get('unique_nodes_referenced', 0)}",
        f"- 최근 24시간 참조: {summary.get('recent_references_count', 0)}",
        f"- 최근 24시간 변경: {summary.get('recent_changes_count', 0)}",
        "",
        "## 가장 많이 참조된 노드"
    ]

    for item in summary.get('top_referenced', [])[:10]:
        lines.append(f"- {item['name']}: {item['count']}회")

    lines.append("\n## 노드 타입별 참조 분포")
    for node_type, count in summary.get('type_distribution', {}).items():
        lines.append(f"- {node_type}: {count}회")

    lines.append("\n## 도구별 사용 분포")
    for tool, count in summary.get('tool_distribution', {}).items():
        lines.append(f"- {tool}: {count}회")

    quality = summary.get('quality_metrics', {})
    lines.append("\n## 품질 지표")
    lines.append(f"- 분포 균형 (엔트로피): {quality.get('entropy_score', 0):.2%}")

    bias = quality.get('bias_indicators', {})
    if bias.get('recency_bias'):
        lines.append(f"- 최신성 편향: {bias['recency_bias']:.1%}")

    return "\n".join(lines)


async def get_top_referenced(reg, args: dict) -> str:
    limit = args.get('limit', 20)

    summary = get_analytics_summary()
    local_top = summary.get('top_referenced', [])[:limit]

    neo4j_top = []
    if reg.hybrid_search and reg.hybrid_search.driver:
        neo4j_top = get_neo4j_top_accessed(reg.hybrid_search.driver, limit)

    lines = ["# 가장 많이 참조된 지식 노드\n"]

    if neo4j_top:
        lines.append("## Neo4j 기준 (access_count)")
        for i, item in enumerate(neo4j_top, 1):
            lines.append(f"{i}. [{item.get('type')}] {item.get('name')}: {item.get('access_count')}회")
        lines.append("")

    lines.append("## 세션 기준 (실시간)")
    for i, item in enumerate(local_top, 1):
        lines.append(f"{i}. {item['name']}: {item['count']}회")

    return "\n".join(lines)


async def get_recent_activity(reg, args: dict) -> str:
    hours = args.get('hours', 24)

    lines = [f"# 최근 {hours}시간 지식그래프 활동\n"]

    if reg.hybrid_search and reg.hybrid_search.driver:
        recent = get_neo4j_recently_accessed(reg.hybrid_search.driver, 20)
        lines.append("## 최근 접근된 노드")
        for item in recent[:10]:
            last_accessed = item.get('last_accessed', 'N/A')
            if hasattr(last_accessed, 'isoformat'):
                last_accessed = last_accessed.isoformat()
            lines.append(f"- [{item.get('type')}] {item.get('name')} (접근: {item.get('access_count')}회, 마지막: {last_accessed})")

    timeline = get_reference_timeline(hours=hours, interval_minutes=60)
    lines.append(f"\n## 시간대별 참조 횟수")
    for entry in timeline[-12:]:
        lines.append(f"- {entry['time']}: {entry['count']}회")

    return "\n".join(lines)


async def get_quality_report(_reg, _args: dict) -> str:
    quality = get_quality_metrics()
    summary = get_analytics_summary()

    lines = [
        "# 지식그래프 품질 리포트\n",
        "## 분포 균형 분석"
    ]

    entropy = quality.type_distribution_entropy
    if entropy >= 0.8:
        entropy_grade = "우수 (균형 잡힌 분포)"
    elif entropy >= 0.6:
        entropy_grade = "보통 (약간의 편향)"
    else:
        entropy_grade = "주의 (심한 편향)"

    lines.append(f"- 엔트로피 점수: {entropy:.2%} {entropy_grade}")

    bias = quality.bias_indicators
    type_bias = bias.get('type_bias', {})
    if type_bias:
        lines.append("\n## 노드 타입 편향")
        for node_type, deviation in sorted(type_bias.items(), key=lambda x: -x[1])[:5]:
            if deviation > 0.5:
                status = "과다 참조"
            elif deviation < -0.3:
                status = "과소 참조"
            else:
                status = "적정"
            lines.append(f"- {node_type}: 편차 {deviation:.1%} {status}")

    recency = bias.get('recency_bias', 0)
    lines.append(f"\n## 최신성 편향")
    if recency > 0.8:
        lines.append(f"- 점수: {recency:.1%} 최근 노드에 집중됨")
        lines.append("- 권장: 과거 지식도 균형있게 참조 필요")
    elif recency > 0.5:
        lines.append(f"- 점수: {recency:.1%} 약간의 최신성 편향")
    else:
        lines.append(f"- 점수: {recency:.1%} 균형 잡힌 시간 분포")

    lines.append("\n## 개선 권장사항")
    if entropy < 0.6:
        lines.append("1. 덜 참조되는 노드 타입을 검토하고 활용도 높이기")
    if recency > 0.8:
        lines.append("2. 오래된 지식도 정기적으로 검토하고 업데이트하기")

    type_dist = summary.get('type_distribution', {})
    total = sum(type_dist.values())
    if total > 0:
        for node_type, count in type_dist.items():
            ratio = count / total
            if ratio < 0.05:
                lines.append(f"3. {node_type} 타입이 거의 사용되지 않음 ({ratio:.1%})")
                break

    if not lines[-1].startswith("1.") and not lines[-1].startswith("2.") and not lines[-1].startswith("3."):
        lines.append("현재 지식그래프 품질이 양호합니다!")

    return "\n".join(lines)
