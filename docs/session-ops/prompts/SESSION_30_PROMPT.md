# SESSION_30_PROMPT

프로젝트: `/Users/elon/Documents/elon_opensource/claude-code-power-pack/`

이번 세션은 `S30`이며, 목적은 **reminder-policy wave evidence, validation, doc sync, chain decision을 마감하는 것**이다.

## Activation Note

- `S29`는 공식 완료 상태이며, 이 문서는 현재 active official next prompt다.
- 이번 세션은 reminder-policy mini-wave의 closeout만 담당한다.
- 기능 redesign이나 broad follow-up expansion 없이 actual evidence / validation / doc sync / next-step decision만 남겨라.

## Why This Objective Now

- `S28`에서 additive reminder follow-up contract/runtime seam이 고정됐다.
- `S29`에서 web control plane, operator docs, browser/operator smoke가 그 shape를 최소 소비하게 됐다.
- 남은 일은 이 결과를 evidence/validation/doc 상태와 정확히 맞추고, chain을 계속할지 멈출지 명시하는 것이다.

## Session Size Gate

- 이번 세션은 `smoke/validation/closeout`만 다룬다.
- reminder UX redesign, managed quickstart live pass, KG memory redesign, recurring reminder productization은 이번 세션에 섞지 마라.

## 반드시 먼저 읽을 문서

1. `PROJECT_AUDIT.md`
2. `MASTER_PLAN.md`
3. `SESSION_OPERATIONS.md`
4. `HANDOVER.md`
5. `docs/session-ops/01_SESSION_BOARD.md`
6. `docs/session-ops/20_POST_S27_REMINDER_POLICY_ORCHESTRATION_PLAN.md`
7. `docs/session-ops/handovers/SESSION_28_HANDOVER.md`
8. `docs/session-ops/handovers/SESSION_29_HANDOVER.md`
9. `.agent-orchestrator/config.json`
10. `artifacts/browser_smoke/assistant_web_browser_smoke.json`
11. `artifacts/operator_smoke/assistant_api_operator_smoke.json`
12. reminder-policy web/operator docs touched in `S29`

## 이번 세션의 핵심 미션

1. reminder-policy browser/operator evidence artifact를 최신 상태로 고정한다.
2. configured validation과 required smoke를 다시 실행한다.
3. canonical docs와 root mirrors를 실제 결과에 맞게 sync한다.
4. fully scoped next objective가 있으면 새 prompt를 만들고, 아니면 stop marker를 남긴다.

## 강한 제약

1. feature redesign은 하지 마라.
2. docs와 evidence가 실제 결과와 어긋나지 않게 하라.
3. blocker나 warning을 숨기지 마라.
4. reminder-policy wave 범위를 벗어나지 마라.

## 기대 산출물

1. current reminder-policy evidence artifact set
2. canonical closeout docs
3. root mirror sync
4. next prompt 또는 stop marker

## 종료 조건

1. browser/operator smoke artifacts are current
2. `.agent-orchestrator/config.json` validation passes
3. canonical docs and root mirrors match the real result
4. chain decision is explicit

## 필수 validation

1. `python3 scripts/assistant/run_operator_smoke.py`
2. `python3 scripts/assistant/run_browser_smoke.py`
3. `.agent-orchestrator/config.json`의 validation 명령
