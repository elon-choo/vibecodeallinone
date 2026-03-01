# Auto-Activation Rules

## 자동 발동 규칙

### 파일 타입 기반

```yaml
File_Type_Rules:
  "*.controller.ts":
    activate:
      - api-first-design
      - security-shield
    reason: "API 컨트롤러 작업"

  "*.service.ts":
    activate:
      - clean-code-mastery
    reason: "비즈니스 로직 작업"

  "*.repository.ts":
    activate:
      - clean-code-mastery
      - security-shield
    reason: "데이터 접근 작업"

  "*.dto.ts":
    activate:
      - api-first-design
    reason: "DTO 정의"

  "*.test.ts | *.spec.ts":
    activate:
      - tdd-guardian
    reason: "테스트 코드 작업"

  "*.module.ts":
    activate:
      - monorepo-architect
    reason: "모듈 구조 작업"

  "package.json | tsconfig.json":
    activate:
      - monorepo-architect
    reason: "프로젝트 설정 변경"

  ".env* | *config.ts":
    activate:
      - security-shield
    reason: "설정/환경 변수"
```

### 콘텐츠 기반

```yaml
Content_Rules:
  security_keywords:
    patterns:
      - "password"
      - "secret"
      - "token"
      - "auth"
      - "session"
      - "cookie"
      - "jwt"
      - "encrypt"
      - "decrypt"
      - "hash"
      - "salt"
      - "api[_-]?key"
    activate: security-shield
    priority: high

  injection_risk:
    patterns:
      - "eval\\("
      - "innerHTML"
      - "dangerouslySetInnerHTML"
      - "\\$\\{.*\\}"  # template literal in SQL
      - "exec\\("
      - "spawn\\("
    activate: security-shield
    priority: critical

  api_patterns:
    patterns:
      - "@Controller"
      - "@Get|@Post|@Put|@Delete|@Patch"
      - "router\\."
      - "app\\.get|app\\.post"
      - "@ApiOperation"
    activate: api-first-design
    priority: normal

  test_patterns:
    patterns:
      - "describe\\("
      - "it\\("
      - "test\\("
      - "expect\\("
      - "jest"
      - "vitest"
      - "mock"
    activate: tdd-guardian
    priority: normal
```

### 작업 타입 기반

```yaml
Task_Type_Rules:
  new_feature:
    description: "새 기능 구현"
    workflow:
      1: tdd-guardian      # 테스트 먼저
      2: clean-code-mastery
      3: security-shield   # 보안 검토
      4: code-reviewer     # 최종 리뷰

  bug_fix:
    description: "버그 수정"
    workflow:
      1: tdd-guardian      # 재현 테스트
      2: clean-code-mastery
      3: code-reviewer

  refactoring:
    description: "리팩토링"
    workflow:
      1: tdd-guardian      # 기존 테스트 확인
      2: clean-code-mastery
      3: monorepo-architect
      4: code-reviewer

  api_change:
    description: "API 변경"
    workflow:
      1: api-first-design
      2: security-shield
      3: tdd-guardian
      4: code-reviewer

  security_patch:
    description: "보안 패치"
    workflow:
      1: security-shield   # 최우선
      2: tdd-guardian
      3: code-reviewer
```

## 발동 로직

```typescript
interface ActivationRule {
  pattern: string | RegExp;
  skills: string[];
  priority: 'low' | 'normal' | 'high' | 'critical';
  reason: string;
}

const activationRules: ActivationRule[] = [
  // Critical - 즉시 발동
  {
    pattern: /password|secret|token|api[_-]?key/i,
    skills: ['security-shield'],
    priority: 'critical',
    reason: 'Security-sensitive content detected',
  },
  {
    pattern: /eval\(|innerHTML|exec\(/,
    skills: ['security-shield'],
    priority: 'critical',
    reason: 'Potential injection vulnerability',
  },

  // High - 우선 발동
  {
    pattern: /\.controller\.ts$/,
    skills: ['api-first-design', 'security-shield'],
    priority: 'high',
    reason: 'API controller file',
  },
  {
    pattern: /auth|session|jwt/i,
    skills: ['security-shield'],
    priority: 'high',
    reason: 'Authentication-related code',
  },

  // Normal - 일반 발동
  {
    pattern: /\.(test|spec)\.tsx?$/,
    skills: ['tdd-guardian'],
    priority: 'normal',
    reason: 'Test file',
  },
  {
    pattern: /\.service\.ts$/,
    skills: ['clean-code-mastery'],
    priority: 'normal',
    reason: 'Service file',
  },

  // Low - 보조 발동
  {
    pattern: /\.tsx?$/,
    skills: ['clean-code-mastery'],
    priority: 'low',
    reason: 'TypeScript file',
  },
];

function getActivatedSkills(
  filePath: string,
  content: string
): ActivatedSkill[] {
  const activated: ActivatedSkill[] = [];

  for (const rule of activationRules) {
    const pattern = rule.pattern instanceof RegExp
      ? rule.pattern
      : new RegExp(rule.pattern);

    // 파일 경로 매칭
    if (pattern.test(filePath)) {
      activated.push({
        skills: rule.skills,
        priority: rule.priority,
        reason: rule.reason,
        source: 'file-path',
      });
    }

    // 콘텐츠 매칭
    if (pattern.test(content)) {
      activated.push({
        skills: rule.skills,
        priority: rule.priority,
        reason: rule.reason,
        source: 'content',
      });
    }
  }

  // 중복 제거 및 우선순위 정렬
  return deduplicateAndSort(activated);
}
```

## 발동 우선순위

```typescript
const PRIORITY_ORDER = {
  critical: 0,
  high: 1,
  normal: 2,
  low: 3,
};

function sortByPriority(skills: ActivatedSkill[]): ActivatedSkill[] {
  return skills.sort((a, b) =>
    PRIORITY_ORDER[a.priority] - PRIORITY_ORDER[b.priority]
  );
}
```

## 발동 충돌 해결

```typescript
function resolveConflicts(activated: ActivatedSkill[]): ActivatedSkill[] {
  // 같은 스킬이 여러 번 발동된 경우 가장 높은 우선순위 유지
  const skillMap = new Map<string, ActivatedSkill>();

  for (const item of activated) {
    for (const skill of item.skills) {
      const existing = skillMap.get(skill);
      if (!existing ||
          PRIORITY_ORDER[item.priority] < PRIORITY_ORDER[existing.priority]) {
        skillMap.set(skill, { ...item, skills: [skill] });
      }
    }
  }

  return Array.from(skillMap.values());
}
```
