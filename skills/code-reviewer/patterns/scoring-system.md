# Scoring System

## 점수 계산

```typescript
interface ReviewScore {
  total: number;
  breakdown: CategoryScore[];
  grade: 'A' | 'B' | 'C' | 'D' | 'F';
  passed: boolean;
}

interface CategoryScore {
  category: string;
  score: number;
  maxScore: number;
  weight: number;
  issues: string[];
}

function calculateReviewScore(review: ReviewResult): ReviewScore {
  const categories: CategoryScore[] = [
    {
      category: 'Code Quality',
      maxScore: 100,
      weight: 0.25,
      score: calculateCodeQualityScore(review),
      issues: review.codeQualityIssues,
    },
    {
      category: 'Security',
      maxScore: 100,
      weight: 0.25,
      score: calculateSecurityScore(review),
      issues: review.securityIssues,
    },
    {
      category: 'Test Coverage',
      maxScore: 100,
      weight: 0.20,
      score: calculateTestScore(review),
      issues: review.testIssues,
    },
    {
      category: 'Documentation',
      maxScore: 100,
      weight: 0.15,
      score: calculateDocScore(review),
      issues: review.docIssues,
    },
    {
      category: 'Naming & Style',
      maxScore: 100,
      weight: 0.15,
      score: calculateStyleScore(review),
      issues: review.styleIssues,
    },
  ];

  // 가중 평균
  const total = categories.reduce(
    (sum, cat) => sum + (cat.score * cat.weight),
    0
  );

  // 등급 결정
  let grade: ReviewScore['grade'];
  if (total >= 90) grade = 'A';
  else if (total >= 80) grade = 'B';
  else if (total >= 70) grade = 'C';
  else if (total >= 60) grade = 'D';
  else grade = 'F';

  return {
    total: Math.round(total),
    breakdown: categories,
    grade,
    passed: total >= 70 && !hasBlockingIssues(review),
  };
}
```

## 카테고리별 점수 계산

```typescript
function calculateCodeQualityScore(review: ReviewResult): number {
  let score = 100;

  // Code Smell 감점
  score -= review.codeSmells.filter(s => s.severity === 'critical').length * 15;
  score -= review.codeSmells.filter(s => s.severity === 'major').length * 10;
  score -= review.codeSmells.filter(s => s.severity === 'minor').length * 5;

  // 복잡도 감점
  const maxComplexity = Math.max(...review.complexityScores.map(c => c.complexity));
  if (maxComplexity > 20) score -= 20;
  else if (maxComplexity > 15) score -= 15;
  else if (maxComplexity > 10) score -= 10;

  // 파일 길이 감점
  if (review.fileLines > 500) score -= 20;
  else if (review.fileLines > 300) score -= 10;

  return Math.max(0, score);
}

function calculateSecurityScore(review: ReviewResult): number {
  let score = 100;

  // 치명적 보안 이슈는 점수 0
  if (review.securityIssues.some(i => i.severity === 'critical')) {
    return 0;
  }

  score -= review.securityIssues.filter(i => i.severity === 'high').length * 25;
  score -= review.securityIssues.filter(i => i.severity === 'medium').length * 15;
  score -= review.securityIssues.filter(i => i.severity === 'low').length * 5;

  return Math.max(0, score);
}

function calculateTestScore(review: ReviewResult): number {
  let score = 100;

  // 커버리지 기반
  const coverage = review.testCoverage;
  if (coverage < 80) score -= (80 - coverage);

  // Fake 테스트 감점
  score -= review.fakeTests.length * 15;

  // 테스트 없음
  if (!review.hasTests) score = 0;

  return Math.max(0, score);
}

function calculateDocScore(review: ReviewResult): number {
  let score = 100;
  score -= review.missingDocs.length * 10;
  score -= review.incompleteDocs.length * 5;
  return Math.max(0, score);
}

function calculateStyleScore(review: ReviewResult): number {
  let score = 100;
  score -= review.namingViolations.length * 5;
  score -= review.eslintWarnings * 2;
  return Math.max(0, score);
}
```

## 등급 기준

```yaml
Grade_Criteria:
  A: "90-100점"
    description: "우수"
    action: "즉시 머지 가능"

  B: "80-89점"
    description: "양호"
    action: "마이너 이슈 수정 후 머지"

  C: "70-79점"
    description: "보통"
    action: "개선 필요, 조건부 승인"

  D: "60-69점"
    description: "미흡"
    action: "대폭 수정 필요"

  F: "60점 미만"
    description: "불합격"
    action: "전면 재작성 필요"

Pass_Criteria:
  minimum_score: 70
  blocking_issues: 0
  critical_security: 0
  fake_tests: 0
```

## 리뷰 출력 형식

```markdown
## 🔍 Self-Review Report

### 📊 Overall Score: 82/100 (Grade: B)

| Category | Score | Weight | Status |
|----------|-------|--------|--------|
| Code Quality | 85/100 | 25% | ✅ |
| Security | 90/100 | 25% | ✅ |
| Test Coverage | 75/100 | 20% | ⚠️ |
| Documentation | 70/100 | 15% | ⚠️ |
| Naming & Style | 90/100 | 15% | ✅ |

### ⚠️ Issues Found

#### High Priority
1. **Missing edge case test** (Line 45-50)

#### Medium Priority
1. **Magic number** (Line 23) - Use named constant

### ✅ Verdict: Approved with conditions
```
