"""Write-back, evolution, feedback, and impact handlers."""

from pathlib import Path

from mcp_server.observability.session_tracker import get_current_session_id


async def provide_feedback(reg, args: dict) -> str:
    if not reg.weight_learner:
        return "NodeWeightLearner is not initialized."

    success = args.get("success", True)
    identifiers = args.get("identifiers", [])

    if not identifiers:
        return "No identifiers provided to update."

    session_id = get_current_session_id() or "unknown_session"
    result = reg.weight_learner.process_feedback(session_id, success, identifiers)

    if result.get("success"):
        action = "+0.2 가중치 증가 (최대 2.0)" if success else "-0.1 가중치 감소 (최소 0.1)"
        return f"피드백이 지식그래프에 반영되었습니다.\n업데이트된 노드 수: {result.get('updated', 0)}개\n적용된 행동: {action}\n다음 검색부터 이 정보가 우선순위에 반영됩니다."
    else:
        return f"업데이트 실패: {result.get('error', 'Unknown error')}"


async def simulate_impact(reg, args: dict) -> str:
    if not reg.impact_simulator:
        return "ImpactSimulator is not initialized."

    target = args.get("target_name")
    if not target:
        return "Error: target_name is required"

    depth = args.get("depth", 3)
    result = reg.impact_simulator.simulate_impact(target, depth)

    if result.get("success"):
        m = result["metrics"]
        target_info = result["target"]
        warning = result["warning"]

        report = [
            f"[Blast Radius Report] Target: {target_info['name']} ({target_info['type']})",
            f"Risk Level: {m['risk_level']} (Score: {m['risk_score']}/100)",
            f"경고: {warning}",
            "",
            "영향도 요약:",
            f"  - 총 영향 받는 노드: {m['total_affected_nodes']}개",
            f"  - 직접 호출하는 노드(1-hop): {m['direct_dependents']}개",
            f"  - 연쇄적으로 영향을 받는 노드(간접): {m['indirect_dependents']}개",
            f"  - 영향 받는 모듈(파일) 수: {m['modules_affected']}개",
            "",
        ]

        if result.get("affected_modules"):
            report.append("영향을 받는 주요 모듈:")
            for mod in result["affected_modules"][:5]:
                report.append(f"  - {mod}")

        if result.get("critical_dependents"):
            report.append("")
            report.append("직접적으로 타격을 입는 함수/클래스 (수정 시 확인 필수):")
            for dep in result["critical_dependents"]:
                report.append(f"  - [{dep['type']}] {dep['name']} (in {dep.get('module', 'unknown')})")

        return "\n".join(report)
    else:
        return f"시뮬레이션 실패: {result.get('error', 'Unknown error')}"


async def sync_incremental(reg, args: dict) -> str:
    if not reg.write_back:
        return "GraphWriteBack is not initialized."

    file_path = args.get("file_path")
    if not file_path:
        return "Error: file_path is required"

    resolved = Path(file_path).resolve()
    if not resolved.is_file():
        return f"Error: '{file_path}' is not a valid file"
    file_path = str(resolved)

    result = reg.write_back.sync_file(file_path)

    if result.get("success"):
        stats = result.get("stats", {})
        return f"성공적으로 지식그래프를 업데이트했습니다!\n파일: {file_path}\n- 반영된 함수: {stats.get('functions', 0)}개\n- 반영된 클래스: {stats.get('classes', 0)}개"
    else:
        return f"업데이트 실패: {result.get('error', 'Unknown error')}"


async def evolve_ontology(reg, args: dict) -> str:
    if not reg.ontology_evolver:
        return "OntologyEvolver is not initialized."

    auto_fix = args.get("auto_fix", False)
    report = reg.ontology_evolver.evolve(auto_fix)

    lines = [
        "# Ontology Evolution Report\n",
        f"총 이슈: {report['total_issues']}개 | 자동 수정: {'ON' if auto_fix else 'OFF'}\n",
    ]

    orphans = report.get("orphans", [])
    lines.append(f"## 1. Orphan Nodes ({len(orphans)}개)")
    for o in orphans[:5]:
        lines.append(f"  - [{o['type']}] {o['name']} ({o.get('module', 'N/A')})")
    if auto_fix and orphans:
        lines.append(f"  -> {len(orphans)}개 자동 삭제됨")

    gods = report.get("god_modules", [])
    lines.append(f"\n## 2. God Modules ({len(gods)}개)")
    for g in gods:
        lines.append(f"  - {g['name']}: {g['func_count']}개 함수")

    circles = report.get("circular_deps", [])
    lines.append(f"\n## 3. Circular Dependencies ({len(circles)}개)")
    for c in circles:
        lines.append(f"  - {c['module_a']} <-> {c['module_b']}")

    stale = report.get("stale_nodes", [])
    lines.append(f"\n## 4. Stale Nodes ({len(stale)}개)")
    for s in stale[:5]:
        lines.append(f"  - {s['name']}: score={s.get('score', 'N/A')}, {s.get('days_stale', '?')}일 미사용")

    drift = report.get("schema_drift", [])
    lines.append(f"\n## 5. Schema Drift ({len(drift)}개)")
    for d in drift[:5]:
        lines.append(f"  - {d['name']}: {d['filepath']} (파일 없음)")

    return "\n".join(lines)


