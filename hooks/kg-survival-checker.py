#!/usr/bin/env python3
"""
KG Survival Checker v1.0 (Phase 2-3)
======================================
PostToolUse Hook - Write/Edit 시 이전에 주입했던 코드가 삭제/되돌려졌는지 확인.
삭제 감지 시 강한 부정 신호 → Neo4j negative_score 대폭 증가.

작동:
1. Edit 시 old_string을 분석하여 이전 주입 식별자가 제거됐는지 확인
2. 제거된 식별자 → negative_score += 2.0 (강한 트라우마)
3. 이벤트 기록
"""

import os
import sys
import json
import re
from pathlib import Path
from datetime import datetime

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"
FEEDBACK_FILE = ANALYTICS_DIR / "feedback_events.jsonl"
INJECTED_FILE = ANALYTICS_DIR / "last_injected_identifiers.json"

DELETION_PENALTY = 2.0  # 삭제 시 강한 트라우마


def _load_power_pack_env():
    """Load ~/.claude/power-pack.env into os.environ if keys not already set."""
    env_file = Path.home() / ".claude" / "power-pack.env"
    if env_file.exists():
        for line in env_file.read_text().splitlines():
            line = line.strip()
            if line and not line.startswith("#") and "=" in line:
                key, _, value = line.partition("=")
                os.environ.setdefault(key.strip(), value.strip())


def read_tool_input():
    """PostToolUse hook: stdin JSON에서 tool_input 추출, env var 폴백"""
    # 1차: stdin에서 읽기 (Claude Code PostToolUse hook 표준)
    try:
        if not sys.stdin.isatty():
            stdin_data = sys.stdin.read()
            if stdin_data:
                parsed = json.loads(stdin_data)
                tool_input_obj = parsed.get("tool_input", {})
                if isinstance(tool_input_obj, dict) and tool_input_obj:
                    return tool_input_obj
    except Exception:
        pass
    # 2차: 환경변수 폴백 (수동 테스트용)
    tool_input = os.environ.get("CLAUDE_TOOL_INPUT", "")
    if tool_input:
        try:
            return json.loads(tool_input)
        except Exception:
            pass
    return None


def main():
    data = read_tool_input()
    if not data:
        sys.exit(0)

    # Edit 도구만 처리 (old_string → new_string 변경 추적)
    old_string = data.get("old_string", "")
    new_string = data.get("new_string", "")
    file_path = data.get("file_path", "")

    if not old_string or not file_path:
        sys.exit(0)

    # 코드 파일만
    if not any(file_path.endswith(ext) for ext in ['.py', '.js', '.ts', '.tsx', '.jsx']):
        sys.exit(0)

    # 주입된 식별자 로드
    try:
        if not INJECTED_FILE.exists():
            sys.exit(0)
        injected = json.loads(INJECTED_FILE.read_text())
        identifiers = injected.get("identifiers", [])
        session_id = injected.get("session_id", "")
        intent = injected.get("intent", "UNKNOWN")
    except Exception:
        sys.exit(0)

    if not identifiers:
        sys.exit(0)

    # old_string에 있었지만 new_string에서 제거된 식별자 찾기
    old_lower = old_string.lower()
    new_lower = new_string.lower()

    removed = []
    for ident in identifiers:
        il = ident.lower()
        was_in_old = il in old_lower
        is_in_new = il in new_lower
        if was_in_old and not is_in_new:
            removed.append(ident)

    if not removed:
        sys.exit(0)

    # 강한 부정 신호 기록
    try:
        event = {
            "timestamp": datetime.utcnow().isoformat() + "Z",
            "type": "code_deletion",
            "session_id": session_id,
            "intent": intent,
            "removed_identifiers": removed,
            "removed_count": len(removed),
            "file_path": file_path,
            "penalty": DELETION_PENALTY,
        }
        FEEDBACK_FILE.parent.mkdir(parents=True, exist_ok=True)
        with open(FEEDBACK_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception:
        pass

    # Neo4j 강한 트라우마 업데이트
    try:
        from neo4j import GraphDatabase
        _load_power_pack_env()
        password = os.getenv("NEO4J_PASSWORD", "")
        if not password:
            return
        driver = GraphDatabase.driver(
            os.getenv("NEO4J_URI", "bolt://localhost:7687"),
            auth=(os.getenv("NEO4J_USERNAME", "neo4j"), password),
            connection_timeout=2,
        )
        with driver.session() as session:
            for name in removed:
                session.run("""
                    MATCH (n) WHERE n.name = $name
                    SET n.negative_score = coalesce(n.negative_score, 0) + $penalty,
                        n.deletion_count = coalesce(n.deletion_count, 0) + 1,
                        n.last_deleted = datetime(),
                        n.relevance_score =
                            (coalesce(n.positive_score, 0) - 0.5 * (coalesce(n.negative_score, 0) + $penalty))
                            / (coalesce(n.positive_score, 0) + coalesce(n.negative_score, 0) + $penalty + 1.0)
                """, name=name, penalty=DELETION_PENALTY)
        driver.close()
    except Exception:
        pass

    print(f"[KG-Survival] DELETION detected: {removed} penalty={DELETION_PENALTY}", file=sys.stderr)


if __name__ == "__main__":
    main()
