"""
구조화된 로깅 모듈

OpenTelemetry 호환, Correlation ID 지원
리서치 기반: MCP Logging Best Practices

주요 기능:
- JSON 구조화 로깅
- Correlation ID 자동 전파
- MCP 요청/응답 로깅
- 보안 민감 정보 마스킹
"""

import json
import logging
import sys
import time
import uuid
from contextvars import ContextVar
from dataclasses import dataclass, asdict
from datetime import datetime, timezone
from typing import Any, Optional
from functools import wraps


# Correlation ID 컨텍스트 변수
_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="")
_session_id: ContextVar[str] = ContextVar("session_id", default="")
_user_id: ContextVar[str] = ContextVar("user_id", default="")


@dataclass
class LogEntry:
    """구조화된 로그 엔트리"""
    timestamp: str
    level: str
    message: str
    service: str = "mcp-kg-server"
    correlation_id: str = ""
    session_id: str = ""
    user_id: str = ""
    tool: str = ""
    duration_ms: float = 0.0
    status: str = ""
    error: str = ""
    extra: dict = None

    def to_json(self) -> str:
        data = asdict(self)
        # None 및 빈 값 제거
        data = {k: v for k, v in data.items() if v is not None and v != "" and v != {}}
        return json.dumps(data, ensure_ascii=False)


class StructuredFormatter(logging.Formatter):
    """JSON 구조화 포맷터"""

    def __init__(self, service: str = "mcp-kg-server"):
        super().__init__()
        self.service = service

    def format(self, record: logging.LogRecord) -> str:
        entry = LogEntry(
            timestamp=datetime.now(timezone.utc).isoformat(),
            level=record.levelname,
            message=record.getMessage(),
            service=self.service,
            correlation_id=_correlation_id.get(),
            session_id=_session_id.get(),
            user_id=_user_id.get(),
        )

        # 추가 속성 처리
        if hasattr(record, "tool"):
            entry.tool = record.tool
        if hasattr(record, "duration_ms"):
            entry.duration_ms = record.duration_ms
        if hasattr(record, "status"):
            entry.status = record.status
        if hasattr(record, "extra"):
            entry.extra = record.extra

        # 예외 정보
        if record.exc_info:
            entry.error = self.formatException(record.exc_info)

        return entry.to_json()


class CorrelationIdFilter(logging.Filter):
    """Correlation ID 필터"""

    def filter(self, record: logging.LogRecord) -> bool:
        record.correlation_id = _correlation_id.get()
        record.session_id = _session_id.get()
        record.user_id = _user_id.get()
        return True


def get_logger(name: str = "mcp-kg-server") -> logging.Logger:
    """구조화된 로거 생성"""
    logger = logging.getLogger(name)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stderr)
        handler.setFormatter(StructuredFormatter(service=name))
        handler.addFilter(CorrelationIdFilter())
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

    return logger


class correlation_id_context:
    """Correlation ID 컨텍스트 매니저"""

    def __init__(self, correlation_id: str = None, session_id: str = None, user_id: str = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())
        self.session_id = session_id or ""
        self.user_id = user_id or ""
        self._tokens = []

    def __enter__(self):
        self._tokens.append(_correlation_id.set(self.correlation_id))
        if self.session_id:
            self._tokens.append(_session_id.set(self.session_id))
        if self.user_id:
            self._tokens.append(_user_id.set(self.user_id))
        return self

    def __exit__(self, *args):
        for token in reversed(self._tokens):
            if hasattr(token, "old_value"):
                # Python 3.7+ contextvars reset
                pass
        _correlation_id.set("")
        _session_id.set("")
        _user_id.set("")


def get_correlation_id() -> str:
    """현재 Correlation ID 반환"""
    return _correlation_id.get() or str(uuid.uuid4())


def set_correlation_id(cid: str):
    """Correlation ID 설정"""
    _correlation_id.set(cid)


def set_session_id(sid: str):
    """Session ID 설정"""
    _session_id.set(sid)


def set_user_id(uid: str):
    """User ID 설정"""
    _user_id.set(uid)


# 보안 민감 정보 마스킹
SENSITIVE_KEYS = {"password", "secret", "token", "api_key", "apikey", "auth", "credential"}


