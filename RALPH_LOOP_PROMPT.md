# Ralph Loop v5 Protocol — Claude Code Native Auto-Loop

> 새 Claude Code 세션에서 아래 프롬프트를 그대로 붙여넣으세요.

---

```
프로젝트: /Users/elon/Documents/elon_opensource/claude-code-power-pack/

## 작업: Ralph Loop v5 — 90점 도달 자동 루프

이 프로젝트의 품질 루프를 Claude Code 세션 안에서 직접 돌려줘.
외부 `claude -p` 호출 없이, 너 자신이 scan → review → fix → verify 루프를 반복한다.

### 핵심 변경 (v4 → v5)

| 항목 | v4 (기존) | v5 (신규) |
|------|-----------|-----------|
| 리뷰 | claude -p × 7회 ($4-5/round) | Claude Code가 직접 파일 읽고 리뷰 |
| 수정 | claude -p × 3회 (fresh context) | Edit 도구로 직접 수정 (컨텍스트 유지) |
| E2E | 0/20 하드코딩 | benchmark + pytest + lint + smoke = 20점 |
| 루프 | Python orchestrator | Claude Code 자체 while 루프 |

### 실행 프로토콜

score = 0
while score < 90:

  #### Step 1: SCAN — 현재 점수 확인
  python3 scripts/ralphloop/loop_runner.py --rescan --run-e2e

  #### Step 2: READ — 액션플랜 확인
  출력된 JSON에서 weakest_areas 확인.
  가장 점수가 낮은 영역부터 처리.

  #### Step 3: FIX — 직접 코드 수정
  - Read 도구로 해당 파일 읽기
  - 문제 파악 후 Edit 도구로 수정
  - 테스트 실행하여 검증: pytest kg-mcp-server/tests/ -x -q

  #### Step 4: SELF-REVIEW — 수정한 영역 셀프 리뷰
  python3 scripts/ralphloop/self_review.py --perspective {영역} --template
  → 출력된 체크리스트를 직접 채워서 저장
  → 결과를 artifacts/reviews/review_{영역}.json에 저장

  #### Step 5: RE-SCAN — 점수 재확인
  python3 scripts/ralphloop/loop_runner.py --rescan --run-e2e

  #### Step 6: COMMIT — 점수 개선 시 커밋
  개선 확인되면:
    git add -u && git commit -m "ralph-loop-v5: {영역} +{점수}pts"

  #### Step 7: 판단
  - 점수 개선됨 → Step 1로 복귀
  - 개선 없음 → 다른 영역으로 전환
  - 3라운드 연속 개선 없음 → 중단하고 현황 보고

### 점수 체계 (100점 만점)

| Stage | 점수 | 측정 방법 |
|-------|------|-----------|
| Stage 1: Machine Gates | 30 | G0~G8 자동 스캔 (run.py) |
| Stage 2: AI Review | 30 | 7개 관점 셀프 리뷰 (self_review.py) |
| Stage 3: E2E Validation | 20 | benchmark + pytest + lint + smoke (t3_benchmark.py --e2e-score) |
| Stage 4: Release Gate | 20 | README, LICENSE, CHANGELOG 등 (run.py) |

### Stage 2 셀프 리뷰 방법

7개 관점 각각에 대해:
1. `python3 scripts/ralphloop/self_review.py --perspective {name} --template` 실행
2. 출력된 체크리스트의 각 항목을 실제 코드를 읽으며 PASS/FAIL/PARTIAL 채우기
3. finding에 구체적 파일:라인 참조 기록
4. 0-10 점수 부여
5. artifacts/reviews/review_{name}.json에 저장

관점 목록:
- code_quality: 에러 처리, 타입 안전, 리소스 정리
- security: 인증, 인젝션, 시크릿, 접근 제어
- testing: 테스트 커버리지, CI, 테스트 품질
- architecture: 모듈 분리, 확장성, 파이프라인
- documentation: README, API 문서, 인라인 문서
- packaging: 의존성, 설치, 버전 관리
- ux: CLI 경험, 에러 메시지, 온보딩

### Stage 3 E2E 점수 해제 방법

python3 scripts/ralphloop/e2e/t3_benchmark.py --e2e-score

4가지 체크 (각 5점):
1. 벤치마크 실행 성공 (10개 쿼리)
2. pytest 전체 PASS
3. ruff lint 0 errors
4. server.py import smoke test

### 파일 구조

scripts/ralphloop/
├── run.py              ← 게이트 스캔 + 점수 (Stage 1+2+3+4 통합)
├── loop_runner.py      ← 통합 점수 + 액션플랜 JSON
├── self_review.py      ← 셀프 리뷰 프레임워크
├── orchestrator.py     ← 기존 외부 호출용 (유지)
└── e2e/
    └── t3_benchmark.py ← 벤치마크 + E2E 점수

artifacts/
├── gates.json          ← 게이트 결과
├── e2e_score.json      ← E2E 점수
├── report.md           ← 헬스 리포트
└── reviews/            ← 7개 관점 리뷰 JSON

### 현재 상태 (최근 실행 기준)
- Stage 1 (Gates): 30/30 PASS
- Stage 4 (Release): 20/20 PASS
- Stage 2 (AI Review): ~16/30 (평균 5.3/10, CRITICAL 이슈 9개)
- Stage 3 (E2E): 0/20 (미실행 → 이제 실행 가능)
- 총점: ~66/100

### 목표
1. Stage 3 E2E 실행하여 0→15~20점 해제
2. AI Review CRITICAL 이슈 수정하여 16→24점
3. 총점 90점 도달

### 우선순위
1. E2E 실행 (가장 빠른 점수 상승: +15~20)
2. testing 관점 개선 (현재 4/10)
3. code_quality CRITICAL 이슈 수정
4. security CRITICAL 이슈 수정
5. 나머지 관점 개선

실행 후 매 라운드 점수 변화를 테이블로 보여줘.
```
