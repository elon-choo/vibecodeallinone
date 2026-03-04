#!/usr/bin/env python3
"""
MCP Knowledge Graph Server v2.1

Neo4j 지식그래프 기반 코드 컨텍스트 제공 MCP 서버
Claude Code, Cursor, Codex 등 모든 MCP 호환 도구에서 사용 가능

v2.1 업그레이드:
- Prometheus 메트릭 엔드포인트 (/metrics on :9091)
- 구조화된 JSON 로깅 (OpenTelemetry 호환)
- Correlation ID 기반 요청 추적
- Grafana 대시보드 통합 준비

v2.0 업그레이드:
- 하이브리드 검색 (키워드 + 그래프)
- Local/Global 이원화 검색
- 캐싱 시스템
- 연구 기반: GraphRAG 29.17% 향상, Zep 72% 토큰 절감
"""

import asyncio
import signal
import sys
import time
import os
import threading
from pathlib import Path

# MCP Stdout 오염 방어: 모든 print()를 stderr로 리다이렉트
# MCP JSON-RPC는 stdout을 사용하므로 print()가 프로토콜을 깨뜨림
_original_stdout = sys.stdout
sys.stdout = sys.stderr

# 프로젝트 루트 추가
sys.path.insert(0, str(Path(__file__).parent.parent))

from mcp.server import Server
from mcp.server.stdio import stdio_server
import mcp.types as types

from mcp_server.tools.schemas import get_all_tool_schemas
from mcp_server.tools.registry import ComponentRegistry
from mcp_server.tools.handlers import build_dispatch_table


# v2.1: Observability 모듈 임포트
from mcp_server.observability.metrics import (
    get_metrics,
    start_metrics_server,
)
from mcp_server.observability.logger import (
    get_logger as get_structured_logger,
    log_mcp_request,
    log_mcp_response,
)
from mcp_server.observability.dashboard_events import log_tool_call_event
from mcp_server.observability.session_tracker import record_kg_loaded, get_current_session_id

# 로깅 설정 (구조화된 로깅 사용)
logger = get_structured_logger("mcp-kg-server-v2.1")

# 메트릭 인스턴스
metrics = get_metrics()


