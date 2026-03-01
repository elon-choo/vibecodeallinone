"""
Prometheus 메트릭 수집 모듈

MCP 서버의 핵심 성능 지표를 수집하고 /metrics 엔드포인트로 노출

리서치 기반 메트릭:
- 검색 히트율 (KG Quality Metrics)
- 응답 지연 P50/P95/P99 (MCP Best Practices)
- 캐시 효율 (Neo4j Monitoring)
- 도구 호출 빈도 (MCP Logging)
"""

import time
import threading
from functools import wraps
from typing import Callable, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import dataclass, field
from collections import defaultdict
import json


@dataclass
class MetricValue:
    """개별 메트릭 값"""
    value: float = 0.0
    labels: dict = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """Prometheus Counter 구현"""

    def __init__(self, name: str, description: str, labels: list[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = defaultdict(float)
        self._lock = threading.Lock()

    def labels(self, **kwargs) -> "CounterLabeled":
        return CounterLabeled(self, kwargs)

    def inc(self, value: float = 1.0, labels: dict = None):
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._values[label_key] += value

    def get(self, labels: dict = None) -> float:
        label_key = tuple(sorted((labels or {}).items()))
        return self._values.get(label_key, 0.0)

    def collect(self) -> list[str]:
        """Prometheus 형식으로 출력"""
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} counter"
        ]
        for label_key, value in self._values.items():
            if label_key:
                label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return lines


class CounterLabeled:
    """레이블이 적용된 Counter"""

    def __init__(self, counter: Counter, labels: dict):
        self._counter = counter
        self._labels = labels

    def inc(self, value: float = 1.0):
        self._counter.inc(value, self._labels)


class Gauge:
    """Prometheus Gauge 구현"""

    def __init__(self, name: str, description: str, labels: list[str] = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self._values: dict[tuple, float] = {}
        self._lock = threading.Lock()

    def labels(self, **kwargs) -> "GaugeLabeled":
        return GaugeLabeled(self, kwargs)

    def set(self, value: float, labels: dict = None):
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._values[label_key] = value

    def inc(self, value: float = 1.0, labels: dict = None):
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            self._values[label_key] = self._values.get(label_key, 0.0) + value

    def dec(self, value: float = 1.0, labels: dict = None):
        self.inc(-value, labels)

    def get(self, labels: dict = None) -> float:
        label_key = tuple(sorted((labels or {}).items()))
        return self._values.get(label_key, 0.0)

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} gauge"
        ]
        for label_key, value in self._values.items():
            if label_key:
                label_str = ",".join(f'{k}="{v}"' for k, v in label_key)
                lines.append(f"{self.name}{{{label_str}}} {value}")
            else:
                lines.append(f"{self.name} {value}")
        return lines


class GaugeLabeled:
    """레이블이 적용된 Gauge"""

    def __init__(self, gauge: Gauge, labels: dict):
        self._gauge = gauge
        self._labels = labels

    def set(self, value: float):
        self._gauge.set(value, self._labels)

    def inc(self, value: float = 1.0):
        self._gauge.inc(value, self._labels)

    def dec(self, value: float = 1.0):
        self._gauge.dec(value, self._labels)


