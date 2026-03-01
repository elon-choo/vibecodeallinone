# Claude Code Power Pack - External Review Prompt Kit

## 현재 상태 요약

`claude-code-power-pack`은 Claude Code용 오픈소스 통합 플러그인으로, 3가지 핵심 컴포넌트를 하나의 패키지로 통합:

- **12개 AI 스킬** (Markdown 기반, 의존성 없음): clean-code-mastery, vibe-coding-orchestrator, codebase-graph, smart-context, impact-analyzer, arch-visualizer, code-reviewer, security-shield, code-smell-detector, naming-convention-guard, tdd-guardian, graph-loader
- **Neo4j Knowledge Graph MCP Server** (Python, 39파일): hybrid_search, smart_context, sync_incremental 등 20+ MCP 도구. Gemini 3 Flash + Voyage AI voyage-code-3 임베딩 사용
- **8개 KG 자동화 Hooks** (Python): auto-trigger, incremental indexing, quality judgment, health monitoring

### 핵심 수치
- 126 파일, 36,996줄
- 3-tier 설치 (Skills Only / +KG MCP / Full)
- 보안 스캔 통과: API 키 0건, 개인 경로 0건
- 내부 리뷰 3라운드 완료: Red Team 72/65 → Blue Team 88/85 → Purple Team 93/90
- Codex o4-mini 리뷰: 60/100 (부분 읽기 한계)
- MIT 라이선스

### 아키텍처
```
claude-code-power-pack/
├── skills/           # 12개 AI 스킬 (순수 Markdown)
├── kg-mcp-server/    # Neo4j KG MCP Server (Python)
│   ├── server.py     # 1,861줄, 20+ MCP 도구
│   ├── config.py     # 환경변수 기반 설정
│   └── pipeline/     # hybrid_search, embedding, rag_engine 등 18개 모듈
├── hooks/            # 8개 자동화 훅 (Python)
├── scripts/          # 3-tier 설치 스크립트
├── README.md, LICENSE (MIT), CONTRIBUTING.md, AGENTS.md
└── .env.example      # 환경변수 템플릿
```

---

## Prompt 1: 종합 아키텍처 리뷰

```
당신은 시니어 소프트웨어 아키텍트입니다. 아래 오픈소스 프로젝트의 아키텍처를 리뷰해주세요.

프로젝트: claude-code-power-pack
목적: Claude Code(AI 코딩 도구)용 통합 플러그인. 12개 AI 스킬 + Neo4j Knowledge Graph MCP Server + 자동화 Hooks를 하나의 패키지로 제공.

구성:
1. skills/ (12개, Markdown 기반, 의존성 없음)
   - clean-code-mastery: SOLID/DRY/KISS + OWASP 보안, 8개 언어 지원
   - vibe-coding-orchestrator: 18개 스킬 조율, 9개 레이어, 4단계 성숙도 모델
   - codebase-graph: 인메모리 코드 지식 그래프
   - smart-context: 토큰 효율적 컨텍스트 (72-77% 절감)
   - impact-analyzer: 변경 전파 분석
   - arch-visualizer: Mermaid/PlantUML 다이어그램
   - code-reviewer: 품질 게이트 채점
   - security-shield: OWASP Top 10, 40+ 시크릿 탐지
   - code-smell-detector: 22가지 코드 스멜
   - naming-convention-guard: 언어별 네이밍
   - tdd-guardian: TDD 워크플로우, 가짜 테스트 탐지
   - graph-loader: JSON→Neo4j 로더

2. kg-mcp-server/ (Python, 39파일, 14,100줄)
   - server.py: MCP 프로토콜 서버, 20+ 도구
   - pipeline/: hybrid_search, embedding_pipeline, rag_engine, llm_judge, auto_test_gen, doc_generator, ts_parser 등 18개 모듈
   - 기술스택: Neo4j(로컬), Gemini 3 Flash, Voyage AI voyage-code-3, Tree-sitter(7언어), FastAPI
   - 벤치마크: keyword P@1 0.720, vector P@1 0.680, hybrid P@1 0.680

3. hooks/ (Python, 8개, 2,387줄)
   - mcp-kg-auto-trigger.py: 의도 분류(7가지) → Neo4j 컨텍스트 자동 주입
   - kg-incremental-indexer.py: 파일 변경 시 AST 파싱 → Neo4j 동기화
   - kg-auto-judge.py: LLM 품질 평가 → Neo4j 저장
   - kg-bulk-indexer.py, kg-feedback-collector.py, kg-precheck.py, kg-survival-checker.py, post-mcp-kg.py

4. 설치: 3-tier (Skills Only / +KG MCP / Full)
5. Graceful Degradation: Neo4j 없이도 스킬 100% 동작, API 키 없이도 키워드 검색 동작

리뷰 요청:
1. 아키텍처 장점/단점 분석
2. 모듈 간 결합도(coupling) 평가
3. 확장성(새 스킬/언어 추가 용이성)
4. 3-tier 설치 전략 적절성
5. Graceful degradation 설계 완성도
6. 성능 병목 가능성
7. 오픈소스 커뮤니티 채택 가능성
8. 경쟁 제품 대비 차별점 (levnikolaevich/claude-code-skills 102개, automagik-dev/forge 멀티에이전트, numman-ali/openskills npm 설치)
9. 점수 /100 + GO/NO-GO 판정
10. 릴리스 전 반드시 수정해야 할 TOP 5
```

