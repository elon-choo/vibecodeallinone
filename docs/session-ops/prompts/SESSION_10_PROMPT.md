# SESSION_10_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S10`이며, 목적은 **구현이 아니라 재기획**이다.

사용자가 직접 밝힌 목표는 아래와 같다.

- 이 오픈소스를 사람들이 아주 쉽게 설치할 수 있게 만든다.
- 텔레그램에 아주 쉽게 연동할 수 있게 만든다.
- PC, 모바일, 텔레그램, 웹 어디서나 쉽게 쓸 수 있게 만든다.
- `openclaw`의 메모리 기능, assistant convenience, cron job류 편의 기능을 제품 전략에 반영한다.
- `엘런자비스 + knowledge graph` 계열의 vibe-coding memory architecture를 적용해 비개발자 코딩 사용자를 돕는다.
- 보안 유의사항은 설계 초기부터 포함한다.

이 세션은 product/architecture/distribution/memory/security 계획을 다시 잠그는 세션이다. **제품 코드 구현을 기본 목표로 삼지 말고 planning package를 만드는 데 집중하라.**

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/README.md`
6. `docs/session-ops/00_MASTER_PLAN.md`
7. `docs/session-ops/01_SESSION_BOARD.md`
8. `docs/session-ops/03_WIN_RUBRIC.md`
9. `docs/session-ops/04_SYSTEM_ARCHITECTURE.md`
10. `docs/session-ops/05_DATA_AUTH_MEMORY_PLAN.md`
11. `docs/session-ops/07_AUTH_MEMORY_API_BOOTSTRAP.md`
12. `docs/session-ops/08_ASSISTANT_WEB_SHELL.md`
13. `docs/session-ops/09_MEMORY_PROVENANCE_AND_SYNC.md`
14. `docs/session-ops/12_REPLAN_CONTEXT.md`
15. `docs/session-ops/handovers/SESSION_10_HANDOVER.md`
16. `services/assistant-api/README.md`
17. `apps/assistant-web/README.md`
18. `README.md`

## 필요하면 추가로 읽을 파일

- `apps/assistant-web/app.js`
- `services/assistant-api/assistant_api/app.py`
- `services/assistant-api/assistant_api/store.py`
- `packages/contracts/openapi/assistant-api.openapi.yaml`
- `scripts/assistant/run_operator_smoke.py`
- `scripts/assistant/run_browser_smoke.py`

## 이번 세션의 핵심 미션

기존 `S01~S09` 산출물을 버리지 말고, 그 위에 사용자 목표 중심의 새 계획을 만든다.

특히 아래 6개 질문에 답하는 계획이어야 한다.

1. **설치/배포**
   - 비개발자가 가장 쉽게 설치하는 경로는 무엇인가?
   - local/self-hosted/managed/Telegram bot onboarding 중 무엇을 MVP 기본으로 둘 것인가?
2. **surface 전략**
   - Telegram, web, PC/mobile의 관계를 어떻게 정의할 것인가?
   - primary entry surface는 무엇이고, secondary surface는 무엇인가?
3. **memory architecture**
   - `openclaw` memory, `Jarvis`, `Knowledge Graph`, current `assistant-api` memory/checkpoint를 어떻게 하나의 구조로 합칠 것인가?
   - 어떤 메모리는 명시 저장이고, 어떤 메모리는 자동 후보이며, 어떤 메모리는 project/code graph memory인가?
4. **assistant convenience**
   - assistant 기능, cron/reminder/background job을 MVP/V1 어디까지 넣을 것인가?
5. **security**
   - Telegram bot token, OAuth, local secrets, memory retention/delete/export, background jobs를 어떤 보안 원칙으로 다룰 것인가?
6. **execution**
   - 무엇을 재사용하고, 무엇을 다시 설계하며, 어떤 wave로 구현할 것인가?

## planning workstreams

### TODO 1. 북극성과 사용자 세분화 재정의
권장 skill/agent:
- `strategic-planner`
- `requirements-analyzer`

산출물:
- primary audience
- JTBD
- success criteria
- `openclaw` 비교 시나리오에서 무엇을 이겨야 하는지

### TODO 2. 설치/배포/온보딩 전략 정의
권장 skill/agent:
- `project-architect`
- `tech-stack-advisor`

산출물:
- 설치 경로 옵션 비교
- 추천 default path
- Telegram onboarding path
- PC/mobile/web packaging 방향

### TODO 3. surface architecture 정의
권장 skill/agent:
- `frontend-developer`
- `node_architect_v1`

산출물:
- Telegram / web / PC/mobile interaction map
- session continuity model
- 어떤 surface가 어떤 기능을 책임지는지

### TODO 4. memory architecture 재설계
권장 skill/agent:
- `code-analyzer`
- `smart-context`
- `codebase-graph`

산출물:
- user memory
- session continuity memory
- project/code memory
- Jarvis/KG/openclaw/current assistant-api memory synthesis
- consent/provenance/retention policy

### TODO 5. assistant convenience + cron/background job 범위 정의
권장 skill/agent:
- `requirements-analyzer`
- `production-scale-launcher`

산출물:
- reminders / cron / background tasks MVP 범위
- 어떤 기능은 Telegram-first인지, web-first인지
- abuse/failure modes

### TODO 6. security baseline 정의
권장 skill/agent:
- `security-shield`
- `threat-modeler-v8`

산출물:
- secrets handling
- Telegram bot token handling
- auth boundary
- memory privacy/export/delete
- operator/user warning set

### TODO 7. 실행 wave와 repo impact 정의
권장 skill/agent:
- `strategic-planner`
- `project-architect`

산출물:
- MVP / V1 / V2 wave
- repo structure impact
- packages/apps/services ownership
- test/evidence gates

## 이번 세션에서 반드시 남겨야 할 문서

1. 갱신된 `docs/session-ops/01_SESSION_BOARD.md`
2. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`
   - 북극성
   - 사용자 정의
   - surface 전략
   - install/distribution 원칙
