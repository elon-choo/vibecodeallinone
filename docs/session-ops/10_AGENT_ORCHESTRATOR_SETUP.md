# S08 Agent Orchestrator Setup

## 1. Purpose

이 문서는 전역 `agent-orchestrator` CLI를 이 저장소에서 안정적으로 쓰기 위한 프로젝트 로컬 설정을 정리한다.

핵심 목표는 두 가지다.

1. `docs/session-ops/` 정본 문서를 유지한다.
2. 오케스트레이터는 stable root entrypoint만 읽어도 다음 worker session을 안전하게 이어갈 수 있게 한다.

## 2. What Was Added

- `.agent-orchestrator/config.json`
- root mirror docs
  - `PROJECT_AUDIT.md`
  - `MASTER_PLAN.md`
  - `SESSION_OPERATIONS.md`
  - `HANDOVER.md`
  - `NEXT_SESSION_PROMPT.md`
- repo-local watchdog scripts
  - `scripts/orchestration/ensure_agent_orchestrator.sh`
  - `scripts/orchestration/watchdog_loop.sh`
  - `scripts/orchestration/start_watchdog_loop.sh`
  - `scripts/orchestration/stop_watchdog_loop.sh`
  - `scripts/orchestration/start_unattended_run.sh`
  - `scripts/orchestration/stop_unattended_run.sh`
- macOS launchd template
  - `ops/launchd/com.elon.claude-code-power-pack.agent-orchestrator.plist`
- copy-paste prompt
  - `docs/session-ops/11_AGENT_ORCHESTRATOR_PROMPT.md`

## 3. Source Of Truth Mapping

- canonical plan: `docs/session-ops/00_MASTER_PLAN.md`
- canonical board: `docs/session-ops/01_SESSION_BOARD.md`
- canonical handover: latest file under `docs/session-ops/handovers/`
- canonical prompt: latest file under `docs/session-ops/prompts/`

Root mirror docs are not independent planning artifacts.
They are stable orchestrator entrypoints that must be kept in sync with the canonical docs above.

## 4. Config Decisions

### Prompt flow

- `initialPromptFile`: `NEXT_SESSION_PROMPT.md`
- `nextPromptFile`: `NEXT_SESSION_PROMPT.md`

이렇게 고정한 이유:

- numbered prompt 파일은 매 세션 바뀐다
- 오케스트레이터는 stable path가 있어야 loop를 계속 이어가기 쉽다
- worker session은 canonical prompt를 만든 뒤 root `NEXT_SESSION_PROMPT.md`도 같은 상태로 갱신해야 한다

### Validation

현재 기본 validation:

1. `ruff check services/assistant-api/assistant_api/*.py tests/test_assistant_api_runtime.py`
2. `node --check apps/assistant-web/app.js`
3. `python3 -m pytest tests/test_ralphloop_artifact_io.py tests/test_ralphloop_trust_bundle.py tests/test_assistant_api_runtime.py -q`

### Session cap

- `maxSessions`: `20`
- watchdog는 체인이 멈춰도 stop marker가 없으면 다시 `agent-orchestrator start --max-sessions 20`을 호출한다

### Stall recovery

- watchdog는 running 상태라도 active worker log가 일정 시간 갱신되지 않으면 stall로 보고 재시작을 시도한다
- 기본 기준:
  - watch interval: `120s`
  - stall threshold: `240s`
- 환경변수:
  - `AGENT_ORCHESTRATOR_WATCH_INTERVAL_SECONDS`
  - `AGENT_ORCHESTRATOR_STALL_SECONDS`
  - `AGENT_ORCHESTRATOR_MAX_SESSIONS`

### Stop markers

아래 문자열 중 하나가 `NEXT_SESSION_PROMPT.md`에 들어가면 체인을 멈출 수 있다.

- `SESSION_CHAIN_COMPLETE`
- `NO_FURTHER_SESSION`
- `ORCHESTRATOR_STOP`
- `SESSION_CHAIN_PAUSE`

## 5. Recommended Commands

### Dry run

```bash
agent-orchestrator run --dry-run
```

### Start resilient detached watchdog

```bash
scripts/orchestration/start_watchdog_loop.sh
```

### Start 10-hour unattended run

```bash
scripts/orchestration/start_unattended_run.sh
```

### Foreground chain

```bash
agent-orchestrator run
```

### Background chain

```bash
agent-orchestrator start --max-sessions 20
```

### Inspect status

```bash
agent-orchestrator status
```

```bash
ps -p "$(cat .agent-orchestrator/runtime/watchdog-loop.pid)" -o pid=,etime=,command=
```

### Stop background run

```bash
agent-orchestrator stop
```

```bash
scripts/orchestration/stop_watchdog_loop.sh
```

```bash
scripts/orchestration/stop_unattended_run.sh
```

## 6. Autonomy Strategy

### Active path now

현재 실제로 신뢰할 수 있는 무인 실행 경로는 detached watchdog loop다.

- 이유:
  - 이 저장소는 `~/Documents/` 아래에 있다
  - macOS `launchd` background job은 현재 TCC 때문에 이 경로 접근이 막힌다
- 현재 세션에서 시작한 detached watchdog는 이미 접근 가능한 컨텍스트를 유지한 채 계속 재기동을 시도할 수 있다
- 10시간 단위 무인 실행이 필요하면 `start_unattended_run.sh`가 watchdog와 `caffeinate`를 함께 올려 잠자기 진입도 막는다

### Optional path

`launchd` plist도 같이 만들었지만, repo가 `~/Documents` 아래인 현재 구조에서는 바로 성공하지 않을 수 있다.
repo를 TCC 영향을 덜 받는 경로로 옮기거나 별도 권한 정책을 확보하면 그때 `launchd` 경로를 다시 붙이는 것이 맞다.

## 7. Worker Session Rules

모든 orchestrated worker session은 종료 전에 아래를 반드시 수행해야 한다.

1. canonical docs 갱신
   - `docs/session-ops/01_SESSION_BOARD.md`
   - latest handover
   - next prompt
2. root mirror 갱신
   - `HANDOVER.md`
   - `NEXT_SESSION_PROMPT.md`
   - 필요 시 `PROJECT_AUDIT.md`, `MASTER_PLAN.md`
3. `.agent-orchestrator/config.json` validation 실행

## 8. Micro-Session Rule

unattended chain에서는 broad epic 하나를 한 세션에 몰지 않는다.

권장 분해 순서:

1. install/bootstrap
2. contracts/backend
3. web surface
4. smoke/validation

## 9. Current Next Step

현재 root orchestrator prompt는 `S11` micro-session을 가리킨다.

즉시 다음으로 수행할 명령은 보통 아래 둘 중 하나다.

```bash
scripts/orchestration/start_unattended_run.sh
```
