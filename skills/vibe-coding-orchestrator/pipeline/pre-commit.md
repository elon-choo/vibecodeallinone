# Pre-Commit Checklist

## 커밋 전 체크리스트

```yaml
Pre_Commit_Checklist:
  mandatory:
    - id: lint-pass
      description: "ESLint 에러 0개"
      command: "npm run lint"

    - id: type-check-pass
      description: "TypeScript 컴파일 에러 0개"
      command: "npm run type-check"

    - id: test-pass
      description: "모든 테스트 통과"
      command: "npm run test"

    - id: no-secrets
      description: "하드코딩된 시크릿 없음"
      check: "security-shield.noHardcodedSecrets"

    - id: no-console
      description: "console.log 없음 (디버깅 코드)"
      pattern: "console\\.(log|debug|info)"
      exclude: ["*.test.ts", "logger.ts"]

  recommended:
    - id: coverage-threshold
      description: "테스트 커버리지 80% 이상"
      threshold: 80

    - id: no-any
      description: "any 타입 사용 최소화"
      max_count: 0

    - id: no-todo
      description: "TODO 주석 해결"
      pattern: "TODO:|FIXME:|HACK:"

    - id: docs-updated
      description: "API 문서 업데이트"
      condition: "hasApiChanges"
```

## 체크 실행

```typescript
interface CheckResult {
  id: string;
  description: string;
  status: 'pass' | 'fail' | 'warn' | 'skip';
  details?: string;
}

interface PreCommitResult {
  canCommit: boolean;
  mandatoryPassed: number;
  mandatoryFailed: number;
  recommendedPassed: number;
  recommendedFailed: number;
  results: CheckResult[];
}

async function runPreCommitChecks(
  files: string[]
): Promise<PreCommitResult> {
  const results: CheckResult[] = [];

  // Mandatory checks
  for (const check of MANDATORY_CHECKS) {
    const result = await runCheck(check, files);
    results.push(result);
  }

  // Recommended checks
  for (const check of RECOMMENDED_CHECKS) {
    const result = await runCheck(check, files);
    results.push(result);
  }

  const mandatoryResults = results.filter(r =>
    MANDATORY_CHECKS.some(c => c.id === r.id)
  );
  const recommendedResults = results.filter(r =>
    RECOMMENDED_CHECKS.some(c => c.id === r.id)
  );

  return {
    canCommit: mandatoryResults.every(r => r.status === 'pass'),
    mandatoryPassed: mandatoryResults.filter(r => r.status === 'pass').length,
    mandatoryFailed: mandatoryResults.filter(r => r.status === 'fail').length,
    recommendedPassed: recommendedResults.filter(r => r.status === 'pass').length,
    recommendedFailed: recommendedResults.filter(r => r.status === 'fail').length,
    results,
  };
}
```

## 개별 체크 로직

```typescript
async function runCheck(
  check: Check,
  files: string[]
): Promise<CheckResult> {
  // Command 기반 체크
  if (check.command) {
    try {
      await execCommand(check.command);
      return { id: check.id, description: check.description, status: 'pass' };
    } catch (error) {
      return {
        id: check.id,
        description: check.description,
        status: 'fail',
        details: error.message,
      };
    }
  }

  // Pattern 기반 체크
  if (check.pattern) {
    const matches = await searchPattern(check.pattern, files, check.exclude);
    if (matches.length > 0) {
      return {
        id: check.id,
        description: check.description,
        status: 'fail',
        details: `Found ${matches.length} occurrences`,
      };
    }
    return { id: check.id, description: check.description, status: 'pass' };
  }

  // Skill 기반 체크
  if (check.check) {
    const [skillName, methodName] = check.check.split('.');
    const skill = await loadSkill(skillName);
    const passed = await skill[methodName](files);
    return {
      id: check.id,
      description: check.description,
      status: passed ? 'pass' : 'fail',
    };
  }

  return { id: check.id, description: check.description, status: 'skip' };
}
```

## Husky 연동

```bash
#!/usr/bin/env sh
# .husky/pre-commit

# Staged 파일만 체크
STAGED_FILES=$(git diff --cached --name-only --diff-filter=ACM | grep -E '\.(ts|tsx|js|jsx)$')

if [ -n "$STAGED_FILES" ]; then
  # Lint 체크
  echo "🔍 Running lint..."
  npm run lint -- $STAGED_FILES

  # Type 체크
  echo "🔍 Running type check..."
  npm run type-check

  # 테스트 (관련 파일만)
  echo "🔍 Running tests..."
  npm run test -- --related $STAGED_FILES --passWithNoTests

  # Security 체크
  echo "🔍 Running security scan..."
  npm run security-scan
fi
```

## Lint-Staged 설정

```json
{
  "lint-staged": {
    "*.{ts,tsx}": [
      "eslint --fix",
      "prettier --write"
    ],
    "*.{ts,tsx,js,jsx}": [
      "vitest related --run --passWithNoTests"
    ],
    "*.{json,md,yml,yaml}": [
      "prettier --write"
    ]
  }
}
```

## Pre-Commit Report

```markdown
## 📋 Pre-Commit Check Results

### Mandatory Checks
| Check | Status | Details |
|-------|--------|---------|
| ESLint | ✅ Pass | 0 errors |
| TypeScript | ✅ Pass | 0 errors |
| Tests | ✅ Pass | 12/12 passed |
| No Secrets | ✅ Pass | Clean |
| No Console | ✅ Pass | Clean |

### Recommended Checks
| Check | Status | Details |
|-------|--------|---------|
| Coverage | ⚠️ Warn | 78% (target: 80%) |
| No Any | ✅ Pass | 0 found |
| No TODO | ⚠️ Warn | 2 TODOs found |
| API Docs | ⏭️ Skip | No API changes |

### Summary
- **Mandatory**: 5/5 passed ✅
- **Recommended**: 2/4 passed, 2 warnings ⚠️

### Verdict: ✅ Ready to Commit
```

## Git Hook 통합

```typescript
// package.json scripts
{
  "scripts": {
    "prepare": "husky install",
    "pre-commit": "lint-staged && npm run pre-commit-checks",
    "pre-commit-checks": "ts-node scripts/pre-commit.ts",
    "pre-push": "npm run test && npm run type-check"
  }
}
```
