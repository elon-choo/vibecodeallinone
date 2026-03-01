# Fake Test Detector - 15+ Patterns

## Detection Patterns

```yaml
# ═══════════════════════════════════════════════════════════════
# Fake Test Detection Patterns
# ═══════════════════════════════════════════════════════════════

Empty_Assertions:
  pattern_1:
    regex: "expect\\([^)]+\\)\\.toBeDefined\\(\\)\\s*;?\\s*(?:$|\\n|//|/\\*)"
    message: "toBeDefined 단독 사용 금지. 구체적 값 검증 필요"
    severity: error

  pattern_2:
    regex: "expect\\([^)]+\\)\\.toBeTruthy\\(\\)\\s*;?\\s*(?:$|\\n|//|/\\*)"
    message: "toBeTruthy 단독 사용 금지. expect(value).toBe(true) 사용"
    severity: error

  pattern_3:
    regex: "expect\\([^)]+\\)\\.toBeFalsy\\(\\)\\s*;?\\s*(?:$|\\n|//|/\\*)"
    message: "toBeFalsy 단독 사용 금지. expect(value).toBe(false) 사용"
    severity: error

  pattern_4:
    regex: "expect\\([^)]+\\)\\.not\\.toBeNull\\(\\)\\s*;?\\s*(?:$|\\n|//|/\\*)"
    message: "not.toBeNull 단독 사용 금지. 실제 값 검증 필요"
    severity: error

  pattern_5:
    regex: "expect\\([^)]+\\)\\.not\\.toBeUndefined\\(\\)\\s*;?\\s*(?:$|\\n|//|/\\*)"
    message: "not.toBeUndefined 단독 사용 금지. 실제 값 검증 필요"
    severity: error

Empty_Test_Blocks:
  pattern_6:
    regex: "it\\(['\"][^'\"]+['\"]\\s*,\\s*(?:async\\s*)?\\(\\)\\s*=>\\s*\\{\\s*\\}\\)"
    message: "빈 테스트 블록. 구현 필요"
    severity: error

  pattern_7:
    regex: "it\\(['\"][^'\"]+['\"]\\s*,\\s*(?:async\\s*)?\\(\\)\\s*=>\\s*\\{\\s*//.*\\s*\\}\\)"
    message: "주석만 있는 테스트 블록. 구현 필요"
    severity: error

  pattern_8:
    regex: "it\\.skip|describe\\.skip|xit|xdescribe"
    message: "스킵된 테스트 발견. 해결 또는 삭제 필요"
    severity: warning

Todo_Tests:
  pattern_9:
    regex: "it\\(['\"].*TODO.*['\"]"
    message: "TODO가 포함된 테스트 제목. 구현 필요"
    severity: error

  pattern_10:
    regex: "//\\s*TODO.*test|//\\s*FIXME.*test"
    message: "TODO/FIXME 테스트 발견. 해결 필요"
    severity: warning

Over_Mocking:
  pattern_11:
    regex: "jest\\.spyOn.*mockResolvedValue.*\\n.*jest\\.spyOn.*mockResolvedValue.*\\n.*jest\\.spyOn.*mockResolvedValue"
    message: "과도한 mock 사용 (3개 이상 연속). 실제 로직 테스트 필요"
    severity: warning

  pattern_12:
    regex: "jest\\.mock\\(['\"][^'\"]+['\"]\\)\\s*\\n.*jest\\.mock"
    message: "여러 모듈 전체 mock. 통합 테스트 고려 필요"
    severity: warning

Title_Content_Mismatch:
  pattern_13:
    regex: "it\\(['\"]should throw.*['\"].*\\n(?:(?!toThrow|rejects)[\\s\\S])*?\\}\\)"
    message: "제목에 throw가 있지만 toThrow 검증 없음"
    severity: error

  pattern_14:
    regex: "it\\(['\"]should.*error.*['\"].*\\n(?:(?!Error|error|throw)[\\s\\S])*?expect\\(.*\\)\\.toBe\\(true\\)"
    message: "제목에 error가 있지만 성공 테스트 수행"
    severity: error

Snapshot_Abuse:
  pattern_15:
    regex: "expect\\([^)]+\\)\\.toMatchSnapshot\\(\\)\\s*;?\\s*\\}\\s*\\)"
    message: "toMatchSnapshot만 사용하는 테스트. 구체적 검증 추가 필요"
    severity: warning

Weak_Assertions:
  pattern_16:
    regex: "expect\\([^)]+\\)\\.toEqual\\(expect\\.any\\(Object\\)\\)"
    message: "expect.any(Object) 사용. 구체적 구조 검증 필요"
    severity: warning

  pattern_17:
    regex: "expect\\([^)]+\\.length\\)\\.toBeGreaterThan\\(0\\)"
    message: "길이만 검증. 내용 검증도 필요"
    severity: warning
```

## Detection Implementation

```typescript
// Fake Test Detector 구현 예시
const FAKE_TEST_PATTERNS = [
  {
    name: 'toBeDefined_alone',
    regex: /expect\([^)]+\)\.toBeDefined\(\)\s*;?\s*(?:$|\n|\/\/|\/\*)/gm,
    message: 'toBeDefined 단독 사용 금지. 구체적 값 검증 필요',
    severity: 'error'
  },
  {
    name: 'toBeTruthy_alone',
    regex: /expect\([^)]+\)\.toBeTruthy\(\)\s*;?\s*(?:$|\n|\/\/|\/\*)/gm,
    message: 'toBeTruthy 단독 사용 금지. expect(value).toBe(true) 사용',
    severity: 'error'
  },
  {
    name: 'empty_test_block',
    regex: /it\(['"][^'"]+['"]\s*,\s*(?:async\s*)?\(\)\s*=>\s*\{\s*\}\)/gm,
    message: '빈 테스트 블록. 구현 필요',
    severity: 'error'
  },
  {
    name: 'skipped_test',
    regex: /it\.skip|describe\.skip|xit|xdescribe/gm,
    message: '스킵된 테스트 발견. 해결 또는 삭제 필요',
    severity: 'warning'
  },
  {
    name: 'throw_without_assertion',
    regex: /it\(['"]should throw.*['"]/gm,
    // 후처리로 toThrow 존재 여부 확인 필요
    message: '제목에 throw가 있지만 toThrow 검증 없음',
    severity: 'error'
  }
];

interface FakeTestIssue {
  pattern: string;
  message: string;
  severity: 'error' | 'warning';
  line: number;
  code: string;
}

function detectFakeTests(testCode: string): FakeTestIssue[] {
  const issues: FakeTestIssue[] = [];

  for (const pattern of FAKE_TEST_PATTERNS) {
    const matches = testCode.matchAll(pattern.regex);
    for (const match of matches) {
      issues.push({
        pattern: pattern.name,
        message: pattern.message,
        severity: pattern.severity as 'error' | 'warning',
        line: getLineNumber(testCode, match.index!),
        code: match[0].substring(0, 100)
      });
    }
  }

  return issues;
}

function getLineNumber(code: string, index: number): number {
  return code.substring(0, index).split('\n').length;
}
```

## Severity Levels

| Severity | Action | Example |
|----------|--------|---------|
| **error** | 즉시 수정 필요 | toBeDefined 단독, 빈 테스트 |
| **warning** | 리뷰 후 수정 | 과도한 mock, 스킵된 테스트 |
| **info** | 참고용 | 스냅샷 사용 |