3. `docs/session-ops/14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`
   - install paths
   - Telegram integration model
   - memory architecture synthesis
   - security baseline
4. `docs/session-ops/15_EXECUTION_WAVES.md`
   - MVP/V1/V2
   - dependency map
   - repo impact
   - evidence/test gates
5. 갱신되거나 교체된 `docs/session-ops/handovers/SESSION_10_HANDOVER.md`
   - planning 결과를 실제 outcome 기준으로 다시 써라
6. 필요하면 `docs/session-ops/prompts/SESSION_11_PROMPT.md`
7. 갱신된 루트 `HANDOVER.md`
8. 갱신된 루트 `NEXT_SESSION_PROMPT.md`

## 강한 제약

1. `openclaw`, `Jarvis`, Telegram 세부 동작을 모르면 지어내지 마라.
   - local repo나 제공된 자료에 없는 경우 `Assumptions`, `Needed Inputs`, `Research Follow-up`으로 분리해라.
2. `openclaw보다 더 좋다`는 표현은 여전히 `03_WIN_RUBRIC.md` 증거 없이 확정 문구로 쓰지 마라.
3. planning session에서는 구현보다 **scope lock / architecture lock / surface lock / memory lock / security lock**이 우선이다.
4. 현재 repo의 `assistant-web`, `assistant-api`, contracts, smoke harness, KG MCP 자산은 재사용 후보로 먼저 평가하라.
5. plan이 바뀌면 먼저 `docs/session-ops/01_SESSION_BOARD.md`의 `Plan Change Log`를 수정하라.

## 세션 종료 조건

이번 세션은 아래가 모두 만족되면 끝난다.

1. 사용자의 새 목표가 planning docs에 명시적으로 반영됐다.
2. easy install / Telegram / cross-surface / memory architecture / assistant convenience / security가 모두 빠짐없이 다뤄졌다.
3. 현재 repo 자산을 재사용할지 버릴지에 대한 판단이 문서화됐다.
4. 다음 구현 세션이 문서만 읽고 바로 움직일 수 있을 정도로 wave와 dependency가 정리됐다.

## 만약 외부 자료가 필요하면

- `openclaw`의 실제 메모리/assistant/cron 설계 근거가 local repo에 없으면 그 사실을 기록하고, 어떤 repo/doc/input이 추가로 필요한지 구체적으로 남겨라.
- `엘런자비스` 설계 세부가 local repo에 없으면 현재 repo의 KG memory 자산과 사용자의 설명만 기준으로 임시 구조를 짜고, 명확한 확인 필요 지점을 따로 적어라.
