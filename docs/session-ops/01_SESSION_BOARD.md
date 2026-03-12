# Session Board

## 1. 현재 상태

- 현재 상태: `post-S30 reminder-policy mini-wave complete / chain paused`
- 현재 저장소: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`
- 외부 리서치 입력: `/Users/elon/Documents/엘런_모바일연동/vibecodeallinone/AI피드백_v3/`
- 최신 handover: `docs/session-ops/handovers/SESSION_30_HANDOVER.md`
- 최신 prompt: `docs/session-ops/prompts/SESSION_30_PROMPT.md`
- orchestrator entrypoint: `.agent-orchestrator/config.json`, `NEXT_SESSION_PROMPT.md` (`SESSION_CHAIN_PAUSE`)

## 2. 잠금된 결정

1. 이 프로젝트의 최종 목표는 `비개발자용 assistant runtime + cross-surface continuity + memory control + evidence-backed quality 운영체계`를 함께 만드는 것이다.
2. `Ralph Loop`는 최종 제품이 아니라 release evidence와 trust를 담당하는 품질 엔진이다.
3. 세션 정본 문서는 `docs/session-ops/` 아래에 둔다.
4. `docs/session-ops/13_PRODUCT_REPLAN_MASTER.md`, `14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`, `15_EXECUTION_WAVES.md`가 S10 이후 제품 방향의 정본이다.
5. `assistant-api`는 계속 사용자 런타임의 단일 백엔드이자 identity/session broker로 유지한다.
6. `assistant-web`는 계속 control plane이며 PC/mobile은 같은 PWA 표면으로 간다.
7. Telegram은 first-class companion surface다. quick capture, reminders, approvals, alerts, resume entry를 맡고 민감 설정 완료와 full memory control은 web/PWA에서 처리한다.
8. 현재 repo의 `assistant-web`, `assistant-api`, `packages/contracts`, `packages/evidence-contracts`, smoke harness, `KG MCP` 자산은 reuse-first다.
9. install 전략은 dual-track이다.
   - fastest user path: managed quickstart + Telegram connect + optional PWA install
   - MVP build priority: one-command self-host reference stack
10. install entrypoints are separated.
   - `scripts/install.sh` -> power-pack developer toolkit install
   - `scripts/assistant/bootstrap_runtime.sh` -> assistant runtime self-host reference stack bootstrap
11. memory architecture는 네 층으로 고정한다.
   - explicit user memory
   - continuity memory
   - workspace/project memory
   - automation memory
12. `KG MCP`는 project/workspace memory와 operator intelligence를 제공하는 support plane으로 유지하고, MVP에서 모든 user request의 mandatory path로 넣지 않는다.
13. background jobs는 export/delete/purge/reminder를 포함한 auditable runtime capability로 승격해야 한다.
14. security baseline은 secrets server-side custody, surface-scoped capability, short-lived linking/handoff token, explicit memory consent, retention/export/delete/purge, auditable jobs를 포함한다.
15. `openclaw`, `Jarvis`, Telegram 세부는 local repo 근거가 없는 한 확정 사실로 쓰지 않고 `Assumptions`, `Needed Inputs`, `Research Follow-up`으로 분리한다.
16. unattended chain은 broad 세션 하나로 밀지 않고 `micro-session chain`으로 분해한다.
   - S11 install/bootstrap
   - S12 contracts/backend
   - S13 web surface
   - S14 smoke/validation
17. 현재 next-wave working default는 `polling-first Telegram self-host`, `separate worker entrypoint`, `additive-only public contract`다.

## 3. 아직 열려 있는 질문

1. `openclaw`의 실제 memory / assistant / cron convenience 범위가 무엇인지
2. `Jarvis` memory architecture의 실제 storage / retrieval / consent 설계가 무엇인지
3. Telegram 운영 모델
   - webhook vs polling
   - group chat scope 여부
   - abuse / moderation 기준
4. managed quickstart의 owner와 hosting path를 언제/누가 맡는지
5. `OpenAI-first`가 public product promise로 계속 유지되는지
6. reminder lifecycle follow-up policy를 어디까지 MVP 이후에 열지
   - recurring reminder support 시점
   - retry / dead-letter 정책
   - snooze / reschedule semantics

## 4. 세션 상태판

| Session | 상태 | 핵심 목적 | 필수 산출물 |
|---|---|---|---|
| S00 | Done | 세션 운영 체계 구축 | `README.md`, `00_MASTER_PLAN.md`, `01_SESSION_BOARD.md`, `SESSION_00_HANDOVER.md`, `SESSION_01_PROMPT.md` |
| S01 | Done | 제품 정의와 승부 기준 고정 | `02_PRODUCT_BRIEF.md`, `03_WIN_RUBRIC.md`, `SESSION_01_HANDOVER.md`, `SESSION_02_PROMPT.md` |
| S02 | Done | 시스템 아키텍처와 워크스트림 분해 | `04_SYSTEM_ARCHITECTURE.md`, `05_DATA_AUTH_MEMORY_PLAN.md`, `SESSION_02_HANDOVER.md`, `SESSION_03_PROMPT.md` |
| S03 | Done | `Ralph Loop` 신뢰도 복구 | `06_RALPH_LOOP_TRUST_MODEL.md`, `SESSION_03_HANDOVER.md`, `SESSION_04_PROMPT.md` |
| S04 | Done | OAuth + 메모리 백엔드 기반 | `07_AUTH_MEMORY_API_BOOTSTRAP.md`, contract package drafts, trust hardening code, handover, next prompt |
| S05 | Done | `assistant-api` runtime + trust publication landing | FastAPI runtime, session middleware, SQLite migration, Ralph Loop bundle publish, handover, next prompt |
| S06 | Done | 비서 앱 UI 셸과 첫 사용 흐름 + auth callback round trip | `apps/assistant-web`, auth callback/provider adapter, shell doc, handover, next prompt |
| S07 | Done | 메모리 provenance/export-delete와 크로스디바이스 hardening | provenance/export code, sync hardening doc, handover, next prompt |
| S08 | Done | live validation 대체 smoke, browser smoke, stale trust polish | operator/browser smoke scripts, stale trust copy, handover, next prompt |
| S09 | Done | live OIDC follow-up 판단과 chain 종료 | live env blocker 확인, stop marker, handover |
| S10 | Done | easy install + Telegram + cross-surface + memory/security replan | `13_PRODUCT_REPLAN_MASTER.md`, `14_INSTALL_TELEGRAM_MEMORY_ARCHITECTURE.md`, `15_EXECUTION_WAVES.md`, updated board, updated handover, `SESSION_11_PROMPT.md` |
| S11 | Done | install story split + assistant runtime bootstrap foundation | README/install split, runtime bootstrap entry, install smoke update, handover, `SESSION_12_PROMPT.md` |
| S12 | Done | contracts + `assistant-api` foundation | contracts/schema/OpenAPI, migration/model/store/app changes, backend tests, handover, `SESSION_13_PROMPT.md` |
| S13 | Done | `assistant-web` surface + browser smoke 정렬 | Telegram link UI, continuity/job state surface, browser smoke update, handover, `SESSION_14_PROMPT.md` |
| S14 | Done | install/Telegram smoke + validation + next-wave sync | install smoke, Telegram mock smoke, validation, handover, next-wave prompt or stop marker |
| S15 | Done | executable worker foundation | worker runtime, purge execution path, reminder persistence skeleton, worker tests, handover, `SESSION_16_PROMPT.md` |
| S16 | Done | Telegram transport foundation | polling runtime, secure Telegram link completion path, transport tests, handover, `SESSION_17_PROMPT.md` |
| S17 | Done | Telegram quick capture + resume backend | quick capture backend, real resume continuity path, backend tests/smoke, handover, `SESSION_18_PROMPT.md` |
| S18 | Done | reminder backend + delivery | reminder runtime API, worker Telegram delivery, audit trail, tests, handover, `SESSION_19_PROMPT.md` |
| S19 | Done | web control plane + browser smoke | runtime/reminder web alignment, browser smoke update |
| S20 | Done | one-command self-host reference stack | stack orchestration, docs, validation |
| S21 | Done | release evidence closeout | final validation, evidence sync, stop marker or closeout |
| S22 | Done | managed quickstart deployment contract | managed quickstart env/secret contract, operator mode/readiness boundary, targeted docs/templates, `SESSION_22_HANDOVER.md`, `SESSION_23_PROMPT.md` |
| S23 | Done | managed quickstart operator/bootstrap path | operator/bootstrap artifacts, install/reference-stack smoke alignment, refreshed docs, `SESSION_23_HANDOVER.md`, `SESSION_24_PROMPT.md` |
| S24 | Done | live provider + real Telegram operator validation | real validation path or blocker artifacts, targeted tests/docs, `SESSION_24_HANDOVER.md`, `SESSION_25_PROMPT.md` |
| S25 | Done | KG memory broker foundation | opt-in workspace/project broker foundation, additive contracts/tests, `SESSION_25_HANDOVER.md`, `SESSION_26_PROMPT.md` |
| S26 | Done | broker opt-in + control-plane alignment | web control-plane alignment, browser smoke, docs refresh, `SESSION_26_HANDOVER.md`, `SESSION_27_PROMPT.md` |
| S27 | Done | later-wave closeout | later-wave evidence/validation/doc sync, explicit chain decision, next prompt or stop marker |
| S28 | Done | reminder follow-up policy contract | additive reminder follow-up contract/state, targeted backend tests/docs, `SESSION_28_HANDOVER.md`, `SESSION_29_PROMPT.md` |
| S29 | Done | follow-up control-plane/operator alignment | browser/operator smoke alignment, docs refresh, `SESSION_29_HANDOVER.md`, `SESSION_30_PROMPT.md` |
| S30 | Done | reminder-policy closeout | evidence/validation/doc sync, explicit chain decision, next prompt or stop marker |

## 5. 재기획 기준 백로그

### P0

- memory broker 방향과 workspace/project memory opt-in boundary 정의
- security baseline을 runtime contract와 operator docs에 반영

### P1

- managed quickstart 또는 hosted reference path
- Telegram reminder / approval / resume UX 고도화
- KG-backed workspace/project memory integration
- install/Telegram release evidence 고도화

### P2

- native desktop/mobile packaging
- shared/team memory
- richer autonomous routines와 multi-project automation

## 6. Plan Change Log

| 날짜 | Session | 변경 내용 | 이유 | 영향 |
|---|---|---|---|---|
| 2026-03-09 | S00 | `docs/session-ops/` 운영 체계를 신설하고 9세션 로드맵을 확정했다 | 기존 `NEXT-SESSION-PROMPT.md` 한 장으로는 장기 세션 운영과 계획 수정 이력이 남지 않음 | 이후 모든 세션은 이 폴더를 정본으로 사용 |
| 2026-03-09 | S01 | MVP 범위를 `GPT OAuth(OpenAI-first) + 클라우드 동기화 우선 메모리 + 웹/PWA 우선`으로 고정하고, 앱은 현 저장소 안의 새 패키지로 확장하기로 정했다 | 제품 정의가 잠기지 않으면 S02 아키텍처와 이후 구현 범위가 계속 흔들릴 위험이 큼 | S02는 인증, 메모리, 패키지 경계를 이 전제 위에서 설계해야 함 |
| 2026-03-09 | S01 | `03_WIN_RUBRIC.md`를 추가해 `openclaw보다 더 좋다`는 표현의 내부 승부 기준을 문서화했다 | 비교 문장이 슬로건으로 남으면 이후 검증과 릴리즈 기준이 모호해짐 | S07~S08의 비교/감사 단계는 이 기준에 맞춰 증거를 남겨야 함 |
| 2026-03-09 | S02 | 사용자 제품 구조를 `assistant-web`, `assistant-api`, `packages/contracts` 중심의 인플레이스 확장 구조로 고정하고, `KG MCP`와 `Ralph Loop`를 지원 평면으로 분리했다 | 기존 저장소의 강점은 유지하되 사용자 런타임의 책임 경계를 먼저 고정해야 이후 구현이 흔들리지 않음 | S03는 품질 엔진 hardening, S04는 auth/memory backend, S05는 web shell 구현으로 바로 이어질 수 있음 |
| 2026-03-09 | S02 | 메모리 설계를 `클라우드 system of record + IndexedDB 로컬 캐시 + session_checkpoint 동기화`로 고정했다 | 메모리 통제와 크로스디바이스 이어쓰기를 동시에 만족시키려면 저장, 캐시, 동기화 단위를 먼저 명확히 해야 함 | S04~S06에서 데이터 모델, sync API, PWA 캐시 정책을 이 전제로 구현해야 함 |
| 2026-03-09 | S03 | `Ralph Loop`를 raw score 루프가 아니라 `release evidence bundle + evidence_summary`를 발행하는 trust plane으로 재정의했다 | 사용자 제품과 품질 엔진을 연결하려면 점수보다 evidence contract가 먼저 고정돼야 함 | S04는 `packages/evidence-contracts`, `assistant-api` evidence lookup, auth/memory backend를 이 계약 위에서 구현해야 함 |
| 2026-03-09 | S03 | trust artifact 공통 metadata와 stage status, manifest/history, Stage 2 `computed_score only` 규칙을 고정했다 | 현재 `self_review.py` override와 느슨한 artifact 파일 구조로는 score integrity를 보장할 수 없음 | 다음 구현 세션은 atomic write, hashing, stale validation, semantic release gate를 우선 도입해야 함 |
| 2026-03-09 | S04 | `packages/contracts`, `packages/evidence-contracts`, `services/assistant-api`를 contract-first bootstrap 구조로 추가하고, `Ralph Loop` P0는 `computed_score only`와 atomic artifact write부터 반영하기로 했다 | 실제 auth/memory runtime을 붙이기 전에 읽기/쓰기 계약과 trust plane 접점을 먼저 고정해야 이후 구현과 UI가 같은 정본을 공유할 수 있음 | S04 산출물은 스키마와 bootstrap 문서가 중심이 되고, 다음 세션은 이를 기준으로 저장소/middleware/runtime을 구현한다 |
| 2026-03-09 | S04 | auth/memory/checkpoint/evidence OpenAPI/JSON Schema 초안과 `assistant-api` bootstrap 문서, `Ralph Loop` artifact helper 및 `computed_score only` hardening을 실제 파일로 반영했다 | 문서 결정만으로는 다음 세션이 바로 web shell과 runtime 구현에 들어가기 어려워 실제 package 경계와 trust hardening hook이 필요했음 | S05는 새 계약을 그대로 소비하는 `assistant-web` shell과 최소 stub/API wiring부터 시작할 수 있다 |
| 2026-03-09 | S05 | 사용자 우선순위에 맞춰 `assistant-web`보다 `assistant-api` runtime과 Ralph Loop trust publication을 먼저 구현하기로 순서를 조정했다 | 계약은 고정됐지만 실제 runtime/middleware/migration과 manifest/history/stale 연결이 비어 있으면 UI 착수가 공중에 뜸 | S05는 backend/trust landing 세션이 되었고, 다음 세션은 이 구현을 소비하는 `assistant-web` shell에 집중한다 |
| 2026-03-09 | S06 | `assistant-web` shell 구현과 auth callback/provider exchange를 같은 세션으로 묶어 end-to-end round trip을 완성했다 | shell이 start route만 호출하고 callback이 비어 있으면 실제 소비 경로 검증이 반쪽으로 남기 때문 | 이후 S07은 provenance/export-delete, cache conflict, live provider validation 같은 hardening에 집중할 수 있다 |
| 2026-03-09 | S07 | memory provenance/export-delete를 실제 contract와 runtime에 올리고, checkpoint sync를 blind overwrite에서 conflict detect + force/restore 모델로 바꿨다 | IndexedDB snapshot과 server checkpoint를 같은 값으로 보면 cross-device 이어쓰기에서 로컬 draft 유실 위험이 크고, memory control도 UI-only 상태로 남기 어렵기 때문 | 이후 S08은 live provider validation, browser E2E, release evidence polish에 집중한다 |
| 2026-03-09 | S08 | 전역 `agent-orchestrator` CLI를 프로젝트에 초기화하고, 루트 mirror docs와 `NEXT_SESSION_PROMPT.md`를 `docs/session-ops/` 정본을 소비하는 안정적인 chained-session entrypoint로 재구성했다. 추가로 `maxSessions=10`, detached watchdog script, macOS launchd template를 붙였다 | 앞으로 여러 worker session이 같은 정본을 읽고 이어지려면 session-specific numbered docs와 별도로 stable root entrypoint가 필요하고, `~/Documents` 경로의 TCC 제약 때문에 launchd 단독보다 현재 세션 권한을 이어받는 detached watchdog가 더 현실적임 | 이후 background/foreground orchestrator 실행이 같은 prompt file과 validation set으로 반복 가능하고, watchdog가 stop marker가 없을 때 체인을 다시 깨운다 |
| 2026-03-09 | S08 | real OIDC env가 없는 상태를 전제로 mock operator smoke와 headless browser smoke를 정본 경로로 추가하고, stale trust fallback copy를 사용자 표면과 API overlay에 반영했다 | 이번 세션의 남은 출시 리스크를 문서-only가 아니라 실제 반복 실행 가능한 증거로 바꾸려면 외부 credential blocker를 정확히 기록하면서도 mock/runtime/browser smoke를 같은 저장소 안에서 재현 가능하게 남겨야 했음 | 이후 S09는 real OIDC credential이 들어오면 live validation만 집중해서 닫을 수 있고, 그렇지 않으면 export retention/purge worker나 stop marker 결정으로 넘어갈 수 있다 |
| 2026-03-09 | S09 | 최신 `agent-orchestrator` 상태와 watchdog/unattended 런타임을 다시 점검한 뒤, real OIDC env가 여전히 없음을 smoke preflight로 재확인하고 chain을 `SESSION_CHAIN_PAUSE`로 닫기로 결정했다 | S09의 목적은 불필요한 세션 반복 없이 실제 live env가 준비됐는지 판단하고, 준비되지 않았으면 supervisor와 stable entrypoint를 명시적으로 멈추는 것이었음 | 이후 자동 세션 체인은 재시작하지 않으며, real OIDC env/policy가 준비될 때만 새 prompt로 재개한다 |
| 2026-03-10 | S10 | 사용자의 새 목표를 기준으로 기존 launch-hardening 중심 체인을 재개방하고, easy install/Telegram/web-mobile/memory-security 재기획을 위한 정본 context, handover, prompt를 새로 만들었다 | 기존 `S01~S09`는 bootstrap/runtime hardening에는 유효하지만 사용자가 지금 원하는 distribution/surface/memory strategy를 충분히 잠그지 못했음 | 다음 세션은 구현보다 planning package 작성에 집중하고, 그 결과로 이후 구현 wave를 다시 정의해야 한다 |
| 2026-03-10 | S10 | 제품 진입 구조를 `web/PWA control plane + Telegram first-class companion surface`로 재정의했다 | 현재 자산을 재사용하면서도 non-developer의 빠른 capture/resume 요구를 충족하려면 rich control plane과 fast-action surface를 분리해야 했음 | 이후 구현은 `assistant-web`를 유지하고 `assistant-api`에 Telegram linking/continuity를 추가하는 방향으로 간다 |
| 2026-03-10 | S10 | install 전략을 `managed quickstart target + one-command self-host MVP priority + separate developer toolkit install`로 재정의했다 | 현재 README/install story는 power-pack developer install에 치우쳐 있어 사용자가 기대한 assistant runtime 설치 경험을 설명하지 못함 | S11은 install story 분리와 self-host reference stack foundation을 우선 구현해야 한다 |
| 2026-03-10 | S10 | memory/security/execution 구조를 `4-layer memory + auditable jobs + surface-scoped security baseline + MVP/V1/V2 waves`로 잠갔다 | `openclaw`/`Jarvis` reference를 추정으로 채우지 않고도 현재 repo 자산과 future input을 연결할 최소 구조가 필요했음 | 이후 구현 세션은 계약, runtime, smoke를 이 구조에 맞춰 확장하고, 외부 reference input은 별도 follow-up으로 받는다 |
| 2026-03-10 | S10 | unattended reliability를 위해 broad `S11`을 `S11~S14 micro-session chain`으로 재분해하고 watchdog stall recovery 기준을 추가했다 | 사용자는 오케스트레이터를 오래 unattended 상태로 돌리는 스타일이고, 넓은 S11 prompt는 두 차례 탐색 단계 stall을 보였음 | 이후 체인은 더 작은 objective 단위로 이어지고, watchdog는 stalled run을 감지해 자동 재시작할 수 있다 |
| 2026-03-10 | S11 | `README.md` install story를 assistant runtime bootstrap과 power-pack developer toolkit으로 분리하고, `scripts/assistant/bootstrap_runtime.sh` 및 install smoke scaffold 검증을 추가했다 | S10에서 잠근 dual-track install 전략을 실제 entrypoint와 smoke로 연결해야 다음 세션이 contracts/backend를 안정적으로 확장할 수 있음 | S12는 새 bootstrap entry를 유지한 채 Telegram/continuity/job contracts와 `assistant-api` foundation만 확장하면 된다 |
| 2026-03-10 | S12 | `packages/contracts`와 `assistant-api` bootstrap을 Telegram link state, checkpoint continuity metadata, auditable runtime jobs로 확장하고, 기존 bootstrap DB를 위한 compat column upgrade path를 추가했다 | S13 web 세션이 기존 shell payload를 깨지 않고 새 backend shape를 소비하려면 contract와 storage foundation을 먼저 안정화해야 했음 | S13은 backend 재설계 없이 UI/browse smoke alignment에만 집중할 수 있다 |
| 2026-03-10 | S13 | `assistant-web`를 Telegram link state, checkpoint continuity metadata, auditable jobs를 소비하는 control plane으로 최소 확장하고 browser smoke를 같은 state에 맞춰 갱신했다 | S12에서 잠근 backend contract를 실제 사용자 표면과 smoke evidence로 연결해야 S14가 closeout validation에 집중할 수 있음 | S14는 install/Telegram smoke completion과 validation/doc sync만 남겨두고, web/backend 재설계 없이 마감 작업에 들어갈 수 있다 |
| 2026-03-10 | S14 | install shell smoke를 structured artifact로 감싸고 Telegram mock smoke를 별도 API-level evidence로 분리한 뒤 targeted validation과 orchestrator dry-run을 통과시켰다. 이후 다음 wave prompt 없이 chain을 `SESSION_CHAIN_PAUSE`로 닫았다 | S14의 남은 과제는 기능 재설계가 아니라 install/Telegram smoke evidence closeout과 session chain 종료 상태를 명확히 남기는 것이었음 | release evidence는 install/operator/browser/Telegram smoke까지 갖추게 되었고, unattended chain은 정의되지 않은 다음 wave로 넘어가지 않는다 |
| 2026-03-10 | post-S14 planning | 다음 구현 wave를 `S15~S21` micro-session chain으로 준비 문서화했다. working decision은 `polling-first Telegram self-host MVP`, `separate worker entrypoint`, `self-host reference stack priority`, `managed quickstart/KG memory broker deferred`다 | 다른 에이전트가 별도 세션에서 바로 이어받으려면 pause 상태를 유지한 채 file-level context와 복붙 prompt가 먼저 필요했음 | 정본 컨텍스트는 `16_POST_S14_NEXT_WAVE_ORCHESTRATION_PLAN.md`, 복붙 prompt는 `17_NEXT_WAVE_PROMPT_PACK.md`에 준비됐고, 체인은 여전히 `SESSION_CHAIN_PAUSE`다 |
| 2026-03-10 | next-wave activation | 사용자가 `S15 -> S21` 순차 세션 오케스트레이션을 명시적으로 지시했고, supervisor가 `S15` 공식 prompt를 canonical/root entrypoint로 승격했다 | prepared draft만 남겨두면 unattended chain이 실제로 시작되지 않으므로 active next session과 stable entry prompt를 먼저 고정해야 했음 | `docs/session-ops/prompts/SESSION_15_PROMPT.md`가 생성됐고 `NEXT_SESSION_PROMPT.md`는 더 이상 pause marker가 아니라 `S15` prompt mirror다 |
| 2026-03-10 | S15 | `assistant-api` runtime job projection을 executable worker foundation으로 승격했다. `runtime_job`에 claim/lease/scheduled execution 필드를 추가하고, separate worker entrypoint와 actual purge execution path, reminder persistence skeleton, worker-focused tests를 붙였다 | Telegram transport나 web UI를 열지 않고도 다음 세션들의 공통 blocker였던 executable background runtime을 먼저 해결해야 했음 | `memory_delete` queued work가 실제 purge로 끝나고 `runtime_job` 상태 전이가 DB에 남게 되었으며, `SESSION_16_PROMPT.md`와 root mirror가 다음 세션 진입점으로 갱신됐다 |
| 2026-03-10 | S16 | polling-first Telegram transport foundation을 추가했다. Telegram bot env, secure token-based link completion, polling cursor persistence, separate polling entrypoint, transport-focused backend tests를 붙였다 | hidden smoke-only completion route만으로는 self-host MVP의 real Telegram linking을 증명할 수 없었고, quick capture/reminder wave 전에 transport/security seam을 먼저 잠가야 했음 | pending Telegram link가 `/start <token>` runtime path로 linked 상태가 될 수 있게 되었고, `SESSION_17_PROMPT.md`와 root mirror가 다음 세션 진입점으로 갱신됐다 |
| 2026-03-10 | S17 | Telegram transport 위에 실제 quick capture/resume continuity path를 올렸다. linked `/start`와 plain text가 모두 runtime에서 checkpoint continuity를 갱신하고, Telegram link state가 최신 resume token ref를 유지하도록 만들었다 | S16까지는 continuity metadata가 테스트/스모크에서만 synthetic write였고, 실제 Telegram inbound path는 link completion 외에 제품 의미가 거의 없었음 | Telegram-originated quick capture가 실제 web/PWA checkpoint를 바꾸게 되었고, `run_telegram_mock_smoke.py`와 Telegram backend tests가 real runtime path를 증명하도록 바뀌었으며, `SESSION_18_PROMPT.md`와 root mirror가 다음 세션 진입점으로 갱신됐다 |
| 2026-03-10 | S18 | reminder lifecycle을 실제 runtime capability로 올렸다. `GET|POST /v1/reminders`와 `DELETE /v1/reminders/{reminder_id}`를 추가하고, worker가 due reminder를 Telegram transport로 보내며 `runtime_job`과 `reminder_delivery`에 delivery success/failure/cancel audit를 남기게 만들었다 | S15의 reminder skeleton은 persistence-only였고, S17의 continuity/Telegram foundation 위에 실제 schedule/delivery path를 연결해야 다음 web/control-plane 세션이 실데이터를 소비할 수 있었음 | reminder 상태가 public contract + worker execution + audit trail로 고정됐고, reminder-focused runtime/worker tests와 full config validation이 통과했으며, `SESSION_19_PROMPT.md`와 root mirror가 다음 세션 진입점으로 갱신됐다 |
| 2026-03-10 | S19 | `assistant-web` control plane을 reminder/runtime 상태에 맞춰 최소 확장했다. Telegram 카드에 reminder queue 요약을 추가하고, 별도 reminder panel에서 schedule/cancel 상태를 additive-only public contract로 제어/표시하게 했으며, browser smoke가 실제 브라우저에서 reminder schedule/cancel과 runtime ledger 반영을 밟도록 갱신했다 | S18까지는 reminder backend와 worker audit가 준비됐지만 web surface와 browser smoke가 새 runtime state를 소비하지 못해 control-plane evidence가 비어 있었음 | reminder 상태가 web shell + browser smoke evidence까지 연결됐고, `SESSION_20_PROMPT.md`와 root mirror가 다음 세션 진입점으로 갱신됐다 |
| 2026-03-10 | S20 | thin bootstrap을 self-host reference stack으로 승격했다. bootstrap workspace가 API/web/worker/Telegram launchers와 `run-assistant-runtime.sh start|stop|restart|status|logs`를 생성하고, install smoke가 real stack start/stop path까지 검증하도록 확장됐으며, README/API/web docs가 같은 operator story로 정리됐다 | S19까지는 runtime pieces가 각각 준비돼 있었지만 operator experience가 scaffold + separate scripts 수준이라 one-command self-host story와 install evidence가 끊겨 있었음 | self-host reference stack이 실제로 one command로 올라가고 멈추게 되었으며, `SESSION_21_PROMPT.md`와 root mirror가 release-evidence closeout 진입점으로 갱신됐다 |
| 2026-03-10 | S21 | install/reference-stack, Telegram runtime, operator, browser smoke와 configured validation을 다시 실행해 evidence artifact를 새로 만들고, canonical docs/root mirrors를 실제 결과에 맞춰 동기화한 뒤 chain을 다시 `SESSION_CHAIN_PAUSE`로 닫았다 | `S21`의 목적은 구현을 넓히는 것이 아니라 현 wave의 release evidence를 현재 상태로 고정하고 다음 공식 wave가 없으면 orchestrator를 명시적으로 멈추는 것이었음 | `S15 -> S21` wave의 closeout evidence가 current 상태로 정리됐고 unattended chain은 새 planning packet이 준비될 때까지 다시 멈춘다 |
| 2026-03-10 | post-S21 planning | 다음 later wave를 `S22~S27` micro-session chain으로 준비 문서화했다. working decision은 `managed quickstart/live-ready productization first`, `KG memory broker second`, `capability-gated live validation`, `reminder follow-up policy deferred`다 | `S21` 이후에는 더 이상 active next session이 없어서, 다른 에이전트가 later wave를 바로 이어받으려면 pause 상태를 유지한 채 scope-locked orchestration plan과 복붙 prompt가 먼저 필요했음 | 정본 later-wave 컨텍스트는 `18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`, 복붙 prompt는 `19_POST_S21_LATER_WAVE_PROMPT_PACK.md`에 준비됐고, 체인은 계속 `SESSION_CHAIN_PAUSE`다 |
| 2026-03-10 | later-wave activation | 사용자가 `S22 -> S27` later-wave 오케스트레이션 재개를 명시적으로 지시했고, supervisor가 Draft Prompt A를 공식 `SESSION_22_PROMPT.md`로 승격해 canonical/root entrypoint를 갱신했다 | prepared later-wave packet만으로는 unattended chain이 실제로 시작되지 않으므로 active next session과 stable prompt mirror를 먼저 고정해야 했음 | `docs/session-ops/prompts/SESSION_22_PROMPT.md`가 생성됐고 `NEXT_SESSION_PROMPT.md`는 `S22` prompt mirror가 되어 later-wave chain이 재시작된다 |
| 2026-03-10 | S22 | managed quickstart deployment contract를 self-host reference stack 위에 additive-only로 정의했다. `scripts/assistant/deployment_contract.py`로 operator mode/readiness surface를 추가하고, self-host bootstrap env에 `ASSISTANT_RUNTIME_OPERATOR_MODE=self-host`를 고정했으며, managed quickstart env template/doc를 `ops/managed/` 아래에 분리했다 | fastest user path를 later wave에서 열기 전에 env/secret contract, operator boundary, readiness surface가 명시돼야 했고, 이 작업은 second runtime path 없이 existing reference stack seam에서 끝내는 것이 안전했음 | `S23`은 이 contract를 바탕으로 managed quickstart bootstrap/operator artifact path와 smoke alignment만 구현하면 되고, self-host reference stack은 그대로 fallback/support path로 유지된다 |
| 2026-03-10 | S23 | managed quickstart contract를 실제 operator/bootstrap path로 승격했다. `scripts/assistant/bootstrap_managed_quickstart.sh`가 same-runtime controller 위에 managed workspace를 생성하고, placeholder-aware readiness blocker, install smoke 확장, `ops/managed/RUNBOOK.md`까지 landing했다 | `S22`까지는 contract/template만 있었고 다른 operator나 automation layer에 건넬 수 있는 generated artifact path와 smoke evidence가 비어 있었음 | `S24`는 packaging을 다시 열지 않고 live provider/Telegram validation foundation과 blocker artifact path에만 집중할 수 있으며, self-host reference stack은 계속 stable fallback으로 유지된다 |
| 2026-03-10 | S24 | live operator validation foundation을 productized했다. `scripts/assistant/smoke_support.py`에 capability-gated provider/Telegram preflight + live attempt helper를 추가하고, `run_operator_smoke.py`가 live provider/live Telegram 상태와 mock smoke를 함께 기록하게 했으며, `run_telegram_live_validation.py`와 managed runbook/docs를 통해 operator가 real env가 있을 때 manual-assisted live validation을 시도할 수 있게 만들었다 | `S23`까지는 managed contract/bootstrap은 있었지만 실제 provider/Telegram 검증 path가 mock evidence와 blocker text에만 머물러 있었고, env가 없을 때도 어떤 command와 artifact가 authoritative한지 더 분명해야 했음 | 현재 세션 env에는 live credential이 없어 `artifacts/operator_smoke/assistant_api_operator_smoke.json`과 `artifacts/telegram_smoke/assistant_api_telegram_live_validation.json`이 explicit blocker 결과로 남았고, `S25`는 이제 KG memory broker backend foundation만 좁게 다루면 된다 |
| 2026-03-10 | S25 | `assistant-api`에 opt-in workspace/project memory broker foundation을 additive-only로 landing했다. optional `memory_broker` seam, workspace opt-in state/audit storage, workspace-scoped query route, OpenAPI/schema/contracts, targeted backend tests를 추가했고 raw Telegram retrieval은 guardrail로 막았다 | `S25`의 목적은 KG를 always-on dependency로 묶지 않으면서 backend/contracts foundation만 먼저 고정하는 것이었고, 이 범위는 web control-plane/browser smoke를 의도적으로 남겨두는 편이 안전했음 | `S26`은 이 backend seam을 소비하는 web control-plane alignment와 browser smoke만 다루면 되며, explicit memory/continuity/runtime behavior는 그대로 유지된다 |
| 2026-03-10 | S26 | `assistant-web`에 web-only broker control panel과 scoped probe state를 추가하고, browser smoke가 `opt-in 저장 -> broker probe -> unavailable audit render` path를 실제로 밟도록 갱신했다. Telegram 카드 copy도 workspace broker가 web-only control임을 명시하도록 정리했다 | `S26`의 목적은 `S25` backend/contracts shape를 바꾸지 않고 control plane과 smoke만 그 shape에 맞추는 것이었고, provider-ready KG integration이나 Telegram admin 확장은 이번 범위 밖이어야 했음 | `S27`은 later-wave evidence/validation/doc closeout과 chain decision만 다루면 되며, reminder/continuity/runtime shell의 기존 동작은 유지된 채 browser evidence도 broker opt-in/control을 포함하게 됐다 |
| 2026-03-10 | S27 | later-wave closeout 세션에서 `run_install_smoke.py`, `run_operator_smoke.py`, `run_telegram_live_validation.py`, `run_browser_smoke.py`를 다시 실행해 artifact를 최신화하고, install shell smoke/targeted broker-operator pytest/configured validation을 모두 통과시킨 뒤 canonical docs와 root mirrors를 실제 결과에 맞춰 동기화했다. live provider/live Telegram은 필요한 managed OIDC/Telegram env가 없어 explicit `blocked` artifact를 유지했고, fully scoped next objective가 없어서 `NEXT_SESSION_PROMPT.md`를 `SESSION_CHAIN_PAUSE`로 다시 닫았다 | `S27`의 목적은 later wave를 다시 넓히는 것이 아니라 evidence, validation, docs, chain decision을 사실대로 마감하는 것이었음 | later-wave artifact set은 `2026-03-10` 기준 current 상태가 되었고, orchestrator는 다음 numbered prompt가 준비될 때까지 pause 상태를 유지한다 |
| 2026-03-11 | post-S27 prompt prep | 원래 제품 목표와 deferred backlog를 다시 대조한 뒤, 다음 단일 objective를 `S28 reminder follow-up policy contract`로 좁혀 `SESSION_28_PROMPT.md`를 준비했다 | live provider/Telegram pass evidence는 외부 managed env가 있어야 전진할 수 있지만, reminder follow-up hardening은 원래 assistant 목적과 맞고 현재 저장소 안에서 바로 진전시킬 수 있는 가장 높은 가치의 좁은 후속 과제였음 | `docs/session-ops/prompts/SESSION_28_PROMPT.md`가 prepared next prompt로 추가됐고, chain은 여전히 `SESSION_CHAIN_PAUSE`로 유지된다 |
| 2026-03-11 | post-S27 orchestration prep | `S28 -> S29 -> S30` reminder-policy mini-wave를 위한 orchestration plan, prompt pack, activation/stall/stop guide를 추가했다 | 다음 세션에 실제 오케스트레이션을 바로 시작하려면 next objective뿐 아니라 session chain, prompt pack, activation rule, monitoring/stall recovery 규칙까지 정리된 packet이 필요했음 | `20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`와 `21_POST_S27_REMINDER_POLICY_PROMPT_PACK.md`가 추가됐고, `S28`~`S30`는 prepared wave로 정리되었지만 chain은 여전히 pause 상태다 |
| 2026-03-12 | post-S27 wave activation | 사용자가 post-`S27` reminder-policy mini-wave 공식 재개를 지시했고, supervisor가 pause marker와 prepared packet 정합성을 확인한 뒤 `docs/session-ops/prompts/SESSION_28_PROMPT.md`를 공식 next prompt로 승격했다 | prepared packet만 유지하면 chain이 실제로 움직이지 않으므로, canonical 상태판을 먼저 active wave 기준으로 갱신하고 stable entry prompt를 `S28` mirror로 전환해야 unattended `S28 -> S29 -> S30` 체인이 같은 범위와 제약을 읽을 수 있었음 | `S28`은 active, `S29`와 `S30`은 queued 상태가 되었고, orchestrator는 reminder follow-up policy hardening wave를 실제 실행할 수 있는 상태가 됐다 |
| 2026-03-12 | S28 | reminder follow-up policy contract를 additive-only로 완료했다. reminder contract에 optional `follow_up_policy`와 explicit `follow_up_state`를 추가하고, runtime job에 `available_at` / `attempt_count` visibility를 열었으며, worker/store에 retry requeue, dead-letter, snooze/reschedule-ready seam과 targeted backend tests를 landed했다 | current reminder lifecycle을 깨지 않고 follow-up state를 explicit/auditable하게 만들려면 UI보다 먼저 backend contract/state와 execution seam을 좁게 고정해야 했음 | `S29`는 이제 `S28` shape를 소비하는 control-plane/operator alignment에만 집중하면 되고, `NEXT_SESSION_PROMPT.md`는 `SESSION_29_PROMPT.md` mirror로 전환된다 |
| 2026-03-12 | S29 | `assistant-web`가 reminder follow-up policy/state를 최소 소비하도록 정렬했다. reminder schedule form에 retry-based `follow_up_policy` 입력을 추가하고, reminder card/Telegram summary/runtime ledger에 follow-up visibility를 열었으며, browser/operator smoke와 operator docs/runbook도 같은 경로를 확인하도록 갱신했다 | `S28`에서 contract/runtime seam은 이미 고정됐으므로, 이 세션은 그 shape를 다시 바꾸지 않고 control-plane/operator/smoke 소비 경로만 최소로 여는 것이 안전했음 | `S30`는 이제 reminder-policy evidence/validation/doc closeout과 chain decision만 다루면 되고, `NEXT_SESSION_PROMPT.md`는 `SESSION_30_PROMPT.md` mirror로 전환된다 |
| 2026-03-12 | S30 | reminder-policy closeout 세션에서 `run_operator_smoke.py`와 `run_browser_smoke.py`를 다시 실행해 operator/browser/browser-screenshot/`e2e_score` artifact를 최신화하고, `.agent-orchestrator/config.json` validation 명령을 모두 통과시킨 뒤 canonical docs와 root mirrors를 실제 결과에 맞춰 동기화했다. live provider/live Telegram은 필요한 managed env가 여전히 없어 explicit `blocked` 상태를 유지했고, fully scoped next objective가 없어서 `NEXT_SESSION_PROMPT.md`를 `SESSION_CHAIN_PAUSE`로 다시 닫았다 | `S30`의 목적은 reminder follow-up policy wave를 더 넓히는 것이 아니라 evidence, validation, docs, chain decision을 사실대로 마감하는 것이었음 | reminder-policy artifact set은 `2026-03-12` 기준 current 상태가 되었고, orchestrator는 다음 scoped numbered prompt가 준비될 때까지 pause 상태를 유지한다 |

## 7. 다음 액션

현재 active next action은 없다.

- latest completed handover:
  - `docs/session-ops/handovers/SESSION_30_HANDOVER.md`
- latest completed prompt:
  - `docs/session-ops/prompts/SESSION_30_PROMPT.md`
- `NEXT_SESSION_PROMPT.md`는 이제 stop marker `SESSION_CHAIN_PAUSE`를 담고 있다.
- active reminder-policy wave:
  - none
- completed reminder-policy sessions:
  - `S28` reminder follow-up policy contract
  - `S29` follow-up control-plane/operator alignment
  - `S30` reminder-policy closeout
- completed later-wave sequence:
  - `S22` managed quickstart deployment contract
  - `S23` managed quickstart operator/bootstrap path
  - `S24` live provider + real Telegram operator validation
  - `S25` KG memory broker foundation
  - `S26` broker opt-in + control-plane alignment
  - `S27` later-wave closeout
- working defaults:
  - managed quickstart/live-ready productization first
  - KG memory broker second
  - live validation은 env가 없으면 blocker artifact를 남기고 fake success를 금지
  - KG memory broker는 opt-in, workspace-scoped, additive-only
- latest reminder-policy orchestration packet:
  - `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
  - `docs/session-ops/21_POST_S27_REMINDER_POLICY_PROMPT_PACK.md`
  - `docs/session-ops/prompts/SESSION_30_PROMPT.md`
- reminder-policy mini-wave는 `S28 -> S30`까지 완료됐다.
- resume rule:
  - 새 numbered prompt는 single fully scoped post-wave objective가 준비됐을 때만 만든다.
- managed quickstart/live validation 재개, KG memory broker 재설계, broad reminder planner UI redesign은 이번 wave 범위 밖이다.
- live pass evidence는 여전히 외부 managed OIDC/Telegram env가 준비돼야 추가될 수 있다.
- stalled run 복구가 아니라 새 wave activation이 필요하면 `20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`와 후속 planning packet을 먼저 갱신한다.
- later-wave closeout 기준 정본 문서는 `docs/session-ops/18_POST_S21_LATER_WAVE_ORCHESTRATION_PLAN.md`, `docs/session-ops/handovers/SESSION_27_HANDOVER.md`, 그리고 이 상태판이다.
- 계획이 바뀌면 먼저 이 파일의 `Plan Change Log`를 수정한다.
