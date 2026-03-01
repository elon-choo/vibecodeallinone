# Naming Conventions

## 네이밍 규칙

```yaml
Naming_Conventions:
  Variables:
    pattern: "^[a-z][a-zA-Z0-9]*$"  # camelCase
    examples:
      good: ["userName", "isActive", "itemCount"]
      bad: ["user_name", "UserName", "ITEM_COUNT"]
    exceptions:
      - "상수 (UPPER_SNAKE_CASE)"

  Constants:
    pattern: "^[A-Z][A-Z0-9_]*$"  # UPPER_SNAKE_CASE
    examples:
      good: ["MAX_RETRY_COUNT", "API_BASE_URL"]
      bad: ["maxRetryCount", "api_base_url"]

  Functions:
    pattern: "^[a-z][a-zA-Z0-9]*$"  # camelCase
    prefixes:
      boolean_return: ["is", "has", "can", "should", "will"]
      async: ["fetch", "load", "save", "update", "delete", "create"]
      event_handler: ["handle", "on"]
      getter: ["get"]
      setter: ["set"]
    examples:
      good: ["getUserById", "isValidEmail", "handleSubmit"]
      bad: ["GetUser", "valid_email", "submit_handler"]

  Classes:
    pattern: "^[A-Z][a-zA-Z0-9]*$"  # PascalCase
    suffixes:
      service: "Service"
      controller: "Controller"
      repository: "Repository"
      dto: "Dto"
    examples:
      good: ["UserService", "AuthController", "CreateUserDto"]
      bad: ["userService", "auth_controller"]

  Interfaces:
    pattern: "^[A-Z][a-zA-Z0-9]*$"  # PascalCase (I 접두사 X)
    examples:
      good: ["User", "ApiResponse", "CreateUserOptions"]
      bad: ["IUser", "user", "create_user_options"]

  Types:
    pattern: "^[A-Z][a-zA-Z0-9]*$"  # PascalCase
    examples:
      good: ["UserId", "ApiError", "UserRole"]
      bad: ["userId", "api_error"]

  Enums:
    pattern: "^[A-Z][a-zA-Z0-9]*$"  # PascalCase
    members: "^[A-Z][A-Z0-9_]*$"  # UPPER_SNAKE_CASE

  Files:
    components: "PascalCase.tsx"
    hooks: "use[Name].ts"
    services: "kebab-case.service.ts"
    utils: "kebab-case.ts"
    constants: "kebab-case.constants.ts"
    types: "kebab-case.types.ts"
```

## 네이밍 검증 함수

```typescript
interface NamingViolation {
  type: 'variable' | 'function' | 'class' | 'interface' | 'constant' | 'file';
  name: string;
  location: string;
  expected: string;
  suggestion: string;
}

function checkNamingConventions(code: string, fileName: string): NamingViolation[] {
  const violations: NamingViolation[] = [];

  // 변수명 검사 (camelCase)
  const varPattern = /(?:const|let|var)\s+([A-Z_][a-zA-Z0-9_]*)\s*[=:]/g;
  let match;
  while ((match = varPattern.exec(code)) !== null) {
    const name = match[1];
    if (!/^[A-Z][A-Z0-9_]*$/.test(name) && !/^[a-z][a-zA-Z0-9]*$/.test(name)) {
      violations.push({
        type: 'variable',
        name,
        location: `Line ${getLineNumber(code, match.index)}`,
        expected: 'camelCase 또는 UPPER_SNAKE_CASE',
        suggestion: toCamelCase(name),
      });
    }
  }

  // Boolean 반환 함수명 검사
  const boolFuncPattern = /(?:function|const)\s+(\w+)\s*(?:=\s*(?:async\s*)?\([^)]*\)\s*:\s*boolean|\([^)]*\)\s*:\s*boolean)/g;
  while ((match = boolFuncPattern.exec(code)) !== null) {
    const name = match[1];
    if (!/^(is|has|can|should|will)[A-Z]/.test(name)) {
      violations.push({
        type: 'function',
        name,
        location: `Line ${getLineNumber(code, match.index)}`,
        expected: 'Boolean 반환 함수는 is/has/can/should/will 접두사 사용',
        suggestion: `is${name.charAt(0).toUpperCase() + name.slice(1)}`,
      });
    }
  }

  // 인터페이스명 검사 (I 접두사 금지)
  const interfacePattern = /interface\s+(I[A-Z][a-zA-Z0-9]*)/g;
  while ((match = interfacePattern.exec(code)) !== null) {
    violations.push({
      type: 'interface',
      name: match[1],
      location: `Line ${getLineNumber(code, match.index)}`,
      expected: 'PascalCase without "I" prefix',
      suggestion: match[1].substring(1),
    });
  }

  return violations;
}
```

## 의미 있는 이름 검사

```typescript
const MEANINGLESS_NAMES = [
  // 단일 문자 (루프 변수 제외)
  { pattern: /^[a-z]$/, context: 'not-loop', message: '단일 문자 변수명은 루프에서만 사용' },

  // 숫자로 끝나는 이름
  { pattern: /\d+$/, message: '숫자 접미사 대신 의미 있는 이름 사용' },

  // 일반적인 의미 없는 이름
  {
    pattern: /^(data|info|item|thing|stuff|obj|object|value|val|temp|tmp|foo|bar|baz|test|result|res|ret)$/i,
    message: '더 구체적인 이름 사용 권장',
  },

  // 타입을 이름에 포함
  {
    pattern: /(List|Array|Map|Set|String|Number|Boolean|Object)$/,
    message: '타입 정보는 타입 시스템에 위임 (userList → users)',
  },

  // 헝가리안 표기법
  {
    pattern: /^(str|int|bool|arr|obj|fn)[A-Z]/,
    message: '헝가리안 표기법 사용 금지',
  },
];
```

## 헬퍼 함수

```typescript
function toCamelCase(str: string): string {
  return str
    .replace(/[-_](.)/g, (_, c) => c.toUpperCase())
    .replace(/^[A-Z]/, c => c.toLowerCase());
}

function toPascalCase(str: string): string {
  return str
    .replace(/[-_](.)/g, (_, c) => c.toUpperCase())
    .replace(/^[a-z]/, c => c.toUpperCase());
}

function getLineNumber(code: string, index: number): number {
  return code.substring(0, index).split('\n').length;
}
```
