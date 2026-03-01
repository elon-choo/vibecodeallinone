# Coverage Thresholds

## Coverage Configuration

```javascript
// jest.config.js
module.exports = {
  // Coverage 수집 설정
  collectCoverage: true,
  collectCoverageFrom: [
    'src/**/*.{ts,tsx}',
    '!src/**/*.d.ts',
    '!src/**/*.test.{ts,tsx}',
    '!src/**/*.spec.{ts,tsx}',
    '!src/**/index.ts',  // barrel exports 제외
    '!src/main.ts',      // entry point 제외
  ],

  // Coverage 임계값 설정
  coverageThreshold: {
    global: {
      branches: 70,    // 분기 커버리지 70%
      functions: 80,   // 함수 커버리지 80%
      lines: 80,       // 라인 커버리지 80%
      statements: 80   // 구문 커버리지 80%
    },
    // 특정 파일/폴더 개별 설정
    './src/services/': {
      branches: 80,
      functions: 90,
      lines: 90
    },
    './src/utils/': {
      branches: 90,
      functions: 100,
      lines: 95
    }
  },

  // Coverage 리포터
  coverageReporters: ['text', 'lcov', 'html'],

  // Coverage 디렉토리
  coverageDirectory: './coverage'
};
```

## Coverage Enforcement in CI/CD

```yaml
# .github/workflows/test.yml
name: Test with Coverage

on: [push, pull_request]

jobs:
  test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Node
        uses: actions/setup-node@v4
        with:
          node-version: '20'

      - name: Install dependencies
        run: pnpm install

      - name: Run tests with coverage
        run: pnpm test -- --coverage --coverageThreshold='{"global":{"lines":80,"branches":70}}'

      - name: Upload coverage to Codecov
        uses: codecov/codecov-action@v3
        with:
          fail_ci_if_error: true

      - name: Coverage check
        run: |
          COVERAGE=$(cat coverage/coverage-summary.json | jq '.total.lines.pct')
          if (( $(echo "$COVERAGE < 80" | bc -l) )); then
            echo "Coverage $COVERAGE% is below 80%"
            exit 1
          fi
```

## Coverage Analysis Guide

```markdown
## Coverage가 낮을 때 점검 사항

### Line Coverage < 80%
- [ ] 실행되지 않는 코드 경로가 있는가?
- [ ] 에러 핸들링 코드가 테스트되지 않았는가?
- [ ] 조건문의 모든 분기가 테스트되었는가?

### Branch Coverage < 70%
- [ ] if-else의 모든 분기 테스트?
- [ ] switch-case의 모든 케이스 테스트?
- [ ] 삼항 연산자의 양쪽 테스트?
- [ ] optional chaining의 null 케이스 테스트?

### Function Coverage < 80%
- [ ] private 메서드가 public 메서드를 통해 테스트되는가?
- [ ] 콜백 함수가 테스트되는가?
- [ ] 에러 핸들러 함수가 테스트되는가?
```

## Coverage Exception Handling

```typescript
/* istanbul ignore next */
function debugOnlyFunction() {
  // 디버그 전용 코드는 커버리지에서 제외
}

/* istanbul ignore if */
if (process.env.NODE_ENV === 'development') {
  // 개발 환경 전용 코드
}
```

## Coverage Thresholds by Code Type

```yaml
Coverage_Targets:
  Business_Logic:
    lines: 90%
    branches: 85%
    reason: "핵심 비즈니스 로직은 높은 커버리지 필요"

  Utility_Functions:
    lines: 95%
    branches: 90%
    reason: "재사용되는 유틸리티는 완벽히 테스트"

  API_Controllers:
    lines: 80%
    branches: 70%
    reason: "통합 테스트로 보완"

  UI_Components:
    lines: 70%
    branches: 60%
    reason: "시각적 테스트로 보완"

  Configuration:
    lines: 50%
    branches: 40%
    reason: "설정 코드는 낮은 우선순위"
```