class Histogram:
    """Prometheus Histogram 구현"""

    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.075, 0.1, 0.25, 0.5, 0.75, 1.0, 2.5, 5.0, 7.5, 10.0, float('inf'))

    def __init__(self, name: str, description: str, labels: list[str] = None, buckets: tuple = None):
        self.name = name
        self.description = description
        self.label_names = labels or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._values: dict[tuple, dict] = defaultdict(lambda: {
            "buckets": {b: 0 for b in self.buckets},
            "sum": 0.0,
            "count": 0
        })
        self._lock = threading.Lock()

    def labels(self, **kwargs) -> "HistogramLabeled":
        return HistogramLabeled(self, kwargs)

    def observe(self, value: float, labels: dict = None):
        label_key = tuple(sorted((labels or {}).items()))
        with self._lock:
            data = self._values[label_key]
            data["sum"] += value
            data["count"] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    data["buckets"][bucket] += 1

    def time(self, labels: dict = None):
        """컨텍스트 매니저로 시간 측정"""
        return HistogramTimer(self, labels)

    def collect(self) -> list[str]:
        lines = [
            f"# HELP {self.name} {self.description}",
            f"# TYPE {self.name} histogram"
        ]
        for label_key, data in self._values.items():
            label_str = ",".join(f'{k}="{v}"' for k, v in label_key) if label_key else ""

            cumulative = 0
            for bucket, count in sorted(data["buckets"].items()):
                cumulative += count
                if label_str:
                    lines.append(f'{self.name}_bucket{{{label_str},le="{bucket if bucket != float("inf") else "+Inf"}"}} {cumulative}')
                else:
                    lines.append(f'{self.name}_bucket{{le="{bucket if bucket != float("inf") else "+Inf"}"}} {cumulative}')

            if label_str:
                lines.append(f"{self.name}_sum{{{label_str}}} {data['sum']}")
                lines.append(f"{self.name}_count{{{label_str}}} {data['count']}")
            else:
                lines.append(f"{self.name}_sum {data['sum']}")
                lines.append(f"{self.name}_count {data['count']}")

        return lines


class HistogramLabeled:
    """레이블이 적용된 Histogram"""

    def __init__(self, histogram: Histogram, labels: dict):
        self._histogram = histogram
        self._labels = labels

    def observe(self, value: float):
        self._histogram.observe(value, self._labels)

    def time(self):
        return HistogramTimer(self._histogram, self._labels)


class HistogramTimer:
    """Histogram 시간 측정 컨텍스트 매니저"""

    def __init__(self, histogram: Histogram, labels: dict = None):
        self._histogram = histogram
        self._labels = labels
        self._start = None

    def __enter__(self):
        self._start = time.perf_counter()
        return self

    def __exit__(self, *args):
        elapsed = time.perf_counter() - self._start
        self._histogram.observe(elapsed, self._labels)


class MCPMetrics:
    """
    MCP 서버 메트릭 컬렉션

    핵심 메트릭 (리서치 기반):
    - mcp_requests_total: 총 MCP 요청 수
    - mcp_request_duration_seconds: 요청 처리 시간
    - mcp_search_hits_total: 검색 히트 수
    - mcp_search_misses_total: 검색 미스 수
    - mcp_cache_hit_ratio: 캐시 히트율
    - mcp_graph_nodes_total: 지식그래프 노드 수
    - mcp_graph_relations_total: 지식그래프 관계 수
    """

    def __init__(self):
        # 요청 메트릭
        self.requests_total = Counter(
            "mcp_requests_total",
            "Total MCP requests",
            ["tool", "status"]
        )

        self.request_duration = Histogram(
            "mcp_request_duration_seconds",
            "MCP request duration in seconds",
            ["tool"],
            buckets=(0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1.0, 2.5, 5.0, 10.0, float('inf'))
        )

        # 검색 메트릭
        self.search_hits = Counter(
            "mcp_search_hits_total",
            "Total search hits (results found)",
            ["search_type"]
        )

        self.search_misses = Counter(
            "mcp_search_misses_total",
            "Total search misses (no results)",
            ["search_type"]
        )

        self.search_results = Histogram(
            "mcp_search_results_count",
            "Number of search results returned",
            ["search_type"],
            buckets=(0, 1, 2, 5, 10, 20, 50, 100, float('inf'))
        )

        # 캐시 메트릭
        self.cache_hits = Counter(
            "mcp_cache_hits_total",
            "Total cache hits",
            ["cache_type"]
        )

        self.cache_misses = Counter(
            "mcp_cache_misses_total",
            "Total cache misses",
            ["cache_type"]
        )

        self.cache_size = Gauge(
            "mcp_cache_size",
            "Current cache size",
            ["cache_type"]
        )

        # 지식그래프 메트릭
        self.graph_nodes = Gauge(
            "mcp_graph_nodes_total",
            "Total nodes in knowledge graph",
            ["label"]
        )

        self.graph_relations = Gauge(
            "mcp_graph_relations_total",
            "Total relations in knowledge graph",
            ["type"]
        )

        # 품질 메트릭 (리서치 기반)
        self.search_hit_rate = Gauge(
            "mcp_search_hit_rate",
            "Search hit rate (hits / total)",
            ["search_type"]
        )

        self.avg_response_time = Gauge(
            "mcp_avg_response_time_seconds",
            "Average response time",
            ["tool"]
        )

        # 연결 메트릭
        self.active_connections = Gauge(
            "mcp_active_connections",
            "Number of active MCP connections"
        )

        self.connection_errors = Counter(
            "mcp_connection_errors_total",
            "Total connection errors",
            ["error_type"]
        )

        # 수집 대상 메트릭 목록
        self._metrics = [
            self.requests_total,
            self.request_duration,
            self.search_hits,
            self.search_misses,
            self.search_results,
            self.cache_hits,
            self.cache_misses,
            self.cache_size,
            self.graph_nodes,
            self.graph_relations,
            self.search_hit_rate,
            self.avg_response_time,
            self.active_connections,
            self.connection_errors,
        ]

    def collect(self) -> str:
        """모든 메트릭을 Prometheus 형식으로 수집"""
        lines = []
        for metric in self._metrics:
            lines.extend(metric.collect())
            lines.append("")  # 메트릭 간 구분
        return "\n".join(lines)

    def update_graph_stats(self, stats: dict):
        """지식그래프 통계 업데이트"""
        for label, count in stats.get("nodes", {}).items():
            self.graph_nodes.labels(label=label).set(count)
        for rel_type, count in stats.get("relations", {}).items():
            self.graph_relations.labels(type=rel_type).set(count)

    def update_cache_stats(self, stats: dict):
        """캐시 통계 업데이트"""
        for cache_name, cache_stats in stats.items():
            self.cache_size.labels(cache_type=cache_name).set(cache_stats.get("size", 0))
            # 히트율 계산
            hits = cache_stats.get("hits", 0)
            misses = cache_stats.get("misses", 0)
            total = hits + misses
            if total > 0:
                hit_rate = hits / total
                self.search_hit_rate.labels(search_type=cache_name).set(hit_rate)


