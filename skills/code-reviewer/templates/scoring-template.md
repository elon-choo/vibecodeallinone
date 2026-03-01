# Scoring System Template

## Score Calculation

### Weighted Categories

```typescript
interface ScoreWeights {
  codeQuality: 25;      // SOLID, Clean Code, DRY
  security: 25;         // OWASP, vulnerabilities
  testCoverage: 20;     // Coverage %, test quality
  documentation: 15;    // Comments, API docs
  namingStyle: 15;      // Conventions, readability
}

function calculateOverallScore(categoryScores: CategoryScores): number {
  const weights: ScoreWeights = {
    codeQuality: 25,
    security: 25,
    testCoverage: 20,
    documentation: 15,
    namingStyle: 15,
  };

  let total = 0;
  for (const [category, weight] of Object.entries(weights)) {
    total += categoryScores[category] * (weight / 100);
  }

  return Math.round(total);
}
```

---

## Category Scoring Rubrics

### Code Quality (25%)

| Score | Criteria |
|-------|----------|
| 25 | No code smells, all SOLID principles followed |
| 20-24 | Minor issues (1-2 small code smells) |
| 15-19 | Moderate issues (3-5 code smells) |
| 10-14 | Significant issues (multiple violations) |
| 0-9 | Major problems (rewrite needed) |

**Deductions**:
- Long method (>20 lines): -2
- God class: -5
- Duplicate code: -3
- High complexity (>10): -3
- SOLID violation: -4

---

### Security (25%)

| Score | Criteria |
|-------|----------|
| 25 | No vulnerabilities, all inputs validated |
| 20-24 | Minor issues (1-2 low severity) |
| 15-19 | Moderate issues (medium severity) |
| 10-14 | High severity issues |
| 0-9 | Critical vulnerabilities |

**Deductions**:
- Hardcoded secret: -10
- SQL injection risk: -10
- XSS vulnerability: -8
- Missing input validation: -5
- Insecure dependency: -3

---

### Test Coverage (20%)

| Score | Criteria |
|-------|----------|
| 20 | Coverage >= 90%, all edge cases |
| 16-19 | Coverage >= 80%, good edge coverage |
| 12-15 | Coverage >= 70%, some edge cases |
| 8-11 | Coverage >= 50%, basic tests |
| 0-7 | Coverage < 50% or fake tests |

**Deductions**:
- Fake test detected: -5
- Missing error case test: -3
- Missing async test: -2
- Mock overuse: -2

---

### Documentation (15%)

| Score | Criteria |
|-------|----------|
| 15 | Complete JSDoc, clear comments |
| 12-14 | Good documentation, minor gaps |
| 9-11 | Basic documentation |
| 5-8 | Minimal documentation |
| 0-4 | No documentation |

**Deductions**:
- Missing function JSDoc: -2
- Missing API doc: -3
- Outdated comment: -1
- TODO without issue: -1

---

### Naming & Style (15%)

| Score | Criteria |
|-------|----------|
| 15 | Perfect naming, consistent style |
| 12-14 | Good naming, minor inconsistencies |
| 9-11 | Acceptable naming |
| 5-8 | Confusing names |
| 0-4 | Very poor naming |

**Deductions**:
- Single letter variable: -2
- Misleading name: -3
- Inconsistent casing: -2
- Magic number: -1

---

## Score Sheet Template

```markdown
## Score Sheet

### Code Quality (Max: 25)
- [ ] SOLID principles: ___ / 10
- [ ] No code smells: ___ / 10
- [ ] Clean functions: ___ / 5
**Subtotal**: ___ / 25

### Security (Max: 25)
- [ ] No hardcoded secrets: ___ / 5
- [ ] Input validation: ___ / 8
- [ ] Output encoding: ___ / 7
- [ ] Auth/authz correct: ___ / 5
**Subtotal**: ___ / 25

### Test Coverage (Max: 20)
- [ ] Line coverage: ___ / 8
- [ ] Branch coverage: ___ / 6
- [ ] Edge cases: ___ / 6
**Subtotal**: ___ / 20

### Documentation (Max: 15)
- [ ] JSDoc/comments: ___ / 8
- [ ] API documentation: ___ / 7
**Subtotal**: ___ / 15

### Naming & Style (Max: 15)
- [ ] Naming conventions: ___ / 8
- [ ] Code style: ___ / 7
**Subtotal**: ___ / 15

---

**TOTAL SCORE**: ___ / 100
**GRADE**: ___
```

---

## Aggregation Function

```typescript
function aggregateScores(skillResults: SkillResult[]): AggregatedScore {
  const scores: CategoryScores = {
    codeQuality: 0,
    security: 0,
    testCoverage: 0,
    documentation: 0,
    namingStyle: 0,
  };

  // Map skill results to categories
  for (const result of skillResults) {
    switch (result.skill) {
      case 'clean-code-mastery':
        scores.codeQuality = result.score;
        scores.namingStyle = result.subscores.naming;
        scores.documentation = result.subscores.documentation;
        break;
      case 'security-shield':
        scores.security = result.score;
        break;
      case 'tdd-guardian':
        scores.testCoverage = result.score;
        break;
      case 'api-first-design':
        scores.documentation = Math.max(scores.documentation, result.score);
        break;
    }
  }

  return {
    categories: scores,
    overall: calculateOverallScore(scores),
    grade: getGrade(calculateOverallScore(scores)),
  };
}
```
