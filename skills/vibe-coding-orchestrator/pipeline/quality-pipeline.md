# Quality Pipeline

## 품질 파이프라인 정의

```yaml
Quality_Pipeline:
  stages:
    - name: lint
      tool: eslint
      blocking: true
      threshold:
        errors: 0
        warnings: 10

    - name: type-check
      tool: tsc
      blocking: true
      threshold:
        errors: 0

    - name: unit-test
      tool: vitest
      blocking: false
      threshold:
        coverage: 80
        pass_rate: 100

    - name: security-scan
      tool: security-shield
      blocking: true
      threshold:
        critical: 0
        high: 0

    - name: code-quality
      tool: clean-code-mastery
      blocking: false
      threshold:
        score: 70

    - name: api-validation
      tool: api-first-design
      blocking: false
      condition: "hasApiChanges"

    - name: integration-test
      tool: vitest
      blocking: false
      condition: "isLargeChange"
```

## 파이프라인 스테이지

```typescript
interface PipelineStage {
  name: string;
  tool: string;
  blocking: boolean;
  threshold: Record<string, number>;
  condition?: string;
  timeout: number;
}

interface StageResult {
  stage: string;
  status: 'pass' | 'warn' | 'fail' | 'skip';
  metrics: Record<string, number>;
  issues: Issue[];
  duration: number;
}

const PIPELINE_STAGES: PipelineStage[] = [
  {
    name: 'lint',
    tool: 'eslint',
    blocking: true,
    threshold: { errors: 0, warnings: 10 },
    timeout: 30000,
  },
  {
    name: 'type-check',
    tool: 'tsc',
    blocking: true,
    threshold: { errors: 0 },
    timeout: 60000,
  },
  {
    name: 'unit-test',
    tool: 'vitest',
    blocking: false,
    threshold: { coverage: 80, passRate: 100 },
    timeout: 120000,
  },
  {
    name: 'security-scan',
    tool: 'security-shield',
    blocking: true,
    threshold: { critical: 0, high: 0 },
    timeout: 60000,
  },
  {
    name: 'code-quality',
    tool: 'clean-code-mastery',
    blocking: false,
    threshold: { score: 70 },
    timeout: 30000,
  },
  {
    name: 'api-validation',
    tool: 'api-first-design',
    blocking: false,
    threshold: { compliance: 100 },
    condition: 'hasApiChanges',
    timeout: 30000,
  },
  {
    name: 'integration-test',
    tool: 'vitest',
    blocking: false,
    threshold: { passRate: 100 },
    condition: 'isLargeChange',
    timeout: 300000,
  },
];
```

## 파이프라인 실행

```typescript
async function runPipeline(
  context: WorkContext
): Promise<PipelineResult> {
  const results: StageResult[] = [];
  let blocked = false;

  for (const stage of PIPELINE_STAGES) {
    // 조건 체크
    if (stage.condition && !evaluateCondition(stage.condition, context)) {
      results.push({
        stage: stage.name,
        status: 'skip',
        metrics: {},
        issues: [],
        duration: 0,
      });
      continue;
    }

    // 이전 블로킹 스테이지 실패 시 중단
    if (blocked) {
      results.push({
        stage: stage.name,
        status: 'skip',
        metrics: {},
        issues: [{ message: 'Skipped due to previous blocking failure' }],
        duration: 0,
      });
      continue;
    }

    // 스테이지 실행
    const result = await runStage(stage, context);
    results.push(result);

    // 블로킹 체크
    if (stage.blocking && result.status === 'fail') {
      blocked = true;
    }
  }

  return {
    stages: results,
    overallStatus: blocked ? 'blocked' :
                   results.some(r => r.status === 'fail') ? 'failed' :
                   results.some(r => r.status === 'warn') ? 'warning' : 'passed',
    totalDuration: results.reduce((sum, r) => sum + r.duration, 0),
  };
}
```

## 스테이지 실행 로직

```typescript
async function runStage(
  stage: PipelineStage,
  context: WorkContext
): Promise<StageResult> {
  const startTime = Date.now();

  try {
    const metrics = await executeStageCommand(stage, context);
    const status = evaluateThreshold(metrics, stage.threshold);
    const issues = extractIssues(stage, metrics);

    return {
      stage: stage.name,
      status,
      metrics,
      issues,
      duration: Date.now() - startTime,
    };
  } catch (error) {
    return {
      stage: stage.name,
      status: 'fail',
      metrics: {},
      issues: [{ message: error.message, severity: 'critical' }],
      duration: Date.now() - startTime,
    };
  }
}

function evaluateThreshold(
  metrics: Record<string, number>,
  threshold: Record<string, number>
): 'pass' | 'warn' | 'fail' {
  for (const [key, limit] of Object.entries(threshold)) {
    const value = metrics[key];
    if (value === undefined) continue;

    // 에러/critical 등은 limit 이하여야 함
    if (key.includes('error') || key.includes('critical') || key.includes('high')) {
      if (value > limit) return 'fail';
    }
    // coverage/score 등은 limit 이상이어야 함
    else if (key.includes('coverage') || key.includes('score') || key.includes('Rate')) {
      if (value < limit) {
        // 70% 이하면 fail, 그 외 warn
        if (value < limit * 0.7) return 'fail';
        return 'warn';
      }
    }
    // warnings 등은 limit 이하면 warn
    else if (key.includes('warning')) {
      if (value > limit) return 'warn';
    }
  }

  return 'pass';
}
```

## 조건 평가

```typescript
function evaluateCondition(
  condition: string,
  context: WorkContext
): boolean {
  const conditions: Record<string, (ctx: WorkContext) => boolean> = {
    hasApiChanges: (ctx) =>
      ctx.file.type === 'controller' ||
      ctx.file.type === 'dto' ||
      ctx.change.affectedAreas.includes('api'),

    isLargeChange: (ctx) =>
      ctx.change.linesAdded + ctx.change.linesRemoved > 100,

    isSecuritySensitive: (ctx) =>
      /auth|security|password|token/i.test(ctx.file.path),

    hasNewDependencies: (ctx) =>
      ctx.file.path.includes('package.json'),

    isTestFile: (ctx) =>
      ctx.file.type === 'test',
  };

  return conditions[condition]?.(context) ?? false;
}
```

## 파이프라인 리포트

```markdown
## 🔄 Quality Pipeline Report

### Summary
| Metric | Value |
|--------|-------|
| Total Stages | 7 |
| Passed | 5 |
| Warnings | 1 |
| Failed | 0 |
| Skipped | 1 |
| Duration | 45.2s |

### Stage Results

| Stage | Status | Key Metrics | Duration |
|-------|--------|-------------|----------|
| lint | ✅ Pass | 0 errors, 3 warnings | 2.1s |
| type-check | ✅ Pass | 0 errors | 5.3s |
| unit-test | ⚠️ Warn | 78% coverage | 12.4s |
| security-scan | ✅ Pass | 0 critical | 8.2s |
| code-quality | ✅ Pass | Score: 85 | 3.1s |
| api-validation | ✅ Pass | 100% compliant | 2.8s |
| integration-test | ⏭️ Skip | Condition not met | 0s |

### Issues Found

#### ⚠️ Warnings (1)
1. **unit-test**: Coverage 78% < threshold 80%
   - Recommendation: Add tests for `UserService.updateProfile()`

### Verdict: ✅ PASSED (with warnings)
```
