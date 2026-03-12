# Agent Orchestrator Copy Prompt

아래 프롬프트를 다음 세션에서 그대로 붙여 넣으면 된다.

```text
`agent-orchestrator` 스킬을 사용해 이 저장소의 전역 오케스트레이션 상태를 확인하고 이어서 작업해.

프로젝트는 `/Users/elon/Documents/elon_opensource/claude-code-power-pack` 이고, stable entrypoint는 아래 파일들이다.
- `PROJECT_AUDIT.md`
- `MASTER_PLAN.md`
- `SESSION_OPERATIONS.md`
- `HANDOVER.md`
- `NEXT_SESSION_PROMPT.md`

먼저 아래를 확인해.
1. `agent-orchestrator status`
2. `.agent-orchestrator/config.json`
3. `docs/session-ops/01_SESSION_BOARD.md`
4. 최신 canonical handover / prompt

그 다음 규칙대로 진행해.
- 필요하면 `scripts/orchestration/start_watchdog_loop.sh`로 detached watchdog 상태를 복구해.
- 장시간 무인 실행이 필요하면 `scripts/orchestration/start_unattended_run.sh` 상태도 확인해.
- canonical docs는 `docs/session-ops/`를 정본으로 유지해.
- 세션 종료 전에는 canonical docs와 root mirror docs를 둘 다 동기화해.
- validation은 `.agent-orchestrator/config.json`에 있는 명령을 사용해.
- 더 이어갈 세션이 없으면 `NEXT_SESSION_PROMPT.md`에 stop marker 한 줄만 남겨.
- unattended chain이면 install/bootstrap, backend, web, smoke/validation 순서의 micro-session으로 쪼개.
- active worker가 stalled 상태면 최신 `runner.stderr.log`와 `last-message.txt`를 보고 재시작해.

현재 목표는 `NEXT_SESSION_PROMPT.md`에 적힌 최신 세션 목표를 그대로 수행하는 것이다.
```