async def promote_pattern(reg, args: dict) -> str:
    if not reg.knowledge_transfer:
        return "KnowledgeTransfer is not initialized."

    name = args.get("name")
    if not name:
        return "Error: name is required."

    result = reg.knowledge_transfer.promote_pattern(name)
    if result.get("success"):
        return f"{result['message']}\n이전 namespace: {result['previous_namespace']}\n점수: {result['score']}"
    return f"{result.get('error', 'Unknown error')}"


async def get_global_insights(reg, args: dict) -> str:
    if not reg.knowledge_transfer:
        return "KnowledgeTransfer is not initialized."

    limit = args.get("limit", 10)
    result = reg.knowledge_transfer.get_global_insights(limit)

    if not result.get("success"):
        return f"{result.get('error', 'Unknown')}"

    lines = ["# Cross-Project Global Insights\n"]

    gp = result.get("global_patterns", [])
    lines.append(f"## 검증된 글로벌 패턴 ({len(gp)}개)")
    for p in gp:
        lines.append(f"  - [{p['type']}] {p['name']} (score={p.get('score', 'N/A')}, from={p.get('origin', 'N/A')})")

    pc = result.get("promotion_candidates", [])
    lines.append(f"\n## 승격 후보 ({len(pc)}개)")
    for c in pc:
        lines.append(f"  - [{c['type']}] {c['name']} (score={c.get('score')}, ns={c.get('namespace', 'N/A')})")

    ap = result.get("anti_patterns", [])
    lines.append(f"\n## 안티패턴 경고 ({len(ap)}개)")
    for a in ap:
        lines.append(f"  - [{a['type']}] {a['name']} (score={a.get('score')})")

    return "\n".join(lines)


async def suggest_tests(reg, args: dict) -> str:
    if not reg.auto_test_gen:
        return "AutoTestGenerator is not initialized."

    func_name = args.get("function_name")
    if not func_name:
        return "Error: function_name is required."

    result = reg.auto_test_gen.suggest_tests(func_name)
    if not result.get("success"):
        return f"테스트 생성 실패: {result.get('error', 'Unknown')}"

    func = result["function"]
    mocks = result["mock_candidates"]
    usages = result["usage_patterns"]

    lines = [
        f"# Auto Test Suggestion: {func['name']}\n",
        f"**모듈**: {func.get('module', 'N/A')}",
        f"**시그니처**: {func.get('args', '()')}",
        f"**Mock 후보**: {', '.join(m['name'] for m in mocks) if mocks else 'None'}",
        f"**사용처**: {', '.join(u['name'] for u in usages) if usages else 'None'}",
        "",
        "## 테스트 스켈레톤",
        "```python",
        result["test_skeleton"],
        "```",
    ]

    return "\n".join(lines)


async def get_bug_hotspots(reg, args: dict) -> str:
    if not reg.bug_radar:
        return "BugRadar is not initialized."

    top_k = args.get("top_k", 10)
    result = reg.bug_radar.get_hotspots(top_k)

    if not result.get("success"):
        return f"핫스팟 조회 실패: {result.get('error', 'Unknown')}"

    hotspots = result["hotspots"]
    if not hotspots:
        return "버그 핫스팟이 감지되지 않았습니다. 코드가 안정적입니다."

    lines = [
        "# Predictive Bug Radar\n",
        f"총 {len(hotspots)}개 핫스팟 감지 (임계값: {result['threshold']}점)\n",
    ]

    for i, h in enumerate(hotspots, 1):
        severity_icon = {"CRITICAL": "CRIT", "HIGH": "HIGH", "MEDIUM": "MED", "LOW": "LOW"}.get(h.get("severity"), "?")
        lines.append(f"## {i}. [{severity_icon}] [{h['type']}] {h['name']}")
        lines.append(f"   - Risk Score: **{h['risk_score']}**/100 ({h.get('severity', 'N/A')})")
        lines.append(f"   - Churn: {h['churn']}회 수정")
        lines.append(f"   - Fan-in: {h['fan_in']} / Fan-out: {h['fan_out']}")
        lines.append(f"   - Lines: {h['line_count']}")
        if h.get("module"):
            lines.append(f"   - Module: {h['module']}")
        lines.append("")

    return "\n".join(lines)
