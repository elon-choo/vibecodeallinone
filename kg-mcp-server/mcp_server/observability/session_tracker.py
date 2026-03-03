#!/usr/bin/env python3
"""
═══════════════════════════════════════════════════════════════════════════════
Session Tracker v2.0 - Always-On Knowledge Graph Monitoring
═══════════════════════════════════════════════════════════════════════════════
모든 개발 세션을 추적하여 KG 로드율을 측정.
hook → session_start 기록, MCP 호출 → kg_loaded 기록, 미호출 → kg_skipped 기록.

핵심 메트릭: KG 로드율 = kg_loaded / total_dev_sessions × 100 (목표 ≥90%)
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import logging
import uuid
from datetime import datetime, timedelta
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

ANALYTICS_DIR = Path.home() / ".claude" / "mcp-kg-analytics"
ANALYTICS_DIR.mkdir(parents=True, exist_ok=True)
SESSIONS_FILE = ANALYTICS_DIR / "sessions.jsonl"
DASHBOARD_EVENTS_FILE = ANALYTICS_DIR / "dashboard_events.jsonl"
CURRENT_SESSION_FILE = ANALYTICS_DIR / "current_session.txt"


def generate_session_id() -> str:
    return str(uuid.uuid4())[:12]


def get_current_session_id() -> str:
    """파일 기반으로 현재 세션 ID를 읽음 (Hook → MCP 서버 공유)"""
    try:
        if CURRENT_SESSION_FILE.exists():
            sid = CURRENT_SESSION_FILE.read_text().strip()
            if sid and len(sid) > 4:
                return sid
    except Exception:
        pass
    return "unknown"


def write_session_event(event: dict):
    """세션 이벤트를 JSONL 파일에 기록"""
    try:
        with open(SESSIONS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, ensure_ascii=False) + "\n")
    except Exception as e:
        logger.warning(f"Failed to write session event: {e}")


def record_session_start(session_id: str, keywords: list, prompt_snippet: str = ""):
    """개발 세션 시작 기록 (hook에서 호출)"""
    write_session_event({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "session_start",
        "session_id": session_id,
        "keywords": keywords[:10],
        "prompt_snippet": prompt_snippet[:100],
    })


def record_kg_loaded(session_id: str, tool_name: str, query: str, results_count: int):
    """KG 로드 완료 기록 (MCP 도구 호출 성공 시)"""
    write_session_event({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "kg_loaded",
        "session_id": session_id,
        "tool": tool_name,
        "query": query,
        "results_count": results_count,
    })


def record_session_end(session_id: str, kg_used: bool, tools_called: int = 0):
    """세션 종료 기록"""
    write_session_event({
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "type": "session_end",
        "session_id": session_id,
        "kg_used": kg_used,
        "tools_called": tools_called,
    })


def load_sessions(days: int = 7) -> list:
    """최근 N일 세션 이벤트 로드"""
    events = []
    cutoff = datetime.utcnow() - timedelta(days=days)

    if not SESSIONS_FILE.exists():
        return events

    try:
        with open(SESSIONS_FILE, "r", encoding="utf-8") as f:
            for line in f:
                try:
                    event = json.loads(line.strip())
                    ts = event.get("timestamp", "").replace("Z", "+00:00")
                    event_time = datetime.fromisoformat(ts).replace(tzinfo=None)
                    if event_time > cutoff:
                        events.append(event)
                except Exception:
                    continue
    except Exception as e:
        logger.warning(f"Failed to load sessions: {e}")

    return events


def calculate_kg_load_rate(days: int = 7) -> dict:
    """KG 로드율 계산 - 핵심 메트릭 (ID 매칭 + 시간 기반 폴백)"""
    events = load_sessions(days)

    session_starts = {}
    kg_loaded_sessions = set()
    kg_loaded_events = []

    for e in events:
        etype = e.get("type")
        sid = e.get("session_id", "")

        if etype == "session_start":
            session_starts[sid] = e
        elif etype == "kg_loaded":
            kg_loaded_sessions.add(sid)
            kg_loaded_events.append(e)

    total_sessions = len(session_starts)

    # 1차: 정확한 session_id 매칭
    loaded_sessions = len(kg_loaded_sessions & set(session_starts.keys()))

    # 2차: 시간 기반 매칭 폴백 (ID가 "auto"/"unknown"인 경우)
    if loaded_sessions < total_sessions:
        for sid, start_event in session_starts.items():
            if sid in kg_loaded_sessions:
                continue  # 이미 매칭됨
            try:
                start_ts = start_event.get("timestamp", "").replace("Z", "+00:00")
                start_dt = datetime.fromisoformat(start_ts).replace(tzinfo=None)
                for load_event in kg_loaded_events:
                    load_ts = load_event.get("timestamp", "").replace("Z", "+00:00")
                    load_dt = datetime.fromisoformat(load_ts).replace(tzinfo=None)
                    if abs((load_dt - start_dt).total_seconds()) < 120:
                        loaded_sessions += 1
                        break
            except Exception:
                continue

    if total_sessions == 0:
        return {
            "value": None,
            "display": "- (세션 없음)",
            "total_sessions": 0,
            "loaded_sessions": 0,
            "skipped_sessions": 0,
            "note": None,
        }

    rate = (loaded_sessions / total_sessions) * 100
    skipped = total_sessions - loaded_sessions

    display = f"{rate:.0f}%"
    note = None
    if total_sessions < 10:
        display = f"{rate:.0f}%*"
        note = f"세션 {total_sessions}개 (10개 미만)"

    return {
        "value": round(rate, 1),
        "display": display,
        "total_sessions": total_sessions,
        "loaded_sessions": loaded_sessions,
        "skipped_sessions": skipped,
        "note": note,
    }


def get_session_list(days: int = 7, limit: int = 50) -> list:
    """세션 목록 조회 (대시보드용)"""
    events = load_sessions(days)

    sessions = {}
    for e in events:
        sid = e.get("session_id", "unknown")
        if sid not in sessions:
            sessions[sid] = {
                "session_id": sid,
                "start_time": None,
                "end_time": None,
                "keywords": [],
                "kg_loaded": False,
                "tools_called": 0,
                "tool_details": [],
            }

        s = sessions[sid]
        etype = e.get("type")

        if etype == "session_start":
            s["start_time"] = e.get("timestamp")
            s["keywords"] = e.get("keywords", [])
        elif etype == "kg_loaded":
            s["kg_loaded"] = True
            s["tools_called"] += 1
            s["tool_details"].append({
                "tool": e.get("tool"),
                "query": e.get("query"),
                "results": e.get("results_count", 0),
                "timestamp": e.get("timestamp"),
            })
        elif etype == "session_end":
            s["end_time"] = e.get("timestamp")
            if not s["kg_loaded"]:
                s["kg_loaded"] = e.get("kg_used", False)

    result = sorted(
        sessions.values(),
        key=lambda x: x.get("start_time") or "",
        reverse=True,
    )

    return result[:limit]


def get_daily_session_stats(days: int = 7) -> list:
    """일별 세션 통계"""
    events = load_sessions(days)

    daily = {}
    session_days = {}

    for e in events:
        ts = e.get("timestamp", "")[:10]
        sid = e.get("session_id", "")
        etype = e.get("type")

        if ts not in daily:
            daily[ts] = {"starts": set(), "loaded": set()}

        if etype == "session_start":
            daily[ts]["starts"].add(sid)
            session_days[sid] = ts
        elif etype == "kg_loaded":
            day = session_days.get(sid, ts)
            if day in daily:
                daily[day]["loaded"].add(sid)

    result = []
    for date in sorted(daily.keys()):
        d = daily[date]
        total = len(d["starts"])
        loaded = len(d["loaded"] & d["starts"])
        rate = (loaded / total * 100) if total > 0 else None
        result.append({
            "date": date,
            "total_sessions": total,
            "loaded_sessions": loaded,
            "kg_load_rate": round(rate, 1) if rate is not None else None,
        })

    return result
