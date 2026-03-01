#!/usr/bin/env python3
"""
KG Pre-Check Hook (Layer 2)
============================
Write/Edit 도구 사용 직전에 실행.
현재 세션에서 KG가 로드되었는지 확인하고, 미로드 시 리마인드.
"""

import json
import sys
from pathlib import Path
from datetime import datetime, timedelta

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"


def check_kg_loaded() -> bool:
    """현재 세션에서 KG가 로드되었는지 확인"""
    session_file = ANALYTICS_DIR / "current_session.txt"
    sessions_file = ANALYTICS_DIR / "sessions.jsonl"

    if not session_file.exists() or not sessions_file.exists():
        return False

    current_sid = session_file.read_text().strip()
    if not current_sid:
        return False

    # 세션 파일에서 kg_loaded 또는 kg_injected 확인
    try:
        with open(sessions_file) as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    if e.get("session_id") == current_sid:
                        if e.get("type") == "kg_loaded":
                            return True
                        if e.get("type") == "session_start" and e.get("kg_injected"):
                            return True
                except (json.JSONDecodeError, KeyError):
                    continue
    except OSError:
        pass

    # 시간 기반 폴백: 최근 2분 내 아무 kg_loaded가 있으면 OK
    try:
        cutoff = datetime.utcnow() - timedelta(minutes=2)
        with open(sessions_file) as f:
            for line in f:
                try:
                    e = json.loads(line.strip())
                    if e.get("type") in ("kg_loaded", "session_start"):
                        ts = e.get("timestamp", "").replace("Z", "+00:00")
                        t = datetime.fromisoformat(ts).replace(tzinfo=None)
                        if t > cutoff and (e.get("type") == "kg_loaded" or e.get("kg_injected")):
                            return True
                except (json.JSONDecodeError, KeyError, ValueError):
                    continue
    except OSError:
        pass

    return False


def main():
    if check_kg_loaded():
        sys.exit(0)  # KG 로드됨 - 통과

    # KG 미로드 - 리마인드 출력
    print("<system-reminder>")
    print("WARNING: Writing code WITHOUT knowledge graph context.")
    print("Consider calling mcp__neo4j-knowledge-graph__hybrid_search first.")
    print("</system-reminder>")


if __name__ == "__main__":
    main()
