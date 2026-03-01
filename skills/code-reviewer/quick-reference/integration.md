# Skill Integration

## 스킬 연동 매트릭스

```yaml
Skill_Integration:
  tdd-guardian:
    trigger: "테스트 관련 코드 발견 시"
    actions:
      - "Fake Test 패턴 검사 위임"
      - "테스트 커버리지 확인"
      - "테스트 품질 점수 계산"

  security-shield:
    trigger: "보안 관련 패턴 발견 시"
    actions:
      - "OWASP Top 10 검사 위임"
      - "하드코딩 시크릿 탐지"
      - "입력 검증 확인"

  monorepo-architect:
    trigger: "Import/의존성 변경 시"
    actions:
      - "의존성 방향 검증"
      - "순환 참조 검사"
      - "경로 별칭 확인"

  api-first-design:
    trigger: "API 관련 코드 변경 시"
    actions:
      - "응답 포맷 일관성 확인"
      - "Swagger 문서화 확인"
      - "에러 코드 체계 확인"
```

## 통합 리뷰 플로우

```typescript
async function integratedReview(
  code: string,
  context: ReviewContext
): Promise<IntegratedReviewResult> {
  const results: IntegratedReviewResult = {
    codeReview: null,
    tddReview: null,
    securityReview: null,
    archReview: null,
    apiReview: null,
    aggregatedScore: 0,
  };

  // 1. 기본 코드 리뷰 (항상 실행)
  results.codeReview = await runCodeReview(code, context);

  // 2. 테스트 관련 코드가 있으면 TDD Guardian 호출
  if (hasTestRelatedCode(code) || context.fileType === 'test') {
    results.tddReview = await callTddGuardian(code);
  }

  // 3. 보안 관련 패턴이 있으면 Security Shield 호출
  if (hasSecurityRelatedCode(code)) {
    results.securityReview = await callSecurityShield(code);
  }

  // 4. Import/의존성 변경이 있으면 Monorepo Architect 호출
  if (hasImportChanges(context)) {
    results.archReview = await callMonorepoArchitect(code, context);
  }

  // 5. API 관련 코드가 있으면 API First Design 호출
  if (hasApiRelatedCode(code)) {
    results.apiReview = await callApiFirstDesign(code);
  }

  // 6. 점수 집계
  results.aggregatedScore = aggregateScores(results);

  return results;
}
```

## 점수 집계

```typescript
function aggregateScores(results: IntegratedReviewResult): number {
  const scores: { score: number; weight: number }[] = [];

  if (results.codeReview) {
    scores.push({ score: results.codeReview.score, weight: 0.30 });
  }
  if (results.tddReview) {
    scores.push({ score: results.tddReview.score, weight: 0.25 });
  }
  if (results.securityReview) {
    scores.push({ score: results.securityReview.score, weight: 0.25 });
  }
  if (results.archReview) {
    scores.push({ score: results.archReview.score, weight: 0.10 });
  }
  if (results.apiReview) {
    scores.push({ score: results.apiReview.score, weight: 0.10 });
  }

  const totalWeight = scores.reduce((sum, s) => sum + s.weight, 0);
  const weightedSum = scores.reduce((sum, s) => sum + s.score * s.weight, 0);

  return Math.round(weightedSum / totalWeight);
}
```

## 통합 리뷰 출력

```markdown
## 🔍 Integrated Code Review Report

### 📊 Overall Score: 85/100 (Grade: B)

---

### 1. Code Quality (30% weight)
**Score: 88/100** ✅

| Check | Status | Details |
|-------|--------|---------|
| Complexity | ✅ Pass | Max: 8 |
| File Length | ✅ Pass | 156 lines |
| Code Smells | ⚠️ 1 issue | 1 minor |

---

### 2. TDD Guardian (25% weight)
**Score: 80/100** ⚠️

| Check | Status | Details |
|-------|--------|---------|
| Coverage | ⚠️ 75% | Target: 80% |
| Fake Tests | ✅ 0 | None |

---

### 3. Security Shield (25% weight)
**Score: 90/100** ✅

| Check | Status |
|-------|--------|
| Hardcoded Secrets | ✅ Pass |
| Input Validation | ✅ Pass |

---

### 4. Architecture (10% weight)
**Score: 85/100** ✅

| Check | Status |
|-------|--------|
| Dependency Direction | ✅ Pass |
| Circular Dependencies | ✅ Pass |

---

### 5. API Design (10% weight)
**Score: 82/100** ⚠️

| Check | Status |
|-------|--------|
| Response Format | ✅ Pass |
| Error Handling | ⚠️ Missing |

---

### 🎯 Summary

**Must Fix (Before Merge):**
1. Add network timeout test case
2. Add @ApiResponse for 500 status

**Should Fix (Recommended):**
1. Extract validation logic
2. Sanitize user input

**Verdict: Approved with Conditions**
```
