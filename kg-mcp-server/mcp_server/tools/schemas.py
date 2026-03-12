"""MCP Tool Schema Definitions.

All tool schemas (name, description, inputSchema) extracted from server.py
to keep the main server class focused on wiring, not schema definition.
"""

import mcp.types as types


def get_all_tool_schemas() -> list[types.Tool]:
    """Return all MCP tool schemas."""
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
