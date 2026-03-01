# Complexity Analysis

## Cyclomatic Complexity

```typescript
/**
 * Cyclomatic Complexity 계산
 * 복잡도 = 1 + (분기문 수)
 */

interface ComplexityResult {
  functionName: string;
  complexity: number;
  factors: ComplexityFactor[];
  recommendation: string;
}

function calculateCyclomaticComplexity(code: string): ComplexityResult[] {
  const functions = extractFunctions(code);
  const results: ComplexityResult[] = [];

  for (const func of functions) {
    let complexity = 1;
    const factors: ComplexityFactor[] = [];

    // if 문
    const ifCount = (func.body.match(/\bif\s*\(/g) || []).length;
    if (ifCount > 0) {
      complexity += ifCount;
      factors.push({ type: 'if statements', count: ifCount, contribution: ifCount });
    }

    // else if
    const elseIfCount = (func.body.match(/\belse\s+if\s*\(/g) || []).length;
    if (elseIfCount > 0) {
      complexity += elseIfCount;
      factors.push({ type: 'else if', count: elseIfCount, contribution: elseIfCount });
    }

    // switch case
    const caseCount = (func.body.match(/\bcase\s+/g) || []).length;
    if (caseCount > 0) {
      complexity += caseCount;
      factors.push({ type: 'case statements', count: caseCount, contribution: caseCount });
    }

    // 논리 연산자
    const logicalCount = (func.body.match(/&&|\|\|/g) || []).length;
    if (logicalCount > 0) {
      complexity += logicalCount;
      factors.push({ type: 'logical operators', count: logicalCount, contribution: logicalCount });
    }

    // 루프
    const loopCount = (func.body.match(/\b(for|while)\s*\(/g) || []).length;
    if (loopCount > 0) {
      complexity += loopCount;
      factors.push({ type: 'loops', count: loopCount, contribution: loopCount });
    }

    // 삼항 연산자
    const ternaryCount = (func.body.match(/\?[^?:]+:/g) || []).length;
    if (ternaryCount > 0) {
      complexity += ternaryCount;
      factors.push({ type: 'ternary operators', count: ternaryCount, contribution: ternaryCount });
    }

    // try-catch
    const catchCount = (func.body.match(/\bcatch\s*\(/g) || []).length;
    if (catchCount > 0) {
      complexity += catchCount;
      factors.push({ type: 'catch blocks', count: catchCount, contribution: catchCount });
    }

    // 권고사항 생성
    let recommendation = '';
    if (complexity <= 5) {
      recommendation = '✅ 복잡도가 낮아 이해하기 쉽습니다';
    } else if (complexity <= 10) {
      recommendation = '⚠️ 복잡도가 적절합니다. 더 늘리지 마세요';
    } else if (complexity <= 20) {
      recommendation = '🔶 복잡도가 높습니다. 함수 분리를 고려하세요';
    } else {
      recommendation = '🔴 복잡도가 매우 높습니다. 반드시 리팩토링 필요';
    }

    results.push({
      functionName: func.name,
      complexity,
      factors,
      recommendation,
    });
  }

  return results;
}
```

## Cognitive Complexity

```typescript
/**
 * Cognitive Complexity (인지 복잡도)
 * - 중첩된 구조에 더 높은 가중치
 */

function calculateCognitiveComplexity(code: string): number {
  let complexity = 0;
  let nesting = 0;

  const lines = code.split('\n');

  for (const line of lines) {
    const trimmed = line.trim();

    // 중첩 레벨 추적
    if (/\{/.test(trimmed) && !/\}.*\{/.test(trimmed)) {
      nesting++;
    }
    if (/\}/.test(trimmed) && !/\{.*\}/.test(trimmed)) {
      nesting = Math.max(0, nesting - 1);
    }

    // 구조적 복잡도 (중첩 가중치 적용)
    if (/\bif\s*\(/.test(trimmed)) {
      complexity += 1 + nesting;
    }
    if (/\belse\s+if\s*\(/.test(trimmed)) {
      complexity += 1 + nesting;
    }
    if (/\belse\s*\{/.test(trimmed)) {
      complexity += 1;
    }
    if (/\b(for|while)\s*\(/.test(trimmed)) {
      complexity += 1 + nesting;
    }
    if (/\bswitch\s*\(/.test(trimmed)) {
      complexity += 1 + nesting;
    }
    if (/\bcatch\s*\(/.test(trimmed)) {
      complexity += 1 + nesting;
    }

    // break, continue
    if (/\b(break|continue)\b/.test(trimmed)) {
      complexity += 1;
    }
  }

  return complexity;
}
```

## 복잡도 등급

```typescript
function getComplexityGrade(complexity: number) {
  if (complexity <= 5) return { grade: 'A', label: 'Simple', color: 'green' };
  if (complexity <= 10) return { grade: 'B', label: 'Moderate', color: 'yellow' };
  if (complexity <= 20) return { grade: 'C', label: 'Complex', color: 'orange' };
  if (complexity <= 30) return { grade: 'D', label: 'Very Complex', color: 'red' };
  return { grade: 'F', label: 'Untestable', color: 'darkred' };
}
```

## 복잡도 임계값

```typescript
const COMPLEXITY_THRESHOLDS = {
  cyclomatic: {
    function: { good: 5, acceptable: 10, warning: 15, critical: 20 },
    file: { good: 50, acceptable: 100, warning: 150, critical: 200 },
  },
  cognitive: {
    function: { good: 8, acceptable: 15, warning: 25, critical: 40 },
  },
  nesting: {
    max: 4,  // 최대 중첩 레벨
  },
  linesOfCode: {
    function: 30,
    class: 300,
    file: 500,
  },
};
```