class KnowledgeGraphServer:
    """MCP 지식그래프 서버 v2.0"""

    def __init__(self):
        self.server = Server("neo4j-knowledge-graph")
        self._registry = ComponentRegistry()
        self._connect_lock = threading.Lock()
        self._setup_handlers()

    async def close(self):
        """Explicitly close the Neo4j driver to release connections."""
        self._registry.close()

    def _connect_neo4j(self):
        """Neo4j 연결 (lazy, thread-safe) — delegates to ComponentRegistry"""
        if self._registry.connected:
            return
        with self._connect_lock:
            if self._registry.connected:
                return
            self._registry.connect()

    def _setup_handlers(self):
        """MCP 핸들러 설정"""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """사용 가능한 도구 목록 — single source of truth in tools/schemas.py"""
            return get_all_tool_schemas()

        # Tool dispatch table — delegates to tools/handlers.py
        self._tool_dispatch = build_dispatch_table(self._registry)

        @self.server.call_tool()
        async def handle_call_tool(
            name: str, arguments: dict
        ) -> list[types.TextContent]:
            """도구 실행 (v2.1: 메트릭 수집 + 구조화 로깅)"""
            self._connect_neo4j()

            # v2.1: 요청 로깅 및 타이머 시작
            start_time = time.perf_counter()
            correlation_id = log_mcp_request(name, arguments)

            try:
                handler = self._tool_dispatch.get(name)
                if handler is None:
                    result = f"Unknown tool: {name}"
                else:
                    result = await handler(arguments)

                # v2.1: 성공 메트릭 기록
                duration = time.perf_counter() - start_time
                duration_ms = duration * 1000
                metrics.requests_total.labels(tool=name, status="success").inc()
                metrics.request_duration.labels(tool=name).observe(duration)
                log_mcp_response(
                    name, "success", duration_ms,
                    result_size=len(result) if isinstance(result, str) else 0,
                    correlation_id=correlation_id
                )

                # v2.3: 대시보드 v1.3 이벤트 로깅
                try:
                    neo4j_driver = None
                    hs = self._registry.hybrid_search
                    if hs and hasattr(hs, 'driver'):
                        neo4j_driver = hs.driver
                    log_tool_call_event(
                        tool_name=name,
                        arguments=arguments,
                        result_text=result if isinstance(result, str) else "",
                        success=True,
                        duration_ms=duration_ms,
                        neo4j_driver=neo4j_driver,
                    )
                except Exception as evt_err:
                    logger.debug(f"Dashboard event logging failed: {evt_err}")

                # v3.0: 세션 추적 - KG 로드 기록
                try:
                    query = arguments.get("query", "") or " ".join(arguments.get("keywords", []))
                    result_len = len(result) if isinstance(result, str) else 0
                    record_kg_loaded(
                        session_id=get_current_session_id(),
                        tool_name=name,
                        query=query,
                        results_count=result_len,
                    )
                except Exception:
                    pass

                return [types.TextContent(type="text", text=result)]

            except Exception as e:
                # v2.1: 에러 메트릭 기록
                duration = time.perf_counter() - start_time
                duration_ms = duration * 1000
                metrics.requests_total.labels(tool=name, status="error").inc()
                metrics.request_duration.labels(tool=name).observe(duration)
                metrics.connection_errors.labels(error_type=type(e).__name__).inc()
                log_mcp_response(
                    name, "error", duration_ms,
                    error=str(e), correlation_id=correlation_id
                )

                # v2.3: 실패 이벤트도 로깅
                try:
                    log_tool_call_event(
                        tool_name=name,
                        arguments=arguments,
                        result_text="",
                        success=False,
                        duration_ms=duration_ms,
                    )
                except Exception:
                    pass

                # Sanitize error message: only expose exception type, not internal details
                error_type = type(e).__name__
                safe_msg = f"오류 발생: {error_type} — 서버 로그를 확인하세요."
                logger.error(f"Tool '{name}' failed: {e}", exc_info=True)
                return [types.TextContent(
                    type="text",
                    text=safe_msg
                )]

    async def run(self):
        """서버 실행"""
        # v2.1: Prometheus 메트릭 서버 시작
        metrics_port = int(os.getenv("MCP_METRICS_PORT", "9091"))
        try:
            start_metrics_server(metrics_port)
            logger.info(f"Prometheus metrics available at http://localhost:{metrics_port}/metrics")
        except Exception as e:
            logger.warning(f"Failed to start metrics server: {e}")

        logger.info("Starting MCP Knowledge Graph Server v2.1...")

        # MCP JSON-RPC가 원래 stdout을 사용할 수 있도록 복원
        sys.stdout = _original_stdout
        async with stdio_server() as (read_stream, write_stream):
            # stdio_server가 스트림을 캡처한 후 다시 stderr로 리다이렉트
            sys.stdout = sys.stderr
            await self.server.run(
                read_stream,
                write_stream,
                self.server.create_initialization_options()
            )


async def main():
    """메인 함수"""
    server = KnowledgeGraphServer()

    # Register signal handlers for graceful shutdown (SIGTERM, SIGINT)
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        loop.add_signal_handler(sig, lambda: asyncio.ensure_future(_shutdown(server, loop)))

    try:
        await server.run()
    finally:
        await server.close()


async def _shutdown(server: KnowledgeGraphServer, loop: asyncio.AbstractEventLoop):
    """Graceful shutdown handler for signals."""
    logger.info("Received shutdown signal, closing server...")
    await server.close()
    loop.stop()


if __name__ == "__main__":
    asyncio.run(main())
