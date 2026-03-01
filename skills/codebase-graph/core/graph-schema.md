# Graph Schema - 상세 스키마 정의

## Node 상세 스키마

### FileNode
```typescript
interface FileNode extends GraphNode {
  type: 'file';
  path: string;                    // 상대 경로
  absolutePath: string;            // 절대 경로
  extension: string;               // .ts, .py 등
  language: Language;              // 감지된 언어
  size: number;                    // 바이트
  loc: number;                     // 라인 수
  imports: string[];               // import한 모듈 목록
  exports: string[];               // export한 심볼 목록
  hash: string;                    // SHA-256 해시
}

// 예시
{
  id: "src/services/auth.ts",
  type: "file",
  name: "auth.ts",
  path: "src/services/auth.ts",
  extension: ".ts",
  language: "typescript",
  size: 4256,
  loc: 156,
  imports: ["bcrypt", "jsonwebtoken", "../types/user"],
  exports: ["AuthService", "validateToken"],
  hash: "abc123..."
}
```

### FunctionNode
```typescript
interface FunctionNode extends GraphNode {
  type: 'function';
  name: string;                    // 함수명
  path: string;                    // 파일 경로
  line: number;                    // 시작 줄
  endLine: number;                 // 끝 줄
  signature: string;               // 시그니처 (간략)
  fullSignature: string;           // 전체 시그니처
  params: ParamInfo[];             // 파라미터 정보
  returnType: string;              // 반환 타입
  isAsync: boolean;                // async 여부
  isExported: boolean;             // export 여부
  visibility: 'public' | 'private' | 'protected';
  complexity: number;              // 순환 복잡도
  loc: number;                     // 함수 라인 수
  docstring?: string;              // JSDoc/docstring
  calls: string[];                 // 호출하는 함수들
  calledBy: string[];              // 이 함수를 호출하는 함수들
}

interface ParamInfo {
  name: string;
  type: string;
  optional: boolean;
  defaultValue?: string;
}

// 예시
{
  id: "src/services/auth.ts:validateToken",
  type: "function",
  name: "validateToken",
  path: "src/services/auth.ts",
  line: 45,
  endLine: 72,
  signature: "validateToken(token: string): Promise<TokenPayload>",
  fullSignature: "async function validateToken(token: string): Promise<TokenPayload | null>",
  params: [{ name: "token", type: "string", optional: false }],
  returnType: "Promise<TokenPayload | null>",
  isAsync: true,
  isExported: true,
  visibility: "public",
  complexity: 5,
  loc: 28,
  docstring: "Validates a JWT token and returns the payload",
  calls: ["jwt.verify", "getUserById"],
  calledBy: ["authMiddleware", "refreshToken"]
}
```

### ClassNode
```typescript
interface ClassNode extends GraphNode {
  type: 'class';
  name: string;
  path: string;
  line: number;
  endLine: number;
  isAbstract: boolean;
  isExported: boolean;
  extends?: string;                // 상속 클래스
  implements: string[];            // 구현 인터페이스
  decorators: string[];            // 데코레이터 (@Injectable 등)
  properties: PropertyInfo[];      // 프로퍼티
  methods: string[];               // 메서드 ID 목록
  constructorParams: ParamInfo[];  // 생성자 파라미터
  docstring?: string;
}

interface PropertyInfo {
  name: string;
  type: string;
  visibility: 'public' | 'private' | 'protected';
  isStatic: boolean;
  isReadonly: boolean;
}

// 예시
{
  id: "src/services/auth.ts:AuthService",
  type: "class",
  name: "AuthService",
  path: "src/services/auth.ts",
  line: 10,
  endLine: 150,
  isAbstract: false,
  isExported: true,
  extends: null,
  implements: ["IAuthService"],
  decorators: ["@Injectable()"],
  properties: [
    { name: "jwtSecret", type: "string", visibility: "private", isStatic: false, isReadonly: true }
  ],
  methods: ["AuthService.validateToken", "AuthService.login", "AuthService.logout"],
  constructorParams: [
    { name: "userService", type: "UserService", optional: false }
  ]
}
```

### TypeNode
```typescript
interface TypeNode extends GraphNode {
  type: 'type';
  name: string;
  path: string;
  line: number;
  kind: 'interface' | 'type' | 'enum';
  isExported: boolean;
  properties?: PropertyInfo[];     // interface/type alias
  values?: string[];               // enum values
  extends?: string[];              // extends 목록
  usedBy: string[];                // 이 타입을 사용하는 곳
}

// 예시
{
  id: "src/types/user.ts:User",
  type: "type",
  name: "User",
  path: "src/types/user.ts",
  line: 5,
  kind: "interface",
  isExported: true,
  properties: [
    { name: "id", type: "string", visibility: "public" },
    { name: "email", type: "string", visibility: "public" },
    { name: "role", type: "UserRole", visibility: "public" }
  ],
  extends: ["BaseEntity"],
  usedBy: ["AuthService", "UserService", "ProfileController"]
}
```