---

## Prompt 2: 보안 전문가 리뷰

```
당신은 사이버보안 전문가(OWASP, SAST/DAST, 시크릿 탐지)입니다. 아래 오픈소스 프로젝트의 보안 상태를 감사해주세요.

프로젝트: claude-code-power-pack (Claude Code용 통합 플러그인)

보안 관련 컨텍스트:
- Python MCP Server가 Neo4j 로컬 DB에 연결 (bolt://localhost:7687)
- Gemini API, Voyage AI API, OpenAI API 키를 환경변수로 관리
- .env.example 제공, .gitignore에 .env 포함
- 8개 Python 훅이 Claude Code의 PreToolUse/PostToolUse에 등록
- install.sh가 ~/.claude/skills/, ~/.claude/hooks/에 파일 복사
- 보안 스캔 완료: 하드코딩된 API 키 0건, 개인 경로 0건

감사 요청:
1. 시크릿 유출 위험 (API 키, 토큰, 비밀번호)
2. 인젝션 취약점 (SQL, Command, Path Traversal)
3. 의존성 보안 (알려진 CVE)
4. install.sh 스크립트 안전성 (임의 코드 실행 위험)
5. MCP Server 공격 표면 (인증, 권한)
6. Hooks의 권한 범위 (파일시스템 접근)
7. Neo4j 기본 비밀번호 문제
8. Cross-tool 호환성의 보안 의미
9. 심각도별 분류 (Critical/High/Medium/Low)
10. 수정 권고사항 우선순위
```

---

## Prompt 3: 개발자 경험(DX) 리뷰

```
당신은 DevRel(개발자 관계) 전문가입니다. 아래 오픈소스 프로젝트의 개발자 경험을 평가해주세요.

프로젝트: claude-code-power-pack
대상 사용자: Claude Code 사용자 (초보~전문가), Codex/Gemini CLI 사용자

평가 항목:
1. 첫 설치 경험 (Time-to-First-Value)
   - git clone부터 첫 'vibe review' 실행까지 몇 분?
   - 필수 의존성은?
   - 실패 시 에러 메시지 품질은?

2. 문서 품질
   - README.md가 30초 내에 "이게 뭔지" 전달하는가?
   - 설치 가이드가 copy-paste 가능한가?
   - 비기너 가이드 품질 (영문 + 한국어)

3. 스킬 발견성
   - 사용자가 12개 스킬 중 필요한 것을 어떻게 찾는가?
   - vibe commands가 직관적인가?
   - AGENTS.md가 Codex/Gemini CLI에서 제대로 인식되는가?

4. 설정 복잡도
   - Tier 1은 정말 "zero config"인가?
   - Tier 2/3의 설정 단계가 몇 개인가?
   - .vibeconfig.yml이 필요한가, 선택인가?

5. 에러 처리
   - Neo4j 연결 실패 시 사용자에게 어떤 메시지가 표시되는가?
   - API 키 미설정 시 graceful degradation이 실제로 작동하는가?

6. 업그레이드 경험
   - v1에서 v2로 업그레이드 시 기존 설정이 보존되는가?
   - install.sh가 기존 스킬을 백업하는가?

7. 경쟁 제품 대비 DX
   - numman-ali/openskills (npm i -g openskills)
   - alirezarezvani/claude-code-skill-factory
   - Jeffallan/claude-skills (66 스킬)

8. 점수 /100 + 개선 TOP 5
```

