# S10 Replan Context

## 1. 왜 다시 계획을 짜는가

지금까지의 세션은 `assistant-web`, `assistant-api`, memory provenance/export/delete, checkpoint sync, trust evidence, repeatable smoke까지는 올려놨다. 하지만 사용자 목표는 단순히 web/PWA bootstrap을 완성하는 것이 아니라 아래 제품 방향을 실제로 잠그는 것이다.

- 사람들이 아주 쉽게 설치할 수 있어야 한다.
- 텔레그램에 아주 쉽게 연동할 수 있어야 한다.
- PC, 모바일, 텔레그램, 웹 어디서든 쉽게 쓸 수 있어야 한다.
- `openclaw`의 메모리/비서/cron job 편의 기능을 참고해 제품 가치를 높여야 한다.
- `엘런자비스 + knowledge graph` 계열의 vibe-coding용 메모리 아키텍처를 접목해 비개발자 코딩 사용자를 도와야 한다.
- 보안 유의사항이 설계 초기부터 들어가 있어야 한다.

즉, 기존 `S01~S09`는 런타임 하드닝과 bootstrap에 가까웠고, 이제는 배포성, surface 전략, memory architecture, assistant convenience를 다시 묶는 재기획이 필요하다.

## 2. 현재 저장소에서 이미 있는 것

### 2.1 사용자 런타임 쪽

- `apps/assistant-web`
  - static mobile-first shell
  - auth start/callback consumption
  - memory CRUD + provenance render
  - memory export/delete UI
  - checkpoint conflict recovery
  - trust summary surface
- `services/assistant-api`
  - FastAPI bootstrap runtime
  - auth start/callback/session routes
  - memory CRUD/export/delete
  - checkpoint sync/conflict handling
  - trust summary lookup
- `packages/contracts`
  - auth/memory/checkpoint/trust contract
- `packages/evidence-contracts`
  - evidence summary / manifest schema

### 2.2 운영/검증 쪽

- repeatable operator smoke
  - `scripts/assistant/run_operator_smoke.py`
- repeatable browser smoke
  - `scripts/assistant/run_browser_smoke.py`
- release evidence 보조 artifact
  - `artifacts/operator_smoke/*`
  - `artifacts/browser_smoke/*`
  - `artifacts/e2e_score.json`
- `agent-orchestrator` 기반 세션 운영 체계
  - `docs/session-ops/*`
  - `.agent-orchestrator/config.json`

### 2.3 지식 그래프/메모리 자산

- 기존 repo의 핵심 강점은 `Knowledge Graph MCP`, code intelligence, skill pack, orchestration layer다.
- 다만 현재 `assistant-web`/`assistant-api` 제품 플로우와 `Jarvis/KG vibe-coding memory`가 아직 하나의 사용자 제품 전략으로 완전히 합쳐지진 않았다.

## 3. 현재 저장소에서 아직 없는 것

- 비개발자가 정말 쉽게 설치하는 경로
  - one-command local install
  - hosted/onboarding path
  - Telegram bot connect path
  - desktop/mobile packaging story
- Telegram을 1급 surface로 다루는 구조
  - Telegram bot UX
  - web/Telegram/device 간 state continuity
  - Telegram security/permission model
- `openclaw`의 편의 기능을 어떤 범위로 가져올지에 대한 정식 제품 판단
  - assistant convenience
  - cron/reminder/background job
  - memory behavior
- `Jarvis + KG` memory architecture를 사용자 제품에 어떻게 섞을지에 대한 정식 설계
  - explicit user memory
  - project/workspace memory
  - code graph / retrieval memory
  - automation memory
- 보안 경계의 제품 수준 정의
  - Telegram bot token / OAuth / user secrets
  - multi-surface auth
  - memory privacy/retention/export/delete

## 4. 새 계획에서 반드시 반영할 사용자 의도

다음 계획 세션은 아래 의도를 정식 제품 요구사항으로 번역해야 한다.

1. 설치 장벽을 극단적으로 낮춘다.
2. Telegram 연동을 부가 기능이 아니라 핵심 surface로 본다.
3. web, PC, mobile, Telegram이 끊기지 않는 하나의 assistant 경험이어야 한다.
4. non-developer vibe-coder가 실제 도움받는 memory architecture를 만든다.
5. `openclaw`식 assistant convenience와 `Jarvis/KG`식 memory intelligence를 조합한다.
6. 보안/권한/주의사항은 부록이 아니라 핵심 설계다.

## 5. 재기획 세션의 비협상 조건

1. `openclaw보다 더 좋다`는 표현은 여전히 `03_WIN_RUBRIC.md`의 증거를 통과하기 전에는 사용하지 않는다.
2. local repo 안에 없는 `openclaw`, `Jarvis`, Telegram-specific 상세가 필요하면 추정으로 메우지 말고 `Assumptions / Needed Inputs`로 분리한다.
3. planning session에서는 구현보다 구조, 우선순위, surface, memory architecture, distribution path를 먼저 고정한다.
4. canonical session docs는 계속 `docs/session-ops/`를 정본으로 쓴다.
5. root mirror docs는 canonical 상태와 동기화한다.

## 6. 다음 planning session이 답해야 하는 핵심 질문

1. 이 제품의 primary user는 누구인가
   - non-developer vibe-coder
   - solo founder/operator
   - developer + non-developer mixed team
2. primary entry surface는 무엇인가
   - Telegram first
   - web first
   - local desktop first
   - hybrid onboarding
3. 설치/배포 전략은 무엇인가
   - local self-host
   - managed cloud
   - Telegram bot first + optional web dashboard
4. memory architecture는 몇 층으로 나눌 것인가
   - user profile/preference
   - conversation/session continuity
   - project/code memory
   - long-term automation memory
5. `openclaw` feature import 범위는 어디까지인가
   - assistant flows
   - cron/reminder/background jobs
   - memory behaviors
6. security baseline은 무엇인가
   - secrets storage
   - Telegram bot token handling
   - OAuth/user identity
   - export/delete/retention
7. MVP와 V1의 경계는 어디인가
8. 현재 repo 구조 안에서 무엇을 재사용하고 무엇을 다시 설계할 것인가

## 7. planning session이 최소로 남겨야 할 산출물

- 사용자 목표를 반영한 새 제품 북극성 문서
- 설치/배포/Telegram/surface 전략 문서
- memory architecture + assistant convenience + security 경계 문서
- 실행 wave / dependency / repo impact 문서

## 8. planning session에서 반드시 읽을 기존 문서

1. `docs/session-ops/03_WIN_RUBRIC.md`
2. `docs/session-ops/04_SYSTEM_ARCHITECTURE.md`
3. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
4. `docs/session-ops/07_AUTH_MEMORY_API_BOOTSTRAP.md`
5. `docs/session-ops/08_ASSISTANT_WEB_SHELL.md`
6. `docs/session-ops/09_MEMORY_PROVENANCE_AND_SYNC.md`
7. `services/assistant-api/README.md`
8. `apps/assistant-web/README.md`
9. `README.md`
