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
import io
import json
import logging
import sys
import time
import os
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

from mcp_server.config import config
from mcp_server.pipeline.graph_search import GraphSearcher
from mcp_server.pipeline.context_builder import ContextBuilder, SimpleReranker
from mcp_server.pipeline.query_router import QueryRouter
from mcp_server.pipeline.hybrid_search import HybridSearchEngine
from mcp_server.pipeline.cache import query_cache, context_cache, get_cache_stats
from mcp_server.pipeline.write_back import GraphWriteBack
from mcp_server.pipeline.impact_simulator import ImpactSimulator
from mcp_server.pipeline.weight_learner import NodeWeightLearner
from mcp_server.pipeline.adaptive_context import ConversationMemory
from mcp_server.pipeline.bug_radar import BugRadar
from mcp_server.pipeline.auto_test_gen import AutoTestGenerator
from mcp_server.pipeline.ontology_evolver import OntologyEvolver
from mcp_server.pipeline.knowledge_transfer import KnowledgeTransfer
from mcp_server.pipeline.llm_judge import LLMJudge
from mcp_server.pipeline.vector_search import VectorSearchEngine
from mcp_server.pipeline.rag_engine import RAGEngine
from mcp_server.pipeline.doc_generator import DocGenerator
from mcp_server.pipeline.shared_memory import SharedMemoryPool
from mcp_server.pipeline.code_assist import CodeAssist