# 싱글톤 인스턴스
_metrics = MCPMetrics()


def get_metrics() -> MCPMetrics:
    """메트릭 인스턴스 반환"""
    return _metrics


def track_mcp_request(tool: str):
    """MCP 요청 추적 데코레이터"""
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.perf_counter()
            status = "success"
            try:
                result = await func(*args, **kwargs)
                return result
            except Exception as e:
                status = "error"
                raise
            finally:
                duration = time.perf_counter() - start_time
                _metrics.requests_total.labels(tool=tool, status=status).inc()
                _metrics.request_duration.labels(tool=tool).observe(duration)
        return wrapper
    return decorator


def increment_search_counter(search_type: str, hit: bool):
    """검색 결과 카운터 증가"""
    if hit:
        _metrics.search_hits.labels(search_type=search_type).inc()
    else:
        _metrics.search_misses.labels(search_type=search_type).inc()


def record_search_latency(search_type: str, duration: float):
    """검색 지연 시간 기록"""
    _metrics.request_duration.labels(tool=f"search_{search_type}").observe(duration)


def record_search_results(search_type: str, count: int):
    """검색 결과 수 기록"""
    _metrics.search_results.labels(search_type=search_type).observe(count)
    increment_search_counter(search_type, count > 0)


class MetricsHandler(BaseHTTPRequestHandler):
    """Prometheus /metrics 및 Analytics REST 엔드포인트 핸들러"""

    # Analytics 모듈 참조 (lazy import 방지)
    _analytics_module = None

    @classmethod
    def _get_analytics(cls):
        """Analytics 모듈 lazy import"""
        if cls._analytics_module is None:
            from mcp_server.observability import analytics
            cls._analytics_module = analytics
        return cls._analytics_module

    def _send_json(self, data: dict, status: int = 200):
        """JSON 응답 전송 헬퍼"""
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()
        self.wfile.write(json.dumps(data, default=str).encode("utf-8"))

    def do_OPTIONS(self):
        """CORS preflight 처리"""
        self.send_response(204)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")
        self.end_headers()

    def do_GET(self):
        if self.path == "/metrics":
            metrics_output = _metrics.collect()
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; charset=utf-8")
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()
            self.wfile.write(metrics_output.encode("utf-8"))

        elif self.path == "/health":
            self._send_json({"status": "healthy"})

        # ===== Analytics REST Endpoints =====
        elif self.path == "/api/analytics":
            analytics = self._get_analytics()
            summary = analytics.get_analytics_summary()
            self._send_json(summary)

        elif self.path == "/api/quality-report":
            analytics = self._get_analytics()
            quality = analytics.get_quality_metrics()
            report = {
                "entropy": quality.type_distribution_entropy,
                "search_precision": quality.search_precision,
                "search_recall": quality.search_recall,
                "context_relevance": quality.context_relevance,
                "bias_indicators": quality.bias_indicators
            }
            self._send_json(report)

        elif self.path == "/api/reference-timeline":
            analytics = self._get_analytics()
            timeline = analytics.get_reference_timeline(hours=24, interval_minutes=60)
            self._send_json({"timeline": timeline})

        elif self.path.startswith("/api/top-referenced"):
            # Parse limit from query string
            limit = 20
            if "?" in self.path:
                query = self.path.split("?")[1]
                for param in query.split("&"):
                    if param.startswith("limit="):
                        try:
                            limit = int(param.split("=")[1])
                        except:
                            pass
            analytics = self._get_analytics()
            summary = analytics.get_analytics_summary()
            self._send_json({
                "top_referenced": summary.get("top_referenced", [])[:limit],
                "type_distribution": summary.get("type_distribution", {})
            })

        elif self.path == "/api/mcp-stats":
            # MCP 서버 통계 (Prometheus 메트릭 기반)
            stats = {
                "requestsTotal": 0,
                "errorRate": 0,
                "avgLatency": 0,
                "searchHitRate": 0,
                "cacheHitRate": 0,
                "toolUsage": [],
                "latencyHistory": []
            }

            # 요청 총계 계산
            for (labels, value) in _metrics.requests_total._values.items():
                stats["requestsTotal"] += int(value)

            # 에러율 계산
            total_requests = stats["requestsTotal"]
            error_requests = 0
            for (labels, value) in _metrics.requests_total._values.items():
                if any(l[1] == "error" for l in labels):
                    error_requests += value
            if total_requests > 0:
                stats["errorRate"] = error_requests / total_requests

            # 도구 사용 통계
            tool_counts = {}
            for (labels, value) in _metrics.requests_total._values.items():
                for label in labels:
                    if label[0] == "tool":
                        tool = label[1]
                        tool_counts[tool] = tool_counts.get(tool, 0) + int(value)
            stats["toolUsage"] = [
                {"tool": t, "count": c}
                for t, c in sorted(tool_counts.items(), key=lambda x: -x[1])
            ]

            # 검색 히트율
            search_hits = sum(_metrics.search_hits._values.values())
            search_misses = sum(_metrics.search_misses._values.values())
            if search_hits + search_misses > 0:
                stats["searchHitRate"] = search_hits / (search_hits + search_misses)

            # 캐시 히트율
            cache_hits = sum(_metrics.cache_hits._values.values())
            cache_misses = sum(_metrics.cache_misses._values.values())
            if cache_hits + cache_misses > 0:
                stats["cacheHitRate"] = cache_hits / (cache_hits + cache_misses)

            # 평균 레이턴시 (request_duration에서 계산)
            total_duration = 0
            total_count = 0
            for data in _metrics.request_duration._values.values():
                total_duration += data.get("sum", 0)
                total_count += data.get("count", 0)
            if total_count > 0:
                stats["avgLatency"] = (total_duration / total_count) * 1000  # ms

            self._send_json(stats)

        else:
            self.send_response(404)
            self.send_header("Access-Control-Allow-Origin", "*")
            self.end_headers()

    def log_message(self, format, *args):
        pass  # 로그 무시


def start_metrics_server(port: int = 9091):
    """메트릭 서버 시작 (백그라운드 스레드)"""
    server = HTTPServer(("0.0.0.0", port), MetricsHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    return server


def get_metrics_handler():
    """메트릭 핸들러 클래스 반환"""
    return MetricsHandler