def mask_sensitive_data(data: dict) -> dict:
    """민감 정보 마스킹"""
    if not isinstance(data, dict):
        return data

    masked = {}
    for key, value in data.items():
        lower_key = key.lower()
        if any(s in lower_key for s in SENSITIVE_KEYS):
            masked[key] = "***MASKED***"
        elif isinstance(value, dict):
            masked[key] = mask_sensitive_data(value)
        else:
            masked[key] = value
    return masked


# MCP 요청/응답 로깅 함수
_logger = get_logger()


def log_mcp_request(tool: str, arguments: dict, correlation_id: str = None):
    """MCP 요청 로깅"""
    cid = correlation_id or get_correlation_id()
    set_correlation_id(cid)

    masked_args = mask_sensitive_data(arguments)

    record = _logger.makeRecord(
        name=_logger.name,
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"MCP Request: {tool}",
        args=(),
        exc_info=None,
    )
    record.tool = tool
    record.status = "request"
    record.extra = {"arguments": masked_args}

    _logger.handle(record)

    return cid


def log_mcp_response(
    tool: str,
    status: str,
    duration_ms: float,
    result_size: int = 0,
    error: str = None,
    correlation_id: str = None
):
    """MCP 응답 로깅"""
    if correlation_id:
        set_correlation_id(correlation_id)

    level = logging.ERROR if error else logging.INFO
    msg = f"MCP Response: {tool}" if not error else f"MCP Error: {tool}"

    record = _logger.makeRecord(
        name=_logger.name,
        level=level,
        fn="",
        lno=0,
        msg=msg,
        args=(),
        exc_info=None,
    )
    record.tool = tool
    record.status = status
    record.duration_ms = duration_ms
    record.extra = {"result_size": result_size}

    if error:
        record.extra["error"] = error

    _logger.handle(record)


def log_search_event(
    search_type: str,
    query: str,
    results_count: int,
    duration_ms: float,
    cache_hit: bool = False
):
    """검색 이벤트 로깅"""
    record = _logger.makeRecord(
        name=_logger.name,
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"Search: {search_type}",
        args=(),
        exc_info=None,
    )
    record.tool = f"search_{search_type}"
    record.status = "hit" if results_count > 0 else "miss"
    record.duration_ms = duration_ms
    record.extra = {
        "query": query[:100],  # 쿼리 길이 제한
        "results_count": results_count,
        "cache_hit": cache_hit,
    }

    _logger.handle(record)


def log_cache_event(cache_type: str, operation: str, hit: bool = None, size: int = None):
    """캐시 이벤트 로깅"""
    record = _logger.makeRecord(
        name=_logger.name,
        level=logging.DEBUG,
        fn="",
        lno=0,
        msg=f"Cache {operation}: {cache_type}",
        args=(),
        exc_info=None,
    )
    record.extra = {"cache_type": cache_type, "operation": operation}
    if hit is not None:
        record.extra["hit"] = hit
    if size is not None:
        record.extra["size"] = size

    _logger.handle(record)


def log_graph_event(operation: str, node_type: str = None, count: int = None):
    """그래프 이벤트 로깅"""
    record = _logger.makeRecord(
        name=_logger.name,
        level=logging.INFO,
        fn="",
        lno=0,
        msg=f"Graph {operation}",
        args=(),
        exc_info=None,
    )
    record.extra = {"operation": operation}
    if node_type:
        record.extra["node_type"] = node_type
    if count is not None:
        record.extra["count"] = count

    _logger.handle(record)


# 데코레이터
def log_execution(tool_name: str = None):
    """실행 로깅 데코레이터"""
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            name = tool_name or func.__name__
            start_time = time.perf_counter()
            cid = log_mcp_request(name, kwargs)

            try:
                result = await func(*args, **kwargs)
                duration_ms = (time.perf_counter() - start_time) * 1000

                result_size = len(result) if isinstance(result, str) else 0
                log_mcp_response(name, "success", duration_ms, result_size, correlation_id=cid)

                return result
            except Exception as e:
                duration_ms = (time.perf_counter() - start_time) * 1000
                log_mcp_response(name, "error", duration_ms, error=str(e), correlation_id=cid)
                raise

        return wrapper
    return decorator