# v2.1: Observability 모듈 임포트
from mcp_server.observability.metrics import (
    get_metrics,
    start_metrics_server,
    record_search_results,
)
from mcp_server.observability.logger import (
    get_logger as get_structured_logger,
    log_mcp_request,
    log_mcp_response,
    log_search_event,
    correlation_id_context,
)
from mcp_server.observability.analytics import (
    track_node_references_batch,
    get_analytics_summary,
    get_reference_timeline,
    get_quality_metrics,
    update_neo4j_access_count,
    get_neo4j_recently_accessed,
    get_neo4j_top_accessed,
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
        self.searcher = None
        self.builder = ContextBuilder(max_tokens=config.max_tokens)
        self.reranker = SimpleReranker()

        # v2 컴포넌트
        self.query_router = QueryRouter()
        self.hybrid_search = None
        self.write_back = None
        self.impact_simulator = None
        self.weight_learner = None
        self.bug_radar = None
        self.llm_judge = None
        self.vector_search_engine = None
        self.rag_engine = None
        self.doc_generator = None
        self.shared_memory = None
        self.code_assist = None

        self._setup_handlers()

    def _connect_neo4j(self):
        """Neo4j 연결 (lazy)"""
        if self.searcher is None:
            try:
                from neo4j import GraphDatabase

                self.searcher = GraphSearcher(
                    config.neo4j_uri,
                    config.neo4j_user,
                    config.neo4j_password
                )

                # v2: 하이브리드 검색 엔진 초기화
                driver = GraphDatabase.driver(
                    config.neo4j_uri,
                    auth=(config.neo4j_user, config.neo4j_password)
                )
                self.hybrid_search = HybridSearchEngine(driver)
                self.write_back = GraphWriteBack(driver)
                self.impact_simulator = ImpactSimulator(driver)
                self.weight_learner = NodeWeightLearner(driver)
                self.bug_radar = BugRadar(driver)
                self.auto_test_gen = AutoTestGenerator(driver)
                self.ontology_evolver = OntologyEvolver(driver)
                self.knowledge_transfer = KnowledgeTransfer(driver)
                self.llm_judge = LLMJudge(driver)
                self.vector_search_engine = VectorSearchEngine(driver)
                self.rag_engine = RAGEngine(driver)
                self.doc_generator = DocGenerator(driver)
                self.shared_memory = SharedMemoryPool(driver)
                self.code_assist = CodeAssist(driver)

                # H-6: B-Tree 인덱스 자동 생성 (MERGE 성능 최적화)
                self._ensure_neo4j_indexes(driver)

                logger.info("Neo4j connected successfully (v2)")
            except Exception as e:
                logger.error(f"Neo4j connection failed: {e}")

    @staticmethod
    def _ensure_neo4j_indexes(driver):
        """Neo4j B-Tree 인덱스 자동 생성. MERGE on (name, file_path) 성능 보장."""
        index_queries = [
            "CREATE INDEX IF NOT EXISTS FOR (f:Function) ON (f.name, f.file_path)",
            "CREATE INDEX IF NOT EXISTS FOR (c:Class) ON (c.name, c.file_path)",
            "CREATE INDEX IF NOT EXISTS FOR (fi:File) ON (fi.path)",
        ]
        try:
            with driver.session() as session:
                for query in index_queries:
                    session.run(query)
            logger.info("Neo4j indexes verified/created (Function, Class, File)")
        except Exception as e:
            logger.warning(f"Neo4j index creation failed (non-fatal): {e}")

    def _setup_handlers(self):
        """MCP 핸들러 설정"""

        @self.server.list_tools()
        async def handle_list_tools() -> list[types.Tool]:
            """사용 가능한 도구 목록"""
            return [
                types.Tool(
                    name="search_knowledge",
                    description="지식그래프에서 코드, 패턴, 보안 정보 검색. 함수명, 클래스명, 패턴명, 키워드로 검색 가능.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "검색 쿼리 (함수명, 클래스명, 패턴명, 키워드)"
                            },
                            "type": {
                                "type": "string",
                                "enum": ["code", "pattern", "all"],
                                "description": "검색 타입: code(코드만), pattern(패턴만), all(전체)",
                                "default": "all"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "최대 결과 수",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_function_context",
                    description="함수의 상세 컨텍스트 조회: 호출 관계, 소속 클래스, 관련 패턴",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "function_name": {
                                "type": "string",
                                "description": "함수 이름"
                            }
                        },
                        "required": ["function_name"]
                    }
                ),
                types.Tool(
                    name="get_module_structure",
                    description="모듈의 구조 조회: 클래스, 함수, 의존성",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "module_name": {
                                "type": "string",
                                "description": "모듈 이름 (예: src.caching.redis_cache)"
                            }
                        },
                        "required": ["module_name"]
                    }
                ),
                types.Tool(
                    name="get_security_patterns",
                    description="보안 패턴과 AI 코드 취약점 정보 조회",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="get_graph_stats",
                    description="지식그래프 전체 통계 조회",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="smart_context",
                    description="현재 작업에 필요한 최적 컨텍스트 자동 구성. 여러 키워드를 조합하여 관련 코드, 패턴, 보안 정보를 한번에 제공.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "keywords": {
                                "type": "array",
                                "items": {"type": "string"},
                                "description": "검색할 키워드 목록"
                            },
                            "current_file": {
                                "type": "string",
                                "description": "현재 작업 중인 파일 경로 (선택)"
                            },
                            "max_tokens": {
                                "type": "integer",
                                "description": "최대 토큰 수",
                                "default": 4000
                            }
                        },
                        "required": ["keywords"]
                    }
                ),
                # ===== v2.0 신규 도구 =====
                types.Tool(
                    name="hybrid_search",
                    description="하이브리드 검색 (키워드 + 그래프). Local/Global 자동 라우팅으로 최적 검색. GraphRAG 29.17% 성능 향상.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "검색 쿼리"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "최대 결과 수",
                                "default": 10
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_call_graph",
                    description="함수 호출 그래프 조회. 해당 함수가 호출하는/호출받는 함수 관계 시각화.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "function_name": {
                                "type": "string",
                                "description": "함수 이름"
                            },
                            "depth": {
                                "type": "integer",
                                "description": "탐색 깊이 (1-4)",
                                "default": 2
                            }
                        },
                        "required": ["function_name"]
                    }
                ),
                types.Tool(
                    name="get_similar_code",
                    description="유사 코드 검색. docstring 기반으로 비슷한 기능의 함수 찾기.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "찾고자 하는 기능 설명"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "최대 결과 수",
                                "default": 5
                            }
                        },
                        "required": ["query"]
                    }
                ),
                types.Tool(
                    name="get_cache_stats",
                    description="캐시 통계 조회. 히트율, 캐시 크기, 성능 메트릭.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                # ===== v2.2 분석 도구 =====
                types.Tool(
                    name="get_analytics_summary",
                    description="지식그래프 사용 분석 요약. 참조 빈도, 품질 메트릭, 편향 지표.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                types.Tool(
                    name="get_top_referenced",
                    description="가장 많이 참조된 지식 노드 조회. 어떤 코드/패턴이 자주 사용되는지 확인.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {
                                "type": "integer",
                                "description": "최대 결과 수",
                                "default": 20
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_recent_activity",
                    description="최근 참조/변경된 노드 조회. 지식그래프 활동 추적.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "hours": {
                                "type": "integer",
                                "description": "조회 기간 (시간)",
                                "default": 24
                            }
                        }
                    }
                ),
                types.Tool(
                    name="get_quality_report",
                    description="지식그래프 품질 리포트. 편향 감지, 컨텍스트 정확도, 분포 균형 분석.",
                    inputSchema={
                        "type": "object",
                        "properties": {}
                    }
                ),
                # ===== Phase 5.5: Ontology Evolver =====
                types.Tool(
                    name="evolve_ontology",
                    description="지식그래프 자가 치유. Orphan/God Module/순환 의존성/Stale 노드/Schema Drift 감지 및 자동 수정.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "auto_fix": {
                                "type": "boolean",
                                "description": "True이면 orphan 삭제, stale 아카이브 자동 수행",
                                "default": False,
                            }
                        }
                    }
                ),
                # ===== Phase 5.6: Knowledge Transfer =====
                types.Tool(
                    name="promote_pattern",
                    description="검증된 패턴을 GLOBAL namespace로 승격. 다른 프로젝트에서도 참조 가능하게 됨.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "name": {"type": "string", "description": "승격할 노드 이름"}
                        },
                        "required": ["name"]
                    }
                ),
                types.Tool(
                    name="get_global_insights",
                    description="모든 프로젝트에서 축적된 글로벌 인사이트. 검증된 패턴, 승격 후보, 안티패턴 조회.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "limit": {"type": "integer", "default": 10}
                        }
                    }
                ),
                # ===== Phase 5.4: Auto Test Generator =====
                types.Tool(
                    name="suggest_tests",
                    description="함수에 대한 테스트 스켈레톤을 지식그래프 기반으로 자동 생성. 시그니처, 의존성 mock, 엣지 케이스를 포함.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "function_name": {
                                "type": "string",
                                "description": "테스트를 생성할 함수 이름"
                            }
                        },
                        "required": ["function_name"]
                    }
                ),
                # ===== Phase 5.3: Predictive Bug Radar =====
                types.Tool(
                    name="get_bug_hotspots",
                    description="버그 핫스팟 감지. 자주 수정되고 의존성이 높은 위험한 코드 지점을 Risk 점수와 함께 반환.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "top_k": {
                                "type": "integer",
                                "description": "반환할 핫스팟 수 (기본 10)",
                                "default": 10,
                            }
                        }
                    }
                ),
                # ===== Phase 5.2: Adaptive Context =====
                types.Tool(
                    name="get_session_context",
                    description="현재 대화 세션의 누적 컨텍스트 요약. 언급된 엔티티, Intent 흐름, 집중 범위, 중복 방지 정보를 제공.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "reset": {
                                "type": "boolean",
                                "description": "True이면 대화 상태를 초기화",
                                "default": False,
                            }
                        }
                    }
                ),
                # ===== Phase 6.6: LLM-as-Judge =====
                types.Tool(
                    name="evaluate_code",
                    description="AI 코드 품질 평가. Gemini Flash로 코드의 정확성, 보안, 가독성, 테스트 가능성을 1-5점으로 평가.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "file_path": {
                                "type": "string",
                                "description": "평가할 파일 경로"
                            },
                            "code_snippet": {
                                "type": "string",
                                "description": "평가할 코드 스니펫 (file_path 대신 직접 코드 전달)"
                            }
                        }
                    }
                ),
                # ===== Phase 6.2: Semantic Vector Search =====
                types.Tool(
                    name="semantic_search",
                    description="의미 기반 벡터 검색. 자연어 쿼리로 유사한 기능의 코드를 찾습니다. '비동기 파일 읽기', '데이터베이스 연결 관리' 같은 자연어 검색 가능.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "query": {
                                "type": "string",
                                "description": "자연어 검색 쿼리 (예: '비동기 파일 읽기', 'error handling pattern')"
                            },
                            "limit": {
                                "type": "integer",
                                "description": "최대 결과 수",
                                "default": 10
                            },
                            "threshold": {
                                "type": "number",
                                "description": "코사인 유사도 임계값 (0.0~1.0, 기본 0.7)",
                                "default": 0.7
                            }
                        },
                        "required": ["query"]
                    }
                ),
                # ===== Phase 7.1: RAG Answer Engine =====
                types.Tool(
                    name="ask_codebase",
                    description="코드베이스에 대한 자연어 질문에 답변. 관련 함수/클래스를 검색하고 종합하여 자연어로 설명합니다.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "question": {
                                "type": "string",
                                "description": "코드베이스에 대한 질문 (예: '인증 흐름을 설명해줘', '캐시 전략은?')"
                            },
                            "max_context_tokens": {
                                "type": "integer",
                                "description": "컨텍스트 최대 토큰 수 (기본 6000)",
                                "default": 6000
                            }
                        },
                        "required": ["question"]
                    }
                ),
                # ===== Phase 7.7: Shared Memory Pool =====
                types.Tool(
                    name="get_shared_context",
                    description="세션 간 공유 컨텍스트 조회. 다른 세션이 발행한 정보(버그, 작업 파일, 변경사항)를 확인.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_dir": {"type": "string", "description": "프로젝트 디렉토리 필터", "default": ""},
                            "keys": {
                                "type": "array", "items": {"type": "string"},
                                "description": "조회할 키 목록 (비면 전체)"
                            }
                        }
                    }
                ),
                types.Tool(
                    name="publish_context",
                    description="세션 간 컨텍스트 공유. 발견한 버그, 작업 중인 파일, 중요 변경사항을 다른 세션에 알림.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "key": {"type": "string", "description": "공유 키 (예: 'found_bug', 'active_file:path')"},
                            "value": {"type": "string", "description": "공유할 값"}
                        },
                        "required": ["key", "value"]
                    }
                ),
                # ===== Phase 7.4: Graph-Driven API Docs Generator =====
                types.Tool(
                    name="generate_docs",
                    description="모듈/프로젝트의 API 문서를 지식그래프 기반으로 자동 생성. Mermaid 다이어그램 포함.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "module_name": {
                                "type": "string",
                                "description": "모듈 이름 ('*'이면 전체 프로젝트 인덱스)"
                            },
                            "depth": {
                                "type": "integer",
                                "description": "문서화 깊이 (1=개요만, 2=상세, 3=풀)",
                                "default": 2
                            }
                        },
                        "required": ["module_name"]
                    }
                ),
                # ===== Phase 7.2: Context-Aware Code Assist =====
                types.Tool(
                    name="assist_code",
                    description="KG 기반 코드 수정 제안. 대상 함수의 호출 관계와 유사 코드를 분석하여 수정된 코드를 생성.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "target_function": {
                                "type": "string",
                                "description": "수정할 함수 이름"
                            },
                            "instruction": {
                                "type": "string",
                                "description": "수정 지시 (예: '에러 핸들링 추가', '캐시 로직 적용', '타입 힌트 추가')"
                            }
                        },
                        "required": ["target_function", "instruction"]
                    }
                ),
                # ===== Phase 8.2: Auto-Index Project =====
                types.Tool(
                    name="index_project",
                    description="프로젝트 전체를 지식그래프에 인덱싱. 모든 코드 파일(.py/.js/.ts/.jsx/.tsx)을 파싱하여 Neo4j에 저장하고 임베딩. git clone 직후 사용 권장.",
                    inputSchema={
                        "type": "object",
                        "properties": {
                            "project_path": {
                                "type": "string",
                                "description": "인덱싱할 프로젝트의 루트 디렉토리 경로"
                            },
                            "no_embed": {
                                "type": "boolean",
                                "description": "True이면 임베딩을 건너뜀 (인덱싱만 수행)",
                                "default": False
                            }
                        },
                        "required": ["project_path"]
                    }
                ),
            ]

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
                if name == "search_knowledge":
                    result = await self._search_knowledge(arguments)
                elif name == "get_function_context":
                    result = await self._get_function_context(arguments)
                elif name == "get_module_structure":
                    result = await self._get_module_structure(arguments)
                elif name == "get_security_patterns":
                    result = await self._get_security_patterns()
                elif name == "get_graph_stats":
                    result = await self._get_graph_stats()
                elif name == "smart_context":
                    result = await self._smart_context(arguments)
                # v2.0 신규 도구
                elif name == "hybrid_search":
                    result = await self._hybrid_search(arguments)
                elif name == "get_call_graph":
                    result = await self._get_call_graph(arguments)
                elif name == "get_similar_code":
                    result = await self._get_similar_code(arguments)
                elif name == "get_cache_stats":
                    result = await self._get_cache_stats_v2()
                # v2.2 분석 도구
                elif name == "get_analytics_summary":
                    result = await self._get_analytics_summary()
                elif name == "get_top_referenced":
                    result = await self._get_top_referenced(arguments)
                elif name == "get_recent_activity":
                    result = await self._get_recent_activity(arguments)
                
                
                
                elif name == "get_session_context":
                    result = await self._get_session_context(arguments)

                elif name == "evolve_ontology":
                    result = await self._evolve_ontology(arguments)

                elif name == "promote_pattern":
                    result = await self._promote_pattern(arguments)

                elif name == "get_global_insights":
                    result = await self._get_global_insights(arguments)

                elif name == "suggest_tests":
                    result = await self._suggest_tests(arguments)

                elif name == "get_bug_hotspots":
                    result = await self._get_bug_hotspots(arguments)

                elif name == "provide_feedback":
                    result_text = await self._provide_feedback(arguments)
                    log_search_event(name, arguments, "weight_learner", len(result_text), time.perf_counter() - start_time)

                elif name == "simulate_impact":
                    result_text = await self._simulate_impact(arguments)
                    log_search_event(name, arguments, "impact_simulator", len(result_text), time.perf_counter() - start_time)

                elif name == "sync_incremental":
                    result_text = await self._sync_incremental(arguments)
                    log_search_event(name, arguments, "write_back", len(result_text), time.perf_counter() - start_time)

                elif name == "evaluate_code":
                    result = await self._evaluate_code(arguments)

                elif name == "semantic_search":
                    result = await self._semantic_search(arguments)

                elif name == "ask_codebase":
                    result = await self._ask_codebase(arguments)

                elif name == "generate_docs":
                    result = await self._generate_docs(arguments)

                elif name == "assist_code":
                    result = await self._assist_code(arguments)

                elif name == "get_shared_context":
                    result = await self._get_shared_context(arguments)

                elif name == "publish_context":
                    result = await self._publish_context(arguments)

                elif name == "get_quality_report":
                    result = await self._get_quality_report()

                elif name == "index_project":
                    result = await self._index_project(arguments)
                else:
                    result = f"Unknown tool: {name}"

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
                    if self.hybrid_search and hasattr(self.hybrid_search, 'driver'):
                        neo4j_driver = self.hybrid_search.driver
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

                return [types.TextContent(
                    type="text",
                    text=f"오류 발생: {str(e)}"
                )]

    async def _search_knowledge(self, args: dict) -> str:
        """지식그래프 검색"""
        query = args.get("query", "")
        search_type = args.get("type", "all")
        limit = args.get("limit", 10)

        if search_type == "code":
            results = self.searcher.search_code(query, limit * 2)
        elif search_type == "pattern":
            results = self.searcher.search_patterns(query, limit * 2)
        else:
            results = self.searcher.search_all(query, limit * 2)

        # 리랭킹
        reranked = self.reranker.rerank(query, results, limit)

        # v2.2: 참조 추적
        track_node_references_batch(reranked, "search_knowledge", query)

        # 컨텍스트 빌드
        context = self.builder.build(reranked, query)

        return context

    async def _get_function_context(self, args: dict) -> str:
        """함수 컨텍스트 조회"""
        func_name = args.get("function_name", "")
        func_data = self.searcher.get_function_context(func_name)

        # v2.2: 참조 추적
        if func_data:
            track_node_references_batch(
                [{"name": func_name, "type": "Function", **func_data}],
                "get_function_context",
                func_name
            )

        return self.builder.build_function_context(func_data)

    async def _get_module_structure(self, args: dict) -> str:
        """모듈 구조 조회"""
        module_name = args.get("module_name", "")
        module_data = self.searcher.get_module_structure(module_name)
        return self.builder.build_module_context(module_data)

    async def _get_security_patterns(self) -> str:
        """보안 패턴 조회"""
        security_data = self.searcher.get_security_recommendations()
        return self.builder._build_security_section(security_data)

    async def _get_graph_stats(self) -> str:
        """그래프 통계"""
        stats = self.searcher.get_graph_stats()

        lines = ["# 지식그래프 통계\n"]

        lines.append("## 노드")
        for label, count in stats.get('nodes', {}).items():
            lines.append(f"- {label}: {count}개")
        lines.append(f"- **총계: {stats.get('total_nodes', 0)}개**")

        lines.append("\n## 관계")
        for rel_type, count in stats.get('relations', {}).items():
            lines.append(f"- {rel_type}: {count}개")
        lines.append(f"- **총계: {stats.get('total_relations', 0)}개**")

        return "\n".join(lines)

    async def _smart_context(self, args: dict) -> str:
        """스마트 컨텍스트 생성"""
        keywords = args.get("keywords", [])
        max_tokens = args.get("max_tokens", 4000)

        if not keywords:
            return "키워드를 입력해주세요."

        all_results = []

        # 각 키워드로 검색
        for keyword in keywords:
            code_results = self.searcher.search_code(keyword, 5)
            pattern_results = self.searcher.search_patterns(keyword, 3)
            all_results.extend(code_results)
            all_results.extend(pattern_results)

        # 중복 제거
        seen = set()
        unique_results = []
        for r in all_results:
            key = (r.get('name'), r.get('type'))
            if key not in seen:
                seen.add(key)
                unique_results.append(r)

        # 리랭킹 (모든 키워드 결합)
        combined_query = " ".join(keywords)
        reranked = self.reranker.rerank(combined_query, unique_results, 15)

        # v2.2: 참조 추적
        track_node_references_batch(reranked, "smart_context", combined_query)

        # 컨텍스트 빌드
        self.builder.max_tokens = max_tokens
        context = self.builder.build(reranked, combined_query)

        # 키워드 요약 추가
        header = f"# 스마트 컨텍스트\n키워드: {', '.join(keywords)}\n결과: {len(reranked)}개\n\n"

        return header + context

    # ===== v2.0 신규 메서드 =====

    async def _hybrid_search(self, args: dict) -> str:
        """하이브리드 검색 (v2)"""
        query = args.get("query", "")
        limit = args.get("limit", 10)

        # 캐시 확인
        cache_key = f"hybrid:{query}:{limit}"
        cached = query_cache.get(cache_key)
        if cached:
            return cached

        # 검색 전략 결정 (Local/Global/Hybrid)
        strategy = self.query_router.get_search_strategy(query)

        # 하이브리드 검색 실행
        results = self.hybrid_search.search(query, strategy, limit)

        # 결과 포맷팅
        lines = [
            f"# 하이브리드 검색 결과",
            f"쿼리: {query}",
            f"모드: {strategy['intent']} (신뢰도: {strategy['confidence']:.1%})",
            f"결과: {len(results)}개\n"
        ]

        for i, item in enumerate(results, 1):
            item_type = item.get("type", "Unknown")
            name = item.get("name", "N/A")
            lines.append(f"## {i}. [{item_type}] {name}")

            if item_type in ("Function", "Class"):
                if item.get("qname"):
                    lines.append(f"- 경로: `{item['qname']}`")
                if item.get("doc"):
                    lines.append(f"- 설명: {item['doc'][:100]}...")
                if item.get("calls"):
                    lines.append(f"- 호출: {', '.join(item['calls'])}")
                if item.get("called_by"):
                    lines.append(f"- 호출자: {', '.join(item['called_by'])}")
            elif item_type == "Module":
                if item.get("path"):
                    lines.append(f"- 경로: `{item['path']}`")
                if item.get("classes"):
                    lines.append(f"- 클래스: {', '.join(item['classes'])}")
                if item.get("functions"):
                    lines.append(f"- 함수: {', '.join(item['functions'])}")
            elif item_type == "Statistics":
                for k, v in item.get("data", {}).items():
                    lines.append(f"- {k}: {v}")
            else:
                if item.get("description"):
                    lines.append(f"- 설명: {item['description']}")

            lines.append("")

        result = "\n".join(lines)

        # 캐시 저장
        query_cache.set(cache_key, result)

        # v2.2: 참조 추적
        track_node_references_batch(results, "hybrid_search", query)

        # Neo4j access_count 업데이트
        if self.hybrid_search and self.hybrid_search.driver:
            for item in results[:5]:  # 상위 5개만
                update_neo4j_access_count(
                    self.hybrid_search.driver,
                    item.get("name", ""),
                    item.get("type", "Function")
                )

        return result

    async def _get_call_graph(self, args: dict) -> str:
        """함수 호출 그래프 조회 (v2)"""
        func_name = args.get("function_name", "")
        depth = min(args.get("depth", 2), 4)  # 최대 4

        # 캐시 확인
        cache_key = f"callgraph:{func_name}:{depth}"
        cached = context_cache.get(cache_key)
        if cached:
            return cached

        graph_data = self.hybrid_search.get_call_graph(func_name, depth)

        lines = [
            f"# 함수 호출 그래프: {func_name}",
            f"탐색 깊이: {depth}\n"
        ]

        # 호출하는 함수들
        outgoing = graph_data.get("outgoing", [])
        lines.append(f"## 호출하는 함수 ({len(outgoing)}개)")
        for item in outgoing:
            path = " → ".join(item.get("path", []))
            lines.append(f"- {path}")

        lines.append("")

        # 호출받는 함수들
        incoming = graph_data.get("incoming", [])
        lines.append(f"## 호출받는 함수 ({len(incoming)}개)")
        for item in incoming:
            path = " → ".join(item.get("path", []))
            lines.append(f"- {path}")

        result = "\n".join(lines)

        # 캐시 저장
        context_cache.set(cache_key, result)

        return result

    async def _get_similar_code(self, args: dict) -> str:
        """유사 코드 검색 (v2)"""
        query = args.get("query", "")
        limit = args.get("limit", 5)

        # 캐시 확인
        cache_key = f"similar:{query}:{limit}"
        cached = query_cache.get(cache_key)
        if cached:
            return cached

        results = self.hybrid_search.get_similar_code(query, limit)

        lines = [
            f"# 유사 코드 검색",
            f"쿼리: {query}",
            f"결과: {len(results)}개\n"
        ]

        for i, item in enumerate(results, 1):
            lines.append(f"## {i}. {item.get('name', 'N/A')}")
            if item.get("qname"):
                lines.append(f"- 경로: `{item['qname']}`")
            if item.get("doc"):
                lines.append(f"- 설명: {item['doc']}")
            if item.get("module"):
                lines.append(f"- 모듈: {item['module']}")
            lines.append(f"- 매칭 점수: {item.get('match_score', 0)}")
            lines.append("")

        result = "\n".join(lines)

        # 캐시 저장
        query_cache.set(cache_key, result)

        return result

    async def _get_cache_stats_v2(self) -> str:
        """캐시 통계 (v2)"""
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

    # ===== v2.2 분석 메서드 =====

    async def _get_analytics_summary(self) -> str:
        """분석 요약"""
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

    async def _get_top_referenced(self, args: dict) -> str:
        """가장 많이 참조된 노드"""
        limit = args.get('limit', 20)

        # 로컬 분석 데이터
        summary = get_analytics_summary()
        local_top = summary.get('top_referenced', [])[:limit]

        # Neo4j에서도 조회 (access_count 기반)
        neo4j_top = []
        if self.hybrid_search and self.hybrid_search.driver:
            neo4j_top = get_neo4j_top_accessed(self.hybrid_search.driver, limit)

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

    async def _get_recent_activity(self, args: dict) -> str:
        """최근 활동"""
        hours = args.get('hours', 24)

        lines = [f"# 최근 {hours}시간 지식그래프 활동\n"]

        # Neo4j에서 최근 접근 노드
        if self.hybrid_search and self.hybrid_search.driver:
            recent = get_neo4j_recently_accessed(self.hybrid_search.driver, 20)
            lines.append("## 최근 접근된 노드")
            for item in recent[:10]:
                last_accessed = item.get('last_accessed', 'N/A')
                if hasattr(last_accessed, 'isoformat'):
                    last_accessed = last_accessed.isoformat()
                lines.append(f"- [{item.get('type')}] {item.get('name')} (접근: {item.get('access_count')}회, 마지막: {last_accessed})")

        # 참조 타임라인
        timeline = get_reference_timeline(hours=hours, interval_minutes=60)
        lines.append(f"\n## 시간대별 참조 횟수")
        for entry in timeline[-12:]:  # 최근 12개 구간만
            lines.append(f"- {entry['time']}: {entry['count']}회")

        return "\n".join(lines)

    async def _get_quality_report(self) -> str:
        """품질 리포트"""
        quality = get_quality_metrics()
        summary = get_analytics_summary()

        lines = [
            "# 지식그래프 품질 리포트\n",
            "## 분포 균형 분석"
        ]

        # 엔트로피 점수 해석
        entropy = quality.type_distribution_entropy
        if entropy >= 0.8:
            entropy_grade = "✅ 우수 (균형 잡힌 분포)"
        elif entropy >= 0.6:
            entropy_grade = "⚠️ 보통 (약간의 편향)"
        else:
            entropy_grade = "❌ 주의 (심한 편향)"

        lines.append(f"- 엔트로피 점수: {entropy:.2%} {entropy_grade}")

        # 타입별 편향
        bias = quality.bias_indicators
        type_bias = bias.get('type_bias', {})
        if type_bias:
            lines.append("\n## 노드 타입 편향")
            for node_type, deviation in sorted(type_bias.items(), key=lambda x: -x[1])[:5]:
                if deviation > 0.5:
                    status = "⚠️ 과다 참조"
                elif deviation < -0.3:
                    status = "⚠️ 과소 참조"
                else:
                    status = "✅ 적정"
                lines.append(f"- {node_type}: 편차 {deviation:.1%} {status}")

        # 최신성 편향
        recency = bias.get('recency_bias', 0)
        lines.append(f"\n## 최신성 편향")
        if recency > 0.8:
            lines.append(f"- 점수: {recency:.1%} ⚠️ 최근 노드에 집중됨")
            lines.append("- 권장: 과거 지식도 균형있게 참조 필요")
        elif recency > 0.5:
            lines.append(f"- 점수: {recency:.1%} ⚠️ 약간의 최신성 편향")
        else:
            lines.append(f"- 점수: {recency:.1%} ✅ 균형 잡힌 시간 분포")

        # 개선 권장사항
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
            lines.append("✅ 현재 지식그래프 품질이 양호합니다!")

        return "\n".join(lines)

    
    
    
    async def _provide_feedback(self, args: dict) -> str:
        """컨텍스트 유용성 피드백을 통한 노드 가중치 업데이트 (강화학습)"""
        if not self.weight_learner:
            return "NodeWeightLearner is not initialized."
            
        success = args.get("success", True)
        identifiers = args.get("identifiers", [])
        
        if not identifiers:
            return "No identifiers provided to update."
            
        session_id = get_current_session_id() or "unknown_session"
        result = self.weight_learner.process_feedback(session_id, success, identifiers)
        
        if result.get("success"):
            action = "+0.2 가중치 증가 (최대 2.0)" if success else "-0.1 가중치 감소 (최소 0.1)"
            return f"📈 피드백이 지식그래프에 반영되었습니다.\n업데이트된 노드 수: {result.get('updated', 0)}개\n적용된 행동: {action}\n다음 검색부터 이 정보가 우선순위에 반영됩니다."
        else:
            return f"❌ 업데이트 실패: {result.get('error', 'Unknown error')}"

    async def _simulate_impact(self, args: dict) -> str:
        """폭발 반경(Impact) 시뮬레이션"""
        if not self.impact_simulator:
            return "ImpactSimulator is not initialized."
            
        target = args.get("target_name")
        if not target:
            return "Error: target_name is required"
            
        depth = args.get("depth", 3)
        result = self.impact_simulator.simulate_impact(target, depth)
        
        if result.get("success"):
            m = result["metrics"]
            target_info = result["target"]
            warning = result["warning"]
            
            report = [
                f"💥 [Blast Radius Report] Target: {target_info['name']} ({target_info['type']})",
                f"Risk Level: {m['risk_level']} (Score: {m['risk_score']}/100)",
                f"경고: {warning}",
                "",
                "📊 영향도 요약:",
                f"  - 총 영향 받는 노드: {m['total_affected_nodes']}개",
                f"  - 직접 호출하는 노드(1-hop): {m['direct_dependents']}개",
                f"  - 연쇄적으로 영향을 받는 노드(간접): {m['indirect_dependents']}개",
                f"  - 영향 받는 모듈(파일) 수: {m['modules_affected']}개",
                "",
            ]
            
            if result.get("affected_modules"):
                report.append("📁 영향을 받는 주요 모듈:")
                for mod in result["affected_modules"][:5]:
                    report.append(f"  - {mod}")
            
            if result.get("critical_dependents"):
                report.append("")
                report.append("⚠️ 직접적으로 타격을 입는 함수/클래스 (수정 시 확인 필수):")
                for dep in result["critical_dependents"]:
                    report.append(f"  - [{dep['type']}] {dep['name']} (in {dep.get('module', 'unknown')})")
                    
            return "\n".join(report)
        else:
            return f"❌ 시뮬레이션 실패: {result.get('error', 'Unknown error')}"

    async def _sync_incremental(self, args: dict) -> str:
        """실시간 파일 동기화"""
        if not self.write_back:
            return "GraphWriteBack is not initialized."
            
        file_path = args.get("file_path")
        if not file_path:
            return "Error: file_path is required"
            
        result = self.write_back.sync_file(file_path)
        
        if result.get("success"):
            stats = result.get("stats", {})
            return f"✅ 성공적으로 지식그래프를 업데이트했습니다!\n파일: {file_path}\n- 반영된 함수: {stats.get('functions', 0)}개\n- 반영된 클래스: {stats.get('classes', 0)}개"
        else:
            return f"❌ 업데이트 실패: {result.get('error', 'Unknown error')}"

    async def _evolve_ontology(self, args: dict) -> str:
        """Phase 5.5: 온톨로지 자가 치유."""
        if not self.ontology_evolver:
            return "OntologyEvolver is not initialized."

        auto_fix = args.get("auto_fix", False)
        report = self.ontology_evolver.evolve(auto_fix)

        lines = [
            "# 🧬 Ontology Evolution Report\n",
            f"총 이슈: {report['total_issues']}개 | 자동 수정: {'✅ ON' if auto_fix else '❌ OFF'}\n",
        ]

        orphans = report.get("orphans", [])
        lines.append(f"## 1. Orphan Nodes ({len(orphans)}개)")
        for o in orphans[:5]:
            lines.append(f"  - [{o['type']}] {o['name']} ({o.get('module', 'N/A')})")
        if auto_fix and orphans:
            lines.append(f"  → {len(orphans)}개 자동 삭제됨")

        gods = report.get("god_modules", [])
        lines.append(f"\n## 2. God Modules ({len(gods)}개)")
        for g in gods:
            lines.append(f"  - {g['name']}: {g['func_count']}개 함수 ⚠️")

        circles = report.get("circular_deps", [])
        lines.append(f"\n## 3. Circular Dependencies ({len(circles)}개)")
        for c in circles:
            lines.append(f"  - {c['module_a']} ↔ {c['module_b']}")

        stale = report.get("stale_nodes", [])
        lines.append(f"\n## 4. Stale Nodes ({len(stale)}개)")
        for s in stale[:5]:
            lines.append(f"  - {s['name']}: score={s.get('score', 'N/A')}, {s.get('days_stale', '?')}일 미사용")

        drift = report.get("schema_drift", [])
        lines.append(f"\n## 5. Schema Drift ({len(drift)}개)")
        for d in drift[:5]:
            lines.append(f"  - {d['name']}: {d['filepath']} (파일 없음)")

        return "\n".join(lines)

    async def _promote_pattern(self, args: dict) -> str:
        """Phase 5.6: 패턴 GLOBAL 승격."""
        if not self.knowledge_transfer:
            return "KnowledgeTransfer is not initialized."

        name = args.get("name")
        if not name:
            return "Error: name is required."

        result = self.knowledge_transfer.promote_pattern(name)
        if result.get("success"):
            return f"🌍 {result['message']}\n이전 namespace: {result['previous_namespace']}\n점수: {result['score']}"
        return f"❌ {result.get('error', 'Unknown error')}"

    async def _get_global_insights(self, args: dict) -> str:
        """Phase 5.6: 글로벌 인사이트."""
        if not self.knowledge_transfer:
            return "KnowledgeTransfer is not initialized."

        limit = args.get("limit", 10)
        result = self.knowledge_transfer.get_global_insights(limit)

        if not result.get("success"):
            return f"❌ {result.get('error', 'Unknown')}"

        lines = ["# 🌍 Cross-Project Global Insights\n"]

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
            lines.append(f"  - ⚠️ [{a['type']}] {a['name']} (score={a.get('score')})")

        return "\n".join(lines)

    async def _suggest_tests(self, args: dict) -> str:
        """Phase 5.4: 자동 테스트 생성."""
        if not self.auto_test_gen:
            return "AutoTestGenerator is not initialized."

        func_name = args.get("function_name")
        if not func_name:
            return "Error: function_name is required."

        result = self.auto_test_gen.suggest_tests(func_name)
        if not result.get("success"):
            return f"❌ 테스트 생성 실패: {result.get('error', 'Unknown')}"

        func = result["function"]
        mocks = result["mock_candidates"]
        usages = result["usage_patterns"]

        lines = [
            f"# 🧪 Auto Test Suggestion: {func['name']}\n",
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

    async def _get_bug_hotspots(self, args: dict) -> str:
        """Phase 5.3: 버그 핫스팟 조회."""
        if not self.bug_radar:
            return "BugRadar is not initialized."

        top_k = args.get("top_k", 10)
        result = self.bug_radar.get_hotspots(top_k)

        if not result.get("success"):
            return f"❌ 핫스팟 조회 실패: {result.get('error', 'Unknown')}"

        hotspots = result["hotspots"]
        if not hotspots:
            return "✅ 버그 핫스팟이 감지되지 않았습니다. 코드가 안정적입니다."

        lines = [
            "# 🔥 Predictive Bug Radar\n",
            f"총 {len(hotspots)}개 핫스팟 감지 (임계값: {result['threshold']}점)\n",
        ]

        for i, h in enumerate(hotspots, 1):
            severity_icon = {"CRITICAL": "🔴", "HIGH": "🟠", "MEDIUM": "🟡", "LOW": "🟢"}.get(h.get("severity"), "⚪")
            lines.append(f"## {i}. {severity_icon} [{h['type']}] {h['name']}")
            lines.append(f"   - Risk Score: **{h['risk_score']}**/100 ({h.get('severity', 'N/A')})")
            lines.append(f"   - Churn: {h['churn']}회 수정")
            lines.append(f"   - Fan-in: {h['fan_in']} / Fan-out: {h['fan_out']}")
            lines.append(f"   - Lines: {h['line_count']}")
            if h.get("module"):
                lines.append(f"   - Module: {h['module']}")
            lines.append("")

        return "\n".join(lines)

    async def _get_session_context(self, args: dict) -> str:
        """Phase 5.2: 현재 대화 세션의 누적 컨텍스트 요약."""
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")
        memory = ConversationMemory(project_dir)

        if args.get("reset"):
            memory.reset()
            return "✅ 대화 컨텍스트가 초기화되었습니다."

        summary = memory.get_context_summary()
        refinement = memory.get_search_refinement()

        lines = [
            "# 대화 세션 컨텍스트 (Phase 5.2)\n",
            f"- 대화 ID: {summary['conversation_id']}",
            f"- 턴 수: {summary['turn_count']}",
            f"- 현재 Intent: {summary['current_intent'] or 'N/A'}",
            f"- Intent 흐름: {' → '.join(summary['intent_flow']) if summary['intent_flow'] else 'N/A'}",
            f"- 집중 범위: {summary['focus_scope'] or '전체'}",
            f"- Narrowing 레벨: {summary['narrowing_level']} (0=광범위, 3=핀포인트)",
            f"- 누적 주입 노드: {summary['total_injected']}개",
        ]

        transition = summary.get("intent_transition")
        if transition:
            lines.append(f"\n⚡ Intent 전환 감지: {transition['from']} → {transition['to']}")

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

    async def _semantic_search(self, args: dict) -> str:
        """Phase 6.2: 의미 기반 벡터 검색."""
        if not self.vector_search_engine:
            return "VectorSearchEngine is not initialized."

        query = args.get("query", "")
        limit = args.get("limit", 10)
        threshold = args.get("threshold", 0.7)

        result = self.vector_search_engine.semantic_search(query, limit, threshold)

        if not result.get("success"):
            return f"검색 실패: {result.get('error', 'Unknown')}"

        lines = [
            f"# Semantic Search Results",
            f"쿼리: {query}",
            f"결과: {result['total']}개 (threshold: {threshold})\n",
        ]

        for i, item in enumerate(result.get("results", []), 1):
            sim = item.get("similarity", 0)
            sim_bar = "█" * int(sim * 10) + "░" * (10 - int(sim * 10))
            lines.append(f"## {i}. [{item.get('type')}] {item.get('name')}")
            lines.append(f"   유사도: {sim_bar} {sim:.3f}")
            if item.get("qname"):
                lines.append(f"   경로: `{item['qname']}`")
            if item.get("docstring"):
                lines.append(f"   설명: {item['docstring'][:150]}")
            if item.get("module"):
                lines.append(f"   모듈: {item['module']}")
            if item.get("calls"):
                lines.append(f"   호출: {', '.join(item['calls'])}")
            if item.get("called_by"):
                lines.append(f"   호출자: {', '.join(item['called_by'])}")
            lines.append("")

        return "\n".join(lines)

    async def _ask_codebase(self, args: dict) -> str:
        """Phase 7.1: RAG Answer Engine - 코드베이스 자연어 질의응답."""
        if not self.rag_engine:
            return "RAGEngine is not initialized."

        question = args.get("question", "")
        max_tokens = args.get("max_context_tokens", 6000)

        result = self.rag_engine.ask(question, max_tokens)

        if not result.get("success"):
            return f"RAG 실패: {result.get('error', 'Unknown')}"

        lines = [
            f"# 코드베이스 답변\n",
            result["answer"],
            f"\n---",
            f"**검색된 소스**: {result['sources_count']}개",
            f"**컨텍스트**: ~{result['context_tokens']} tokens",
            f"**검색 전략**: {result.get('search_strategy', 'N/A')}",
        ]

        if result.get("from_cache"):
            lines.append("**캐시**: 캐시된 답변 (5분 TTL)")

        citations = result.get("citations", [])
        if citations:
            lines.append(f"\n**참조된 코드**:")
            for c in citations[:10]:
                lines.append(
                    f"- [{c['type']}] {c['name']} ({c.get('module', 'N/A')})"
                )

        return "\n".join(lines)

    async def _evaluate_code(self, args: dict) -> str:
        """Phase 6.6: AI 코드 품질 평가."""
        if not self.llm_judge:
            return "LLMJudge is not initialized."

        file_path = args.get("file_path")
        code_snippet = args.get("code_snippet")

        if not file_path and not code_snippet:
            return "Error: file_path or code_snippet is required."

        result = self.llm_judge.evaluate_code(file_path, code_snippet)

        if not result.get("success"):
            return f"Evaluation failed: {result.get('error', 'Unknown')}"

        lines = [
            f"# Code Quality Evaluation",
            f"",
            f"**Overall Score: {result['overall_score']}/5**",
            f"",
            "## Criteria Scores",
        ]
        for criterion, score in result.get("criteria", {}).items():
            bar = "█" * score + "░" * (5 - score)
            lines.append(f"- {criterion}: {bar} {score}/5")

        lines.append(f"\n## Feedback")
        lines.append(result.get("feedback", ""))

        suggestions = result.get("suggestions", [])
        if suggestions:
            lines.append(f"\n## Suggestions")
            for i, s in enumerate(suggestions, 1):
                lines.append(f"{i}. {s}")

        if result.get("eval_id"):
            lines.append(f"\n---\nEval ID: {result['eval_id']}")

        return "\n".join(lines)

    # ===== Phase 7.7: Shared Memory Pool =====

    async def _get_shared_context(self, args: dict) -> str:
        """Phase 7.7: 세션 간 공유 컨텍스트 조회."""
        if not self.shared_memory:
            return "SharedMemoryPool is not initialized."
        project_dir = args.get("project_dir", "")
        keys = args.get("keys")
        result = self.shared_memory.get_context(project_dir, keys)
        if not result.get("success"):
            return f"조회 실패: {result.get('error')}"

        lines = [f"# Shared Context ({result['total']} entries)\n"]
        for entry in result.get("entries", []):
            lines.append(f"## [{entry['key']}]")
            lines.append(f"- Value: {entry['value']}")
            lines.append(f"- Session: {entry.get('session_id', 'N/A')}")
            lines.append(f"- Published: {entry.get('published_at', 'N/A')}")
            lines.append("")

        conflicts = result.get("conflicts", [])
        if conflicts:
            lines.append("## Conflicts Detected")
            for c in conflicts:
                lines.append(f"- {c['warning']}")

        return "\n".join(lines)

    async def _publish_context(self, args: dict) -> str:
        """Phase 7.7: 세션 간 컨텍스트 발행."""
        if not self.shared_memory:
            return "SharedMemoryPool is not initialized."
        key = args.get("key", "")
        value = args.get("value", "")
        session_id = get_current_session_id() or "unknown"
        project_dir = os.environ.get("CLAUDE_PROJECT_DIR", "")

        result = self.shared_memory.publish(key, value, session_id, project_dir)
        if result.get("success"):
            return f"Published: [{key}] (TTL: {result['ttl_minutes']}min)"
        return f"Publish failed: {result.get('error')}"

    # ===== Phase 7.2: Context-Aware Code Assist =====

    async def _assist_code(self, args: dict) -> str:
        """Phase 7.2: KG 컨텍스트 기반 코드 수정/생성 제안."""
        if not self.code_assist:
            return "CodeAssist is not initialized."

        target = args.get("target_function", "")
        instruction = args.get("instruction", "")

        result = self.code_assist.assist(target, instruction)

        if not result.get("success"):
            return f"코드 어시스트 실패: {result.get('error')}"

        lines = [
            f"# Code Assist: {result['function']}",
            f"**Module**: {result.get('module', 'N/A')}",
            f"**Instruction**: {result['instruction']}",
            f"**Original Lines**: {result.get('original_lines', 'N/A')}",
            "",
            "## Changes Summary",
            result.get("changes_summary", ""),
            "",
            "## Modified Code",
            "```python",
            result.get("modified_code", ""),
            "```",
        ]

        imports = result.get("added_imports", [])
        if imports:
            lines.append("\n## Added Imports")
            for imp in imports:
                lines.append(f"- `{imp}`")

        warnings = result.get("warnings", [])
        if warnings:
            lines.append("\n## Warnings")
            for w in warnings:
                lines.append(f"- {w}")

        return "\n".join(lines)

    # ===== Phase 7.4: Graph-Driven API Docs Generator =====

    async def _generate_docs(self, args: dict) -> str:
        """Phase 7.4: Graph-Driven API Docs Generator."""
        if not self.doc_generator:
            return "DocGenerator is not initialized."

        module_name = args.get("module_name", "*")
        depth = args.get("depth", 2)

        result = self.doc_generator.generate(module_name, depth)

        if not result.get("success"):
            return f"문서 생성 실패: {result.get('error')}"

        return result["markdown"]

    # ===== Phase 8.2: Auto-Index Project =====

    async def _index_project(self, args: dict) -> str:
        """프로젝트 전체를 지식그래프에 인덱싱 + 임베딩."""
        project_path = args.get("project_path", "")
        no_embed = args.get("no_embed", False)

        if not os.path.isdir(project_path):
            return f"Error: '{project_path}' is not a valid directory"

        project_path = os.path.abspath(project_path)

        # 인덱싱 대상 파일 탐색
        EXTS = {".py", ".js", ".ts", ".jsx", ".tsx"}
        EXCLUDES = {
            "node_modules", "__pycache__", ".git", "dist", "build",
            ".next", "venv", ".venv", ".tox", ".mypy_cache",
            ".pytest_cache", "coverage", ".turbo", ".cache",
        }

        files = []
        for root, dirs, fnames in os.walk(project_path):
            dirs[:] = [d for d in dirs if d not in EXCLUDES and not d.startswith(".")]
            for fn in fnames:
                if Path(fn).suffix in EXTS:
                    files.append(os.path.join(root, fn))
        files.sort()

        if not files:
            return f"No indexable files found in {project_path}"

        # 동기화 (sync_file은 동기 메서드이므로 executor에서 실행)
        loop = asyncio.get_event_loop()

        def _do_sync():
            synced = 0
            errors = 0
            total_functions = 0
            total_classes = 0
            error_details = []

            for fp in files:
                try:
                    result = self.write_back.sync_file(fp)
                    if result.get("success"):
                        synced += 1
                        stats = result.get("stats", {})
                        total_functions += stats.get("functions", 0)
                        total_classes += stats.get("classes", 0)
                    else:
                        errors += 1
                        if len(error_details) < 5:
                            rel = os.path.relpath(fp, project_path)
                            error_details.append(f"{rel}: {result.get('error', 'unknown')}")
                except Exception as e:
                    errors += 1
                    if len(error_details) < 5:
                        rel = os.path.relpath(fp, project_path)
                        error_details.append(f"{rel}: {e}")

            return synced, errors, total_functions, total_classes, error_details

        synced, errors, total_functions, total_classes, error_details = await loop.run_in_executor(None, _do_sync)

        # 임베딩
        embed_info = ""
        if not no_embed:
            def _do_embed():
                from mcp_server.pipeline.embedding_pipeline import EmbeddingPipeline
                ep = EmbeddingPipeline(self.hybrid_search.driver)
                ep.create_vector_index()
                return ep.embed_all_nodes(batch_size=100)

            try:
                embed_stats = await loop.run_in_executor(None, _do_embed)
                embed_info = (
                    f"\n\nEmbedding: {embed_stats.get('total_embedded', 0)} nodes embedded, "
                    f"{embed_stats.get('total_errors', 0)} errors, "
                    f"{embed_stats.get('elapsed_seconds', 0):.1f}s"
                )
            except Exception as e:
                embed_info = f"\n\nEmbedding failed: {e}"

        # watched-projects에 등록
        watch_info = ""
        try:
            import json as _json
            watched_path = os.path.expanduser("~/.claude/kg-watched-projects.json")
            if os.path.exists(watched_path):
                with open(watched_path, "r", encoding="utf-8") as f:
                    watched = _json.load(f)
            else:
                watched = {"projects": [], "auto_detect": True, "exclude_patterns": list(EXCLUDES)}

            existing = {p["path"] for p in watched.get("projects", [])}
            if project_path not in existing:
                watched["projects"].append({
                    "path": project_path,
                    "enabled": True,
                    "namespace": os.path.basename(project_path),
                })
                os.makedirs(os.path.dirname(watched_path), exist_ok=True)
                with open(watched_path, "w", encoding="utf-8") as f:
                    _json.dump(watched, f, indent=2, ensure_ascii=False)
                watch_info = f"\nRegistered in watched-projects."
            else:
                watch_info = f"\nAlready in watched-projects."
        except Exception as e:
            watch_info = f"\nFailed to update watched-projects: {e}"

        # 결과 포맷팅
        lines = [
            f"# Project Indexed: {os.path.basename(project_path)}",
            f"",
            f"- Path: {project_path}",
            f"- Files scanned: {len(files)}",
            f"- Files synced: {synced}",
            f"- Sync errors: {errors}",
            f"- Functions: {total_functions}",
            f"- Classes: {total_classes}",
        ]

        if error_details:
            lines.append(f"\nFirst {len(error_details)} errors:")
            for ed in error_details:
                lines.append(f"  - {ed}")

        lines.append(embed_info)
        lines.append(watch_info)

        return "\n".join(lines)

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
    await server.run()


if __name__ == "__main__":
    asyncio.run(main())
