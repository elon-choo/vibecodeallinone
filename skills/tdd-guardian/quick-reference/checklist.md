# TDD Quick Checklist

## Pre-Test Checklist

```markdown
## 테스트 작성 전 확인사항

### 요구사항 분석
- [ ] 테스트할 기능의 요구사항을 명확히 이해했는가?
- [ ] Happy Path 시나리오를 파악했는가?
- [ ] Error 시나리오를 파악했는가?
- [ ] Boundary 조건을 파악했는가?

### 테스트 설계
- [ ] 각 시나리오별 테스트 케이스를 도출했는가?
- [ ] 테스트 데이터를 준비했는가?
- [ ] Mock이 필요한 의존성을 파악했는가?
```

## Post-Test Checklist

```markdown
## 테스트 완료 후 확인사항

### Assertion 품질
- [ ] toBeDefined/toBeTruthy 단독 사용 없음?
- [ ] 모든 assertion이 구체적 값을 검증?
- [ ] 테스트 제목과 내용이 일치?

### Coverage
- [ ] Line coverage >= 80%?
- [ ] Branch coverage >= 70%?
- [ ] 중요 비즈니스 로직 100% 커버?

### Edge Cases
- [ ] 빈 입력 테스트?
- [ ] 경계값 테스트?
- [ ] 에러 케이스 테스트?
- [ ] 비동기 에러 테스트?

### Mock 사용
- [ ] 외부 의존성만 mock?
- [ ] 비즈니스 로직은 실제 코드 테스트?
- [ ] Mock 설정이 테스트보다 짧음?

### Clean Code
- [ ] 테스트가 독립적? (다른 테스트에 의존 안 함)
- [ ] Setup/teardown 적절히 사용?
- [ ] 테스트 코드도 readable?
```

## Quick Review Checklist (단일 함수)

```markdown
## Quick Review Checklist

### 기본 검사
- [ ] 함수명이 동작을 명확히 설명하는가?
- [ ] 파라미터 수가 4개 이하인가?
- [ ] 함수 길이가 20줄 이하인가?
- [ ] 단일 책임 원칙을 따르는가?

### 타입 검사
- [ ] 모든 파라미터에 타입이 있는가?
- [ ] 반환 타입이 명시되어 있는가?
- [ ] any 타입을 사용하지 않았는가?

### 에러 처리
- [ ] 예외 상황이 처리되었는가?
- [ ] null/undefined 체크가 있는가?

### 테스트
- [ ] 테스트가 작성되었는가?
- [ ] 엣지 케이스가 커버되는가?
```

## TDD Cycle Reminder

```
┌─────────────────────────────────────────────────────────────┐
│                TDD 3단계 사이클                              │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│   1️⃣ RED    - 실패하는 테스트 먼저 작성                    │
│   2️⃣ GREEN  - 테스트 통과하는 최소한의 코드                │
│   3️⃣ REFACTOR - 코드 품질 개선 (테스트 유지)              │
│                                                             │
│   ⚠️ 구현 코드 없이 테스트만 먼저!                         │
│   ⚠️ 최소한의 코드만 (불필요한 기능 X)                     │
│   ⚠️ 테스트 통과 상태에서만 리팩토링                       │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

## Coverage Thresholds

| Type | Lines | Branches | Functions |
|------|-------|----------|-----------|
| **Global** | 80% | 70% | 80% |
| **Services** | 90% | 80% | 90% |
| **Utils** | 95% | 90% | 100% |
| **Controllers** | 80% | 70% | 80% |
| **UI Components** | 70% | 60% | 70% |

## Assertion Quality Quick Reference

| Bad | Good |
|-----|------|
| `expect(x).toBeDefined()` | `expect(x).toEqual({...})` |
| `expect(x).toBeTruthy()` | `expect(x).toBe(true)` |
| `expect(x).not.toBeNull()` | `expect(x).toEqual(expected)` |
| `expect(arr.length).toBeGreaterThan(0)` | `expect(arr).toHaveLength(3)` |
| `expect(x).toEqual(expect.any(Object))` | `expect(x).toMatchObject({...})` |
