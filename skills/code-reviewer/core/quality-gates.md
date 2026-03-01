# Quality Gates

## Gate 정의

```typescript
interface QualityGate {
  name: string;
  threshold: number;
  blocking: boolean;  // 실패 시 진행 차단 여부
}

const QUALITY_GATES: QualityGate[] = [
  // Blocking Gates (반드시 통과)
  { name: 'TypeScript Strict', threshold: 100, blocking: true },
  { name: 'No Security Vulnerabilities', threshold: 100, blocking: true },
  { name: 'No Hardcoded Secrets', threshold: 100, blocking: true },
  { name: 'ESLint Errors', threshold: 0, blocking: true },

  // Warning Gates (권고)
  { name: 'Function Complexity', threshold: 10, blocking: false },
  { name: 'File Length', threshold: 300, blocking: false },
  { name: 'Test Coverage', threshold: 80, blocking: false },
  { name: 'Documentation Coverage', threshold: 70, blocking: false },
  { name: 'ESLint Warnings', threshold: 5, blocking: false },
];
```

## Gate 체크 함수

```typescript
interface GateCheckResult {
  gate: string;
  passed: boolean;
  actual: number;
  threshold: number;
  message: string;
}

function checkQualityGates(code: string, context: ReviewContext): GateCheckResult[] {
  const results: GateCheckResult[] = [];

  // Gate 1: TypeScript Strict
  const tsErrors = checkTypeScriptStrict(code);
  results.push({
    gate: 'TypeScript Strict',
    passed: tsErrors.length === 0,
    actual: tsErrors.length,
    threshold: 0,
    message: tsErrors.length > 0
      ? `${tsErrors.length} type errors found`
      : 'All types are strict',
  });

  // Gate 2: Security Vulnerabilities
  const securityIssues = scanSecurityVulnerabilities(code);
  results.push({
    gate: 'No Security Vulnerabilities',
    passed: securityIssues.critical === 0,
    actual: securityIssues.critical,
    threshold: 0,
    message: securityIssues.critical > 0
      ? `${securityIssues.critical} critical vulnerabilities`
      : 'No critical vulnerabilities',
  });

  // Gate 3: Hardcoded Secrets
  const secrets = detectHardcodedSecrets(code);
  results.push({
    gate: 'No Hardcoded Secrets',
    passed: secrets.length === 0,
    actual: secrets.length,
    threshold: 0,
    message: secrets.length > 0
      ? `${secrets.length} potential secrets detected`
      : 'No hardcoded secrets',
  });

  // Gate 4: Function Complexity
  const complexity = calculateCyclomaticComplexity(code);
  results.push({
    gate: 'Function Complexity',
    passed: complexity.max <= 10,
    actual: complexity.max,
    threshold: 10,
    message: complexity.max > 10
      ? `Max complexity ${complexity.max} (function: ${complexity.function})`
      : 'Complexity within limits',
  });

  // Gate 5: File Length
  const lines = code.split('\n').length;
  results.push({
    gate: 'File Length',
    passed: lines <= 300,
    actual: lines,
    threshold: 300,
    message: lines > 300
      ? `File has ${lines} lines, consider splitting`
      : 'File length acceptable',
  });

  return results;
}
```

## Gate 결과 처리

```typescript
interface ReviewDecision {
  decision: 'APPROVED' | 'NEEDS_WORK' | 'REJECTED';
  reason: string;
  mustFix: GateCheckResult[];
  shouldFix: GateCheckResult[];
}

function processGateResults(results: GateCheckResult[]): ReviewDecision {
  const blockingFailures = results.filter(
    r => !r.passed && QUALITY_GATES.find(g => g.name === r.gate)?.blocking
  );

  const warnings = results.filter(
    r => !r.passed && !QUALITY_GATES.find(g => g.name === r.gate)?.blocking
  );

  if (blockingFailures.length > 0) {
    return {
      decision: 'REJECTED',
      reason: `Blocking gate failures: ${blockingFailures.map(f => f.gate).join(', ')}`,
      mustFix: blockingFailures,
      shouldFix: warnings,
    };
  }

  if (warnings.length > 3) {
    return {
      decision: 'NEEDS_WORK',
      reason: 'Too many quality warnings',
      mustFix: [],
      shouldFix: warnings,
    };
  }

  return {
    decision: 'APPROVED',
    reason: 'All quality gates passed',
    mustFix: [],
    shouldFix: warnings,
  };
}
```
