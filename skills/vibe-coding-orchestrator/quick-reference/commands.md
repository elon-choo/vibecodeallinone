# Quick Commands

## Vibe Commands

| Command | Description | Executes |
|---------|-------------|----------|
| `vibe check` | 현재 코드 상태 빠른 진단 | lint + type-check |
| `vibe review` | code-reviewer 호출 | Full review |
| `vibe secure` | security-shield 호출 | Security scan |
| `vibe test` | tdd-guardian 호출 | Test analysis |
| `vibe api` | api-first-design 호출 | API validation |
| `vibe arch` | monorepo-architect 호출 | Architecture check |
| `vibe clean` | clean-code-mastery 호출 | Code quality |
| `vibe pipeline` | 전체 품질 파이프라인 실행 | All stages |
| `vibe commit` | 커밋 전 체크 | Pre-commit checks |
| `vibe report` | 종합 리포트 생성 | Full report |

## Command Details

### `vibe check`
```bash
# 빠른 진단 - 기본 품질 체크
vibe check [file|directory]

# 예시
vibe check src/services/user.service.ts
vibe check src/controllers/

# 실행 내용:
# 1. ESLint 검사
# 2. TypeScript 타입 체크
# 3. 기본 보안 패턴 검사
```

### `vibe review`
```bash
# 전체 코드 리뷰
vibe review [file|directory] [--depth quick|standard|deep]

# 예시
vibe review src/services/auth.service.ts --depth deep
vibe review . --depth standard

# 실행 내용:
# 1. 모든 스킬 통합 실행
# 2. 점수 계산
# 3. 리포트 생성
```

### `vibe secure`
```bash
# 보안 검사
vibe secure [file|directory] [--level basic|owasp|full]

# 예시
vibe secure src/controllers/ --level owasp
vibe secure . --level full

# 실행 내용:
# 1. 하드코딩 시크릿 검사
# 2. OWASP Top 10 검사
# 3. 입력 검증 확인
# 4. 인증/권한 검사
```

### `vibe test`
```bash
# 테스트 분석
vibe test [file|directory] [--coverage] [--fake-check]

# 예시
vibe test src/services/ --coverage
vibe test --fake-check

# 실행 내용:
# 1. 테스트 커버리지 분석
# 2. Fake 테스트 탐지
# 3. 누락된 테스트 식별
# 4. 테스트 품질 점수
```

### `vibe pipeline`
```bash
# 전체 파이프라인 실행
vibe pipeline [--stage lint|type|test|security|quality|all]

# 예시
vibe pipeline --stage all
vibe pipeline --stage security,quality

# 실행 내용:
# 1. Lint 검사
# 2. Type 검사
# 3. Unit Test
# 4. Security Scan
# 5. Code Quality
# 6. API Validation
# 7. Integration Test
```

## 복합 명령어

### `vibe pr`
```bash
# PR 준비 체크
vibe pr [--base main]

# 실행 내용:
# 1. 변경된 파일 분석
# 2. 영향 범위 파악
# 3. 관련 테스트 실행
# 4. 보안 검사
# 5. 코드 리뷰
# 6. PR 체크리스트 생성
```

### `vibe fix`
```bash
# 자동 수정 가능한 이슈 해결
vibe fix [--dry-run]

# 실행 내용:
# 1. ESLint 자동 수정
# 2. Prettier 포맷팅
# 3. Import 정리
# 4. 간단한 코드 스멜 수정
```

### `vibe init`
```bash
# 프로젝트에 vibe 설정 초기화
vibe init [--preset minimal|standard|strict]

# 실행 내용:
# 1. .vibeconfig.yml 생성
# 2. husky 설정
# 3. lint-staged 설정
# 4. CI 파이프라인 템플릿
```

## 출력 형식 옵션

```bash
# JSON 출력
vibe review --format json

# Markdown 출력
vibe review --format markdown

# CI용 간략 출력
vibe review --format ci

# 상세 출력
vibe review --verbose
```

## 설정 파일 옵션

```bash
# 커스텀 설정 파일 사용
vibe review --config .vibeconfig.custom.yml

# 특정 규칙 비활성화
vibe check --disable no-any,no-console

# 특정 파일 제외
vibe pipeline --ignore "**/*.test.ts,**/__mocks__/**"
```

## 대화형 모드

```bash
# 대화형 리뷰
vibe review --interactive

# 예시 플로우:
# ? Which files to review? [Select files]
# ? Review depth? [quick/standard/deep]
# ? Fix issues automatically? [y/N]
# ? Generate report? [Y/n]
```

## 단축 별칭

```yaml
Aliases:
  vc: vibe check
  vr: vibe review
  vs: vibe secure
  vt: vibe test
  vp: vibe pipeline
  vf: vibe fix
```

## NPM Scripts 연동

```json
{
  "scripts": {
    "vibe:check": "vibe check",
    "vibe:review": "vibe review --depth standard",
    "vibe:secure": "vibe secure --level owasp",
    "vibe:test": "vibe test --coverage",
    "vibe:pipeline": "vibe pipeline --stage all",
    "vibe:fix": "vibe fix",
    "vibe:pr": "vibe pr --base main"
  }
}
```
