"""
Real-time Dashboard v5 (Phase 10)
===================================
WebSocket 기반 실시간 MCP 지식그래프 모니터링 대시보드.
Tab Navigation + Chart.js + PM2 Health + Feedback + Context Analytics.
Port: 9093
"""
import asyncio
import json
import logging
import time
import os
import subprocess
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse
from neo4j import GraphDatabase

logger = logging.getLogger(__name__)

app = FastAPI(title="KG Dashboard v5", version="5.0")

# Neo4j connection
NEO4J_URI = os.getenv("NEO4J_URI", "bolt://localhost:7687")
NEO4J_USER = os.getenv("NEO4J_USERNAME", "neo4j")
NEO4J_PASS = os.getenv("NEO4J_PASSWORD", "")

driver = None


def get_driver():
    global driver
    if driver is None:
        driver = GraphDatabase.driver(NEO4J_URI, auth=(NEO4J_USER, NEO4J_PASS))
    return driver


# WebSocket connections
active_connections: List[WebSocket] = []

# Event log (circular buffer)
event_log: List[Dict] = []
MAX_EVENTS = 200


def add_event(event: Dict):
    """이벤트 로그에 추가 (외부에서 호출 가능)"""
    event["timestamp"] = time.time()
    event_log.append(event)
    if len(event_log) > MAX_EVENTS:
        event_log.pop(0)


