# Configuration

## 설정 파일 구조

```yaml
# .vibeconfig.yml

version: "1.0"

# 전역 설정
global:
  language: typescript
  framework: nestjs
  strictMode: true
  autoFix: false

# 스킬 설정
skills:
  clean-code-mastery:
    enabled: true
    complexity:
      maxCyclomatic: 10
      maxCognitive: 15
    fileLength:
      maxLines: 300
      warningLines: 200

  tdd-guardian:
    enabled: true
    coverage:
      minimum: 80
      target: 90
    fakeTestDetection: true

  security-shield:
    enabled: true
    level: owasp
    scanDependencies: true
    allowedPatterns: []

  monorepo-architect:
    enabled: true
    enforceLayerBoundaries: true
    allowedCrossDependencies: []

  api-first-design:
    enabled: true
    swaggerRequired: true
    responseFormat: standard
    versioningStrategy: url-prefix

  code-reviewer:
    enabled: true
    autoTrigger: false
    minimumScore: 70

# 파이프라인 설정
pipeline:
  stages:
    - lint
    - type-check
    - unit-test
    - security-scan
    - code-quality

  thresholds:
    lint:
      errors: 0
      warnings: 10
    coverage: 80
    codeQuality: 70

# Pre-commit 설정
preCommit:
  enabled: true
  checks:
    - lint
    - type-check
    - test
    - no-secrets
    - no-console

# 무시할 경로
ignore:
  - "node_modules/**"
  - "dist/**"
  - "coverage/**"
  - "**/*.test.ts"
  - "**/__mocks__/**"

# 리포트 설정
reports:
  format: markdown
  output: .vibe-reports/
  includeTimestamp: true
```

## 환경별 설정

### 개발 환경 (.vibeconfig.dev.yml)
```yaml
extends: .vibeconfig.yml

global:
  strictMode: false
  autoFix: true

skills:
  tdd-guardian:
    coverage:
      minimum: 60

pipeline:
  thresholds:
    coverage: 60
    codeQuality: 60

preCommit:
  enabled: false
```

### 프로덕션 환경 (.vibeconfig.prod.yml)
```yaml
extends: .vibeconfig.yml

global:
  strictMode: true

skills:
  security-shield:
    level: full
    scanDependencies: true

pipeline:
  stages:
    - lint
    - type-check
    - unit-test
    - integration-test
    - security-scan
    - code-quality
    - performance-test

  thresholds:
    coverage: 90
    codeQuality: 80
```

### CI 환경 (.vibeconfig.ci.yml)
```yaml
extends: .vibeconfig.yml

global:
  autoFix: false

reports:
  format: json
  output: ./reports/

pipeline:
  failFast: true
  parallel: true
```

## 프로젝트별 설정 오버라이드

```yaml
# packages/api/.vibeconfig.yml
extends: ../../.vibeconfig.yml

skills:
  api-first-design:
    swaggerRequired: true
    responseFormat: standard

  security-shield:
    level: full
```

```yaml
# packages/web/.vibeconfig.yml
extends: ../../.vibeconfig.yml

global:
  framework: react

skills:
  api-first-design:
    enabled: false
```

## 설정 우선순위

```
1. 명령줄 옵션 (최우선)
   vibe review --config custom.yml

2. 환경 변수
   VIBE_CONFIG_PATH=./custom.yml

3. 로컬 디렉토리 설정
   ./packages/api/.vibeconfig.yml

4. 루트 프로젝트 설정
   ./.vibeconfig.yml

5. 글로벌 사용자 설정
   ~/.vibe/config.yml

6. 기본 설정 (최하위)
```

## 설정 스키마

```typescript
interface VibeConfig {
  version: string;
  extends?: string;

  global: {
    language: 'typescript' | 'javascript';
    framework: string;
    strictMode: boolean;
    autoFix: boolean;
  };

  skills: {
    [skillName: string]: {
      enabled: boolean;
      [key: string]: any;
    };
  };

  pipeline: {
    stages: string[];
    thresholds: Record<string, number>;
    failFast?: boolean;
    parallel?: boolean;
  };

  preCommit: {
    enabled: boolean;
    checks: string[];
  };

  ignore: string[];

  reports: {
    format: 'json' | 'markdown' | 'html';
    output: string;
    includeTimestamp: boolean;
  };
}
```

## 환경 변수

```bash
# 설정 파일 경로
VIBE_CONFIG_PATH=./custom.vibeconfig.yml

# 로그 레벨
VIBE_LOG_LEVEL=debug|info|warn|error

# 캐시 디렉토리
VIBE_CACHE_DIR=./.vibe-cache

# 병렬 실행 워커 수
VIBE_WORKERS=4

# CI 모드 (자동 감지되지만 수동 설정 가능)
VIBE_CI=true

# 리포트 출력 경로
VIBE_REPORT_PATH=./reports/
```

## 초기화 명령어

```bash
# 기본 설정 생성
vibe init

# 프리셋 선택
vibe init --preset minimal   # 최소 설정
vibe init --preset standard  # 표준 설정
vibe init --preset strict    # 엄격 설정

# 대화형 설정
vibe init --interactive

# 기존 설정 마이그레이션
vibe init --migrate-from eslintrc
```

## 설정 검증

```bash
# 설정 파일 유효성 검사
vibe config validate

# 현재 적용된 설정 확인
vibe config show

# 특정 스킬 설정 확인
vibe config show --skill security-shield
```