---

## Prompt 4: 코드 품질 리뷰 (KG MCP Server)

```
당신은 Python 시니어 개발자입니다. 아래 MCP Server 코드의 품질을 리뷰해주세요.

프로젝트: claude-code-power-pack의 kg-mcp-server/
규모: 39 Python 파일, 약 14,100줄
기술스택: Neo4j, MCP Protocol, Gemini 3 Flash, Voyage AI, Tree-sitter, FastAPI

주요 파일:
- server.py (1,861줄): MCP 서버 메인, 20+ 도구 정의
- pipeline/hybrid_search.py (695줄): BM25 + 벡터 하이브리드 검색
- pipeline/embedding_pipeline.py (566줄): voyage-code-3 임베딩
- pipeline/llm_judge.py (553줄): LLM 기반 코드 품질 평가
- pipeline/rag_engine.py (444줄): GraphRAG 엔진
- pipeline/ts_parser.py (371줄): Tree-sitter 파서

리뷰 요청:
1. server.py의 1,861줄은 God Class인가? 분리 전략은?
2. pipeline/ 모듈 간 의존성 구조
3. 에러 처리 패턴 (Neo4j 연결 실패, API 타임아웃)
4. 테스트 가능성 (모킹, DI)
5. 타입 힌팅 완성도
6. 비동기 처리 패턴
7. 메모리 관리 (대규모 코드베이스 인덱싱 시)
8. config.py의 환경변수 검증
9. 로깅 전략
10. 점수 /100 + 리팩토링 우선순위 TOP 5
```

---

## Prompt 5: 오픈소스 커뮤니티 성장 전략 리뷰

```
당신은 오픈소스 프로젝트 매니저입니다. 아래 프로젝트의 커뮤니티 성장 전략을 평가해주세요.

프로젝트: claude-code-power-pack
현재 상태: v2.0.0 초기 릴리스 준비 중
구성: 12 AI 스킬 + Neo4j KG MCP Server + 8 자동화 Hooks
라이선스: MIT
경쟁:
- levnikolaevich/claude-code-skills (102 스킬)
- Jeffallan/claude-skills (66 스킬, 365 참조파일)
- alirezarezvani/claude-code-skill-factory (스킬 팩토리)
- numman-ali/openskills (npm 패키지)
- VoltAgent/awesome-agent-skills (380+ 스킬 마켓플레이스)

차별점:
- KG 통합 (유일): 코드베이스 인텔리전스 (82K 노드, 190K 엣지 검증)
- 토큰 절감: 72-77% (smart-context)
- 3-tier 설치: 진입장벽 최소화
- 4단계 성숙도 모델: MVP→Enterprise 경로

평가 요청:
1. GitHub 레포 이름/설명 최적화
2. awesome-claude-skills 등 큐레이션 리스트 등록 전략
3. README의 "hero section" 매력도
4. Star/Fork 유도 전략
5. 컨트리뷰터 온보딩 경로
6. 로드맵 제시 방법
7. 초기 100 Star까지의 전략
8. npm/pip 패키지 배포 필요성
9. 데모/스크린캐스트 필요성
10. 점수 /100 + 즉시 실행 가능한 TOP 5 액션
```

---

## 사용법

위 프롬프트를 아래 도구에 복붙하세요:

| 도구 | 사용법 |
|------|--------|
| **Gemini** | [AI Studio](https://aistudio.google.com) → gemini-2.5-pro |
| **ChatGPT** | [chat.openai.com](https://chat.openai.com) → o3 또는 GPT-5 |
| **Claude** | [claude.ai](https://claude.ai) → Claude Opus 4.5 |
| **Codex CLI** | `codex --dangerously-bypass-approvals-and-sandbox "프롬프트"` |
| **Gemini CLI** | `gemini "프롬프트"` |

### 파일 첨부 시
위 프롬프트와 함께 아래 파일들을 첨부하면 더 정확한 리뷰:
- `README.md`
- `skills/clean-code-mastery/SKILL.md`
- `skills/vibe-coding-orchestrator/SKILL.md`
- `kg-mcp-server/server.py` (앞부분 500줄)
- `kg-mcp-server/config.py`
- `hooks/mcp-kg-auto-trigger.py` (앞부분 200줄)
- `scripts/install.sh`