@app.get("/", response_class=HTMLResponse)
async def dashboard_page():
    """대시보드 HTML 반환"""
    html_path = Path(__file__).parent / "index.html"
    return html_path.read_text(encoding="utf-8")


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket 연결 관리"""
    await websocket.accept()
    active_connections.append(websocket)
    try:
        # 초기 데이터 전송
        initial_data = await get_dashboard_data()
        await websocket.send_json({"type": "initial", "data": initial_data})

        while True:
            # 주기적 업데이트 (3초마다)
            await asyncio.sleep(3)
            update_data = await get_dashboard_data()
            await websocket.send_json({"type": "update", "data": update_data})
    except WebSocketDisconnect:
        active_connections.remove(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        if websocket in active_connections:
            active_connections.remove(websocket)


@app.get("/api/stats")
async def api_stats():
    """REST API: 통계"""
    return await get_dashboard_data()


async def get_dashboard_data() -> Dict[str, Any]:
    """대시보드 데이터 수집"""
    d = get_driver()
    data = {}

    with d.session() as session:
        # 1. 노드 통계
        node_stats = session.run("""
            MATCH (n)
            WITH labels(n)[0] as label, count(n) as cnt
            RETURN label, cnt ORDER BY cnt DESC LIMIT 20
        """)
        data["node_stats"] = {r["label"]: r["cnt"] for r in node_stats}

        # 2. 총 노드/엣지
        totals = session.run("""
            MATCH (n) WITH count(n) as nodes
            MATCH ()-[r]->() WITH nodes, count(r) as edges
            RETURN nodes, edges
        """).single()
        data["total_nodes"] = totals["nodes"] if totals else 0
        data["total_edges"] = totals["edges"] if totals else 0

        # 3. 임베딩 커버리지
        embed_stats = session.run("""
            MATCH (n) WHERE n:Function OR n:Class
            WITH count(n) as total,
                 count(CASE WHEN n.embedding IS NOT NULL THEN 1 END) as embedded
            RETURN total, embedded
        """).single()
        data["embedding_total"] = embed_stats["total"] if embed_stats else 0
        data["embedding_done"] = embed_stats["embedded"] if embed_stats else 0

        # 4. 최근 수정 노드 (Bug Radar 용)
        recent_mods = session.run("""
            MATCH (n:Function)
            WHERE n.modification_count IS NOT NULL AND n.modification_count > 0
            RETURN n.name as name, n.modification_count as mods,
                   n.module as module
            ORDER BY n.modification_count DESC
            LIMIT 10
        """)
        data["hotspots"] = [dict(r) for r in recent_mods]

        # 5. Namespace 분포
        ns_stats = session.run("""
            MATCH (n)
            WHERE n.namespace IS NOT NULL
            WITH n.namespace as ns, count(n) as cnt
            RETURN ns, cnt ORDER BY cnt DESC LIMIT 10
        """)
        data["namespace_dist"] = {r["ns"]: r["cnt"] for r in ns_stats}

        # 6. 데이터 의존성 엣지 통계
        dep_stats = session.run("""
            MATCH ()-[r]->()
            WHERE type(r) IN ['READS_CONFIG', 'ACCESSES_TABLE', 'SHARES_STATE']
            RETURN type(r) as rel_type, count(r) as cnt
        """)
        data["data_deps"] = {r["rel_type"]: r["cnt"] for r in dep_stats}

    # 7. 이벤트 로그 (최근 20개)
    data["recent_events"] = event_log[-20:]

    # 8. 서버 시간
    data["server_time"] = time.time()

    return data


@app.get("/api/search")
async def api_search(q: str = "", mode: str = "hybrid"):
    """검색 테스트 API — Search Playground용"""
    if not q.strip():
        return {"results": [], "strategy": {}}

    d = get_driver()
    try:
        if mode == "vector":
            from mcp_server.pipeline.vector_search import VectorSearchEngine
            vs = VectorSearchEngine(d)
            results = vs.semantic_search(q, limit=10, threshold=0.3)
            # vector_search returns list of dicts directly
            return {"results": results if isinstance(results, list) else results.get("results", []), "strategy": {"mode": "vector"}}
        else:
            from mcp_server.pipeline.hybrid_search import HybridSearchEngine
            from mcp_server.pipeline.query_router import QueryRouter
            hs = HybridSearchEngine(d)
            qr = QueryRouter()
            strategy = qr.get_search_strategy(q)
            results = hs.search(q, strategy, 10)
            return {"results": results, "strategy": strategy}
    except Exception as e:
        logger.error(f"Search API error: {e}")
        return {"results": [], "error": str(e)}


@app.get("/api/namespaces")
async def api_namespaces():
    """프로젝트(Namespace) 목록 + 노드 수"""
    d = get_driver()
    with d.session() as s:
        r = s.run("""
            MATCH (n) WHERE n.namespace IS NOT NULL
            WITH n.namespace AS ns, count(n) AS cnt
            RETURN ns, cnt ORDER BY cnt DESC LIMIT 30
        """).data()
    return {"namespaces": r}


@app.get("/api/stats/by-namespace")
async def api_stats_by_namespace(ns: str = ""):
    """특정 네임스페이스의 노드/엣지 통계"""
    if not ns:
        return {"error": "namespace required"}
    d = get_driver()
    with d.session() as s:
        node_stats = s.run("""
            MATCH (n) WHERE n.namespace = $ns
            WITH labels(n)[0] as label, count(n) as cnt
            RETURN label, cnt ORDER BY cnt DESC LIMIT 20
        """, ns=ns).data()

        totals = s.run("""
            MATCH (n) WHERE n.namespace = $ns
            WITH count(n) as nodes
            RETURN nodes
        """, ns=ns).single()

    return {
        "namespace": ns,
        "total_nodes": totals["nodes"] if totals else 0,
        "node_stats": {r["label"]: r["cnt"] for r in node_stats}
    }


@app.get("/api/judge-history")
async def api_judge_history():
    """Judge 평가 이력 (최근 20개)"""
    log_file = os.path.expanduser("~/.claude/kg-judge-log/judge.jsonl")
    entries = []
    if os.path.isfile(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entries.append(json.loads(line))
                except Exception:
                    pass
    return {"entries": entries[-20:]}


@app.get("/api/github-ratio")
async def api_github_ratio():
    """GitHub vs Local 노드 비율"""
    d = get_driver()
    with d.session() as s:
        result = s.run("""
            MATCH (n)
            WHERE n:Function OR n:Class OR n:Module
            WITH count(n) as total,
                 count(CASE WHEN n.repo IS NOT NULL AND n.repo <> '' THEN 1 END) as github
            RETURN total, github, total - github as local
        """).single()
    if result:
        return {
            "total": result["total"],
            "github": result["github"],
            "local": result["local"]
        }
    return {"total": 0, "github": 0, "local": 0}


@app.get("/api/services")
async def api_services():
    """PM2 서비스 상태"""
    try:
        r = subprocess.run(["pm2", "jlist"], capture_output=True, text=True, timeout=5)
        procs = json.loads(r.stdout)
        services = []
        for p in procs:
            pm2_env = p.get("pm2_env", {})
            uptime_ms = pm2_env.get("pm_uptime", 0)
            uptime_str = ""
            if uptime_ms:
                secs = int((time.time() * 1000 - uptime_ms) / 1000)
                hours, rem = divmod(secs, 3600)
                mins, secs = divmod(rem, 60)
                uptime_str = f"{hours}h {mins}m"
            services.append({
                "name": p.get("name", "?"),
                "status": pm2_env.get("status", "unknown"),
                "cpu": p.get("monit", {}).get("cpu", 0),
                "memory": round(p.get("monit", {}).get("memory", 0) / 1024 / 1024, 1),
                "uptime": uptime_str,
                "restarts": pm2_env.get("restart_time", 0),
                "pid": p.get("pid", 0),
            })
        return {"services": services}
    except Exception as e:
        return {"services": [], "error": str(e)}


@app.get("/api/feedback-stats")
async def api_feedback_stats():
    """사용자 피드백 통계"""
    fb_file = os.path.expanduser("~/.claude/kg-user-feedback.jsonl")
    stats = {"total": 0, "good": 0, "bad": 0, "recent": [], "by_intent": {}}
    if not os.path.isfile(fb_file):
        return stats
    try:
        entries = []
        with open(fb_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        stats["total"] = len(entries)
        stats["good"] = sum(1 for e in entries if e.get("rating") == "good")
        stats["bad"] = stats["total"] - stats["good"]
        stats["recent"] = entries[-10:]
        for e in entries:
            intent = e.get("context_items", [None])[0] if e.get("context_items") else "unknown"
            rating = e.get("rating", "unknown")
            stats["by_intent"].setdefault(rating, 0)
            stats["by_intent"][rating] = stats["by_intent"].get(rating, 0) + 1
        return stats
    except Exception as e:
        return {**stats, "error": str(e)}


@app.get("/api/context-stats")
async def api_context_stats():
    """컨텍스트 주입 분석 — trigger 로그 기반"""
    log_file = os.path.expanduser("~/.claude/logs/mcp-kg-trigger.log")
    stats = {"total_triggers": 0, "injected": 0, "quality": {"HIGH": 0, "MEDIUM": 0, "LOW": 0, "NONE": 0}, "intents": {}, "recent": []}
    if not os.path.isfile(log_file):
        return stats
    try:
        entries = []
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line:
                    try:
                        entries.append(json.loads(line))
                    except Exception:
                        pass
        stats["total_triggers"] = len(entries)
        stats["injected"] = sum(1 for e in entries if e.get("kg_injected"))
        for e in entries:
            intent = e.get("intent", "unknown")
            stats["intents"][intent] = stats["intents"].get(intent, 0) + 1
        stats["recent"] = entries[-15:]
        # quality breakdown from last_injected file
        inj_file = os.path.expanduser("~/.claude/mcp-kg-analytics/last_injected_identifiers.json")
        if os.path.isfile(inj_file):
            try:
                with open(inj_file, "r") as f:
                    last_inj = json.loads(f.read())
                rel = last_inj.get("relevance", {})
                stats["last_quality"] = rel.get("quality", "N/A")
                stats["last_relevance_pct"] = rel.get("relevance_pct", 0)
                stats["last_summary"] = rel.get("summary", "")
            except Exception:
                pass
        return stats
    except Exception as e:
        return {**stats, "error": str(e)}


@app.get("/api/relationships")
async def api_relationships():
    """관계 타입 분포"""
    d = get_driver()
    with d.session() as s:
        result = s.run("""
            MATCH ()-[r]->()
            WITH type(r) as rel_type, count(r) as cnt
            RETURN rel_type, cnt ORDER BY cnt DESC LIMIT 15
        """).data()
    return {"relationships": result}


@app.get("/api/top-accessed")
async def api_top_accessed():
    """가장 많이 참조된 노드"""
    d = get_driver()
    with d.session() as s:
        result = s.run("""
            MATCH (n)
            WHERE n.access_count IS NOT NULL AND n.access_count > 0
            RETURN n.name as name, labels(n)[0] as type,
                   n.access_count as count,
                   COALESCE(n.namespace, '') as namespace
            ORDER BY n.access_count DESC
            LIMIT 15
        """).data()
    return {"nodes": result}


@app.get("/api/watcher-activity")
async def api_watcher_activity():
    """파일 워처 최근 활동"""
    watched_file = os.path.expanduser("~/.claude/kg-watched-projects.json")
    activity = {"projects": [], "recent_syncs": []}
    if os.path.isfile(watched_file):
        try:
            with open(watched_file, "r") as f:
                data = json.loads(f.read())
            activity["projects"] = data.get("projects", [])
        except Exception:
            pass
    # Recent sync events from sessions log
    sessions_file = os.path.expanduser("~/.claude/mcp-kg-analytics/sessions.jsonl")
    if os.path.isfile(sessions_file):
        try:
            entries = []
            with open(sessions_file, "r", encoding="utf-8") as f:
                for line in f:
                    line = line.strip()
                    if line:
                        try:
                            entries.append(json.loads(line))
                        except Exception:
                            pass
            activity["recent_syncs"] = entries[-10:]
        except Exception:
            pass
    return activity


@app.get("/api/search-quality")
async def api_search_quality():
    """최근 벤치마크 결과 (타입별 분석 포함)"""
    results_dir = Path(__file__).parent.parent.parent / "tests" / "benchmark" / "results"
    if not results_dir.exists():
        return {"benchmarks": []}
    files = sorted(results_dir.glob("benchmark_*.json"), reverse=True)[:5]
    benchmarks = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            modes = {}
            type_analysis = {}
            results_data = data.get("results", {})
            for mode_name, mode_data in results_data.items():
                avg = mode_data.get("avg_metrics", {})
                modes[mode_name] = {
                    "p_at_1": avg.get("P@1", 0),
                    "p_at_3": avg.get("P@3", 0),
                    "p_at_5": avg.get("P@5", 0),
                    "p_at_10": avg.get("P@10", 0),
                    "mrr": avg.get("MRR", 0),
                    "ndcg_5": avg.get("nDCG@5", 0),
                    "hit_1": avg.get("Hit@1", 0),
                    "hit_5": avg.get("Hit@5", 0),
                    "hit_10": avg.get("Hit@10", 0),
                    "elapsed": mode_data.get("elapsed_seconds", 0),
                }
                # Type-level analysis
                tm = mode_data.get("type_metrics", {})
                for qtype, metrics in tm.items():
                    if qtype not in type_analysis:
                        type_analysis[qtype] = {}
                    type_analysis[qtype][mode_name] = {
                        "p_at_1": metrics.get("P@1", 0),
                        "mrr": metrics.get("MRR", 0),
                        "count": metrics.get("count", 0),
                    }
            benchmarks.append({
                "timestamp": data.get("timestamp", ""),
                "total_queries": data.get("total_queries", 0),
                "modes": modes,
                "type_analysis": type_analysis,
            })
        except Exception:
            pass
    return {"benchmarks": benchmarks}


@app.get("/api/graph")
async def api_graph(ns: str = "", center: str = "", limit: int = 150, mode: str = ""):
    """그래프 시각화용 노드+엣지 데이터 (Cytoscape.js 형식)
    mode='all' → 모든 네임스페이스에서 골고루 샘플링
    """
    d = get_driver()
    elements = []

    with d.session() as s:
        target_ns = ns

        # mode=all: 전체 프로젝트 오버뷰
        if mode == "all" or (not target_ns and not center):
            # 각 네임스페이스에서 대표 노드+엣지를 균등 샘플링
            ns_list = s.run("""
                MATCH (n) WHERE n.namespace IS NOT NULL
                WITH n.namespace AS ns, count(n) AS cnt
                RETURN ns, cnt ORDER BY cnt DESC LIMIT 15
            """).data()

            per_ns = max(limit // max(len(ns_list), 1), 5)
            seen_nodes = set()

            for ns_info in ns_list:
                cur_ns = ns_info["ns"]
                # 각 네임스페이스에서 다양한 관계 샘플링
                rows = s.run("""
                    MATCH (a)-[r]->(b)
                    WHERE a.namespace = $ns
                    WITH type(r) AS rtype, collect({a:a, r:r, b:b})[0..4] AS samples
                    UNWIND samples AS s
                    RETURN id(s.a) AS aid, s.a.name AS aname, labels(s.a)[0] AS atype,
                           s.a.namespace AS ans, COALESCE(s.a.module,'') AS amod,
                           type(s.r) AS rel,
                           id(s.b) AS bid, s.b.name AS bname, labels(s.b)[0] AS btype,
                           COALESCE(s.b.namespace, s.a.namespace) AS bns
                    LIMIT $per
                """, ns=cur_ns, per=per_ns).data()

                for row in rows:
                    aid = str(row["aid"])
                    bid = str(row["bid"])
                    if aid not in seen_nodes:
                        seen_nodes.add(aid)
                        elements.append({"data": {"id": aid, "label": row["aname"], "type": row["atype"], "ns": row["ans"] or "", "module": row["amod"]}})
                    if bid not in seen_nodes:
                        seen_nodes.add(bid)
                        elements.append({"data": {"id": bid, "label": row["bname"], "type": row["btype"], "ns": row.get("bns") or ""}})
                    elements.append({"data": {"source": aid, "target": bid, "label": row["rel"]}})

            return {"elements": elements, "namespace": "ALL", "ns_count": len(ns_list)}

        if center:
            # Explore from a specific node
            result = s.run("""
                MATCH (c) WHERE toLower(c.name) = toLower($center)
                AND ($ns = '' OR c.namespace = $ns)
                WITH c LIMIT 1
                OPTIONAL MATCH (c)-[r]->(out)
                WITH c, collect({n: out, r: r, dir: 'out'})[0..20] AS outs
                OPTIONAL MATCH (inc)-[r2]->(c)
                WITH c, outs, collect({n: inc, r: r2, dir: 'in'})[0..20] AS ins
                RETURN c, outs, ins
            """, center=center, ns=target_ns).single()

            if result:
                c = result["c"]
                elements.append({"data": {"id": str(c.element_id), "label": c.get("name", "?"), "type": list(c.labels)[0] if c.labels else "?", "center": True}})
                for item in (result["outs"] or []) + (result["ins"] or []):
                    n = item["n"]
                    r = item["r"]
                    if n is None:
                        continue
                    nid = str(n.element_id)
                    elements.append({"data": {"id": nid, "label": n.get("name", "?"), "type": list(n.labels)[0] if n.labels else "?"}})
                    if item["dir"] == "out":
                        elements.append({"data": {"source": str(c.element_id), "target": nid, "label": r.type if r else "?"}})
                    else:
                        elements.append({"data": {"source": nid, "target": str(c.element_id), "label": r.type if r else "?"}})
        else:
            # Get ALL relationship types, balanced sampling
            result = s.run("""
                MATCH (a)-[r]->(b)
                WHERE a.namespace = $ns
                WITH type(r) AS rtype, collect({a:a, r:r, b:b})[0..$per] AS samples
                UNWIND samples AS s
                RETURN id(s.a) AS aid, s.a.name AS aname, labels(s.a)[0] AS atype,
                       COALESCE(s.a.module, '') AS amod,
                       type(s.r) AS rel,
                       id(s.b) AS bid, s.b.name AS bname, labels(s.b)[0] AS btype,
                       COALESCE(s.b.module, '') AS bmod
            """, ns=target_ns, per=max(limit // 6, 20)).data()

            seen_nodes = set()
            for row in result:
                aid = str(row["aid"])
                bid = str(row["bid"])
                if aid not in seen_nodes:
                    seen_nodes.add(aid)
                    elements.append({"data": {"id": aid, "label": row["aname"], "type": row["atype"], "module": row["amod"]}})
                if bid not in seen_nodes:
                    seen_nodes.add(bid)
                    elements.append({"data": {"id": bid, "label": row["bname"], "type": row["btype"], "module": row["bmod"]}})
                elements.append({"data": {"source": aid, "target": bid, "label": row["rel"]}})

    return {"elements": elements, "namespace": target_ns}


@app.get("/api/growth")
async def api_growth():
    """시스템 성장 타임라인 — 날짜별 노드/활동 증가 추이"""
    d = get_driver()
    result = {}

    with d.session() as s:
        # 날짜별 인덱싱된 노드 수 (indexed_at 기준)
        indexed = s.run("""
            MATCH (n) WHERE n.indexed_at IS NOT NULL
            WITH date(datetime(n.indexed_at)) AS d, count(n) AS cnt
            RETURN toString(d) AS day, cnt
            ORDER BY d
        """).data()
        result["indexed_by_day"] = indexed

        # 네임스페이스별 노드 수 (상위 15)
        ns_data = s.run("""
            MATCH (n) WHERE n.namespace IS NOT NULL
            RETURN n.namespace AS ns, count(n) AS cnt
            ORDER BY cnt DESC LIMIT 15
        """).data()
        result["namespaces"] = ns_data

        # 총 노드/엣지 현재 값
        totals = s.run("""
            MATCH (n) WITH count(n) as nodes
            MATCH ()-[r]->() RETURN nodes, count(r) as edges
        """).single()
        result["total_nodes"] = totals["nodes"] if totals else 0
        result["total_edges"] = totals["edges"] if totals else 0

    # Trigger log에서 일별 활동량
    log_file = os.path.expanduser("~/.claude/logs/mcp-kg-trigger.log")
    daily_activity = {}
    if os.path.isfile(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                try:
                    entry = json.loads(line)
                    ts = entry.get("timestamp", "")[:10]
                    if ts:
                        daily_activity[ts] = daily_activity.get(ts, 0) + 1
                except Exception:
                    pass
    result["daily_activity"] = [{"day": k, "cnt": v} for k, v in sorted(daily_activity.items())]

    return result


@app.get("/api/data-quality")
async def api_data_quality():
    """데이터 품질 대시보드 — 네임스페이스별 커버리지"""
    d = get_driver()
    result = {"overall": {}, "by_namespace": []}
    with d.session() as s:
        # Overall coverage
        overall = s.run("""
            MATCH (n) WHERE n:Function OR n:Class
            WITH count(n) as total,
                 count(CASE WHEN n.file_path IS NOT NULL AND n.file_path <> '' THEN 1 END) as has_file_path,
                 count(CASE WHEN n.code IS NOT NULL AND n.code <> '' THEN 1 END) as has_code,
                 count(CASE WHEN n.ai_description IS NOT NULL AND n.ai_description <> '' THEN 1 END) as has_ai_desc,
                 count(CASE WHEN n.embedding IS NOT NULL THEN 1 END) as has_embedding
            RETURN total, has_file_path, has_code, has_ai_desc, has_embedding
        """).single()
        if overall:
            t = max(overall["total"], 1)
            result["overall"] = {
                "total": overall["total"],
                "file_path": overall["has_file_path"],
                "file_path_pct": round(overall["has_file_path"] / t * 100, 1),
                "code_body": overall["has_code"],
                "code_body_pct": round(overall["has_code"] / t * 100, 1),
                "ai_description": overall["has_ai_desc"],
                "ai_description_pct": round(overall["has_ai_desc"] / t * 100, 1),
                "embedding": overall["has_embedding"],
                "embedding_pct": round(overall["has_embedding"] / t * 100, 1),
            }
            # Quality score: weighted average
            pcts = [result["overall"]["file_path_pct"], result["overall"]["code_body_pct"],
                    result["overall"]["ai_description_pct"], result["overall"]["embedding_pct"]]
            result["overall"]["quality_score"] = round(sum(pcts) / 4, 0)

        # By namespace (top 10)
        ns_data = s.run("""
            MATCH (n) WHERE (n:Function OR n:Class) AND n.namespace IS NOT NULL
            WITH n.namespace as ns,
                 count(n) as total,
                 count(CASE WHEN n.code IS NOT NULL AND n.code <> '' THEN 1 END) as code,
                 count(CASE WHEN n.ai_description IS NOT NULL AND n.ai_description <> '' THEN 1 END) as ai_desc,
                 count(CASE WHEN n.embedding IS NOT NULL THEN 1 END) as embed
            RETURN ns, total, code, ai_desc, embed
            ORDER BY total DESC LIMIT 10
        """).data()
        result["by_namespace"] = [{
            "namespace": r["ns"],
            "total": r["total"],
            "code_pct": round(r["code"] / max(r["total"], 1) * 100, 1),
            "ai_desc_pct": round(r["ai_desc"] / max(r["total"], 1) * 100, 1),
            "embed_pct": round(r["embed"] / max(r["total"], 1) * 100, 1),
        } for r in ns_data]

        # Stale embedding count
        stale = s.run("""
            MATCH (n) WHERE (n:Function OR n:Class)
            AND n.ai_description IS NOT NULL AND n.embedding IS NOT NULL
            AND (n.ai_described_at > n.embedded_at OR n.embedded_at IS NULL)
            RETURN count(n) as cnt
        """).single()
        result["stale_embeddings"] = stale["cnt"] if stale else 0

    return result


@app.get("/api/pipeline-status")
async def api_pipeline_status():
    """자동 파이프라인 상태 — 진행 중인 프로세스 확인"""
    status = {"stages": [], "running": False}
    try:
        r = subprocess.run(["ps", "aux"], capture_output=True, text=True, timeout=3)
        lines = r.stdout.split("\n")
        pipeline_procs = []
        for line in lines:
            if "auto_index_project" in line and "python" in line:
                pipeline_procs.append({"stage": "index+describe+embed", "process": "auto_index_project.py"})
            elif "bulk_ai_describe" in line and "python" in line and "grep" not in line:
                pipeline_procs.append({"stage": "describe", "process": "bulk_ai_describe.py"})
            elif "reembed_enriched" in line and "python" in line and "grep" not in line:
                pipeline_procs.append({"stage": "embed", "process": "reembed_enriched.py"})
            elif "kg-bulk-indexer" in line and "python" in line:
                pipeline_procs.append({"stage": "index", "process": "kg-bulk-indexer.py"})
        status["stages"] = pipeline_procs
        status["running"] = len(pipeline_procs) > 0
    except Exception:
        pass

    # Auto-index log (recent entries)
    log_file = os.path.expanduser("~/.claude/mcp-kg-analytics/auto_index.log")
    log_entries = []
    if os.path.isfile(log_file):
        with open(log_file, "r", encoding="utf-8") as f:
            log_entries = [l.strip() for l in f.readlines()[-10:] if l.strip()]
    status["log"] = log_entries
    return status


@app.get("/api/hook-activity")
async def api_hook_activity():
    """Hook 실행 모니터 — 로그 파일 기반 통계"""
    hooks = {
        "auto-trigger": {"log": "~/.claude/logs/mcp-kg-trigger.log", "calls": 0, "errors": 0},
        "feedback": {"log": "~/.claude/mcp-kg-analytics/feedback-events.jsonl", "calls": 0, "errors": 0},
        "indexer": {"log": "~/.claude/mcp-kg-analytics/incremental-index.log", "calls": 0, "errors": 0},
        "judge": {"log": "~/.claude/kg-judge-log/judge.jsonl", "calls": 0, "errors": 0},
    }
    result = {"hooks": [], "total_calls": 0, "total_errors": 0}
    now = time.time()
    one_hour_ago = now - 3600

    for name, info in hooks.items():
        log_path = os.path.expanduser(info["log"])
        calls_1h = 0
        errors_1h = 0
        total = 0
        if os.path.isfile(log_path):
            try:
                with open(log_path, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        total += 1
                        try:
                            entry = json.loads(line)
                            ts = entry.get("timestamp", 0)
                            if isinstance(ts, str):
                                ts = 0
                            if ts > one_hour_ago:
                                calls_1h += 1
                                if entry.get("error") or entry.get("status") == "error":
                                    errors_1h += 1
                        except (json.JSONDecodeError, TypeError):
                            # non-JSON log line
                            pass
            except Exception:
                pass
        result["hooks"].append({
            "name": name,
            "calls_1h": calls_1h,
            "errors_1h": errors_1h,
            "total": total,
        })
        result["total_calls"] += calls_1h
        result["total_errors"] += errors_1h

    return result


@app.get("/api/benchmark-history")
async def api_benchmark_history():
    """벤치마크 히스토리 — 시간순 트렌드"""
    results_dir = Path(__file__).parent.parent.parent / "tests" / "benchmark" / "results"
    if not results_dir.exists():
        return {"history": []}
    files = sorted(results_dir.glob("benchmark_*.json"))
    history = []
    for f in files:
        try:
            data = json.loads(f.read_text())
            ts = data.get("timestamp", "")
            modes = {}
            for mode_name, mode_data in data.get("results", {}).items():
                avg = mode_data.get("avg_metrics", {})
                modes[mode_name] = {
                    "p_at_1": avg.get("P@1", 0),
                    "mrr": avg.get("MRR", 0),
                    "ndcg_5": avg.get("nDCG@5", 0),
                }
            history.append({"timestamp": ts[:16], "modes": modes})
        except Exception:
            pass
    return {"history": history}


@app.get("/api/cost-tracker")
async def api_cost_tracker():
    """API 비용 추적 — 이번 달 사용량 추정"""
    costs = {
        "voyage_embedding": {"calls": 0, "cost": 0.0, "unit_price": 0.00012},
        "gemini_describe": {"calls": 0, "cost": 0.0, "unit_price": 0.0},  # free tier
        "gemini_judge": {"calls": 0, "cost": 0.0, "unit_price": 0.0},
    }

    # Estimate from Neo4j node counts
    d = get_driver()
    with d.session() as s:
        embedded = s.run("""
            MATCH (n) WHERE (n:Function OR n:Class) AND n.embedding IS NOT NULL
            RETURN count(n) as cnt
        """).single()
        costs["voyage_embedding"]["calls"] = embedded["cnt"] if embedded else 0
        costs["voyage_embedding"]["cost"] = round(costs["voyage_embedding"]["calls"] * 0.00012, 2)

        described = s.run("""
            MATCH (n) WHERE (n:Function OR n:Class) AND n.ai_description IS NOT NULL
            RETURN count(n) as cnt
        """).single()
        costs["gemini_describe"]["calls"] = described["cnt"] if described else 0

    # Judge calls from log
    judge_log = os.path.expanduser("~/.claude/kg-judge-log/judge.jsonl")
    if os.path.isfile(judge_log):
        try:
            with open(judge_log, "r") as f:
                costs["gemini_judge"]["calls"] = sum(1 for line in f if line.strip())
        except Exception:
            pass

    total_cost = sum(c["cost"] for c in costs.values())
    return {"costs": costs, "total_cost": round(total_cost, 2)}


async def broadcast_event(event: Dict):
    """모든 WebSocket 연결에 이벤트 전송"""
    add_event(event)
    for conn in active_connections:
        try:
            await conn.send_json({"type": "event", "data": event})
        except Exception:
            pass