## Edge 상세 스키마

### Import Edge
```typescript
interface ImportEdge extends GraphEdge {
  type: 'imports';
  source: string;                  // 가져오는 파일
  target: string;                  // 가져오는 대상
  importType: 'default' | 'named' | 'namespace' | 'side-effect';
  importedNames: string[];         // import한 이름들
  isTypeOnly: boolean;             // import type 여부
  isDynamic: boolean;              // dynamic import 여부
}

// 예시
{
  source: "src/services/auth.ts",
  target: "src/types/user.ts",
  type: "imports",
  importType: "named",
  importedNames: ["User", "UserRole"],
  isTypeOnly: true,
  isDynamic: false
}
```

### Call Edge
```typescript
interface CallEdge extends GraphEdge {
  type: 'calls';
  source: string;                  // 호출하는 함수
  target: string;                  // 호출되는 함수
  callCount: number;               // 호출 횟수 (파일 내)
  callLines: number[];             // 호출 위치 줄 번호
  isConditional: boolean;          // 조건부 호출 여부
  isAsync: boolean;                // await 여부
}

// 예시
{
  source: "src/services/auth.ts:validateToken",
  target: "src/services/user.ts:getUserById",
  type: "calls",
  callCount: 1,
  callLines: [58],
  isConditional: false,
  isAsync: true
}
```

### Extends/Implements Edge
```typescript
interface InheritanceEdge extends GraphEdge {
  type: 'extends' | 'implements';
  source: string;                  // 자식 클래스
  target: string;                  // 부모 클래스/인터페이스
}

// 예시
{
  source: "src/services/auth.ts:AuthService",
  target: "src/interfaces/auth.ts:IAuthService",
  type: "implements"
}
```

### Contains Edge
```typescript
interface ContainsEdge extends GraphEdge {
  type: 'contains';
  source: string;                  // 컨테이너 (파일/클래스)
  target: string;                  // 포함된 것 (함수/메서드)
}

// 예시
{
  source: "src/services/auth.ts",
  target: "src/services/auth.ts:AuthService",
  type: "contains"
},
{
  source: "src/services/auth.ts:AuthService",
  target: "src/services/auth.ts:AuthService.validateToken",
  type: "contains"
}
```

## Graph Metadata

```typescript
interface GraphMetadata {
  // 기본 정보
  version: string;                 // 그래프 스키마 버전
  projectRoot: string;             // 프로젝트 루트 경로
  projectName: string;             // 프로젝트 이름
  language: string;                // 주 언어
  framework?: string;              // 프레임워크 (Next.js, NestJS 등)

  // 분석 통계
  stats: {
    totalFiles: number;
    totalFunctions: number;
    totalClasses: number;
    totalTypes: number;
    totalEdges: number;
    avgComplexity: number;
    maxComplexity: number;
  };

  // 시간 정보
  timestamps: {
    generatedAt: number;           // 생성 시간
    lastUpdatedAt: number;         // 마지막 업데이트
    analysisTime: number;          // 분석 소요 시간 (ms)
  };

  // 파일 해시 (증분 업데이트용)
  fileHashes: Record<string, string>;
}
```

## 인덱스 구조

```typescript
// 빠른 검색을 위한 인덱스
interface GraphIndex {
  // 이름 → 노드 ID 매핑
  byName: Map<string, string[]>;

  // 타입별 노드 목록
  byType: {
    files: string[];
    functions: string[];
    classes: string[];
    types: string[];
  };

  // 파일별 포함 노드
  byFile: Map<string, string[]>;

  // Edge 인덱스 (source → edges)
  outgoingEdges: Map<string, GraphEdge[]>;

  // Edge 인덱스 (target → edges)
  incomingEdges: Map<string, GraphEdge[]>;
}
```

## JSON 저장 형식

```json
{
  "version": "1.0.0",
  "metadata": {
    "projectRoot": "/path/to/project",
    "projectName": "my-app",
    "language": "typescript",
    "framework": "nestjs",
    "stats": {
      "totalFiles": 156,
      "totalFunctions": 423,
      "totalClasses": 87,
      "totalTypes": 156,
      "totalEdges": 1247,
      "avgComplexity": 4.2,
      "maxComplexity": 18
    },
    "timestamps": {
      "generatedAt": 1702234567890,
      "lastUpdatedAt": 1702234567890,
      "analysisTime": 2340
    }
  },
  "nodes": [
    {
      "id": "src/services/auth.ts:AuthService",
      "type": "class",
      "name": "AuthService",
      ...
    }
  ],
  "edges": [
    {
      "source": "src/services/auth.ts",
      "target": "src/types/user.ts",
      "type": "imports",
      ...
    }
  ],
  "fileHashes": {
    "src/services/auth.ts": "abc123...",
    "src/types/user.ts": "def456..."
  }
}
```
