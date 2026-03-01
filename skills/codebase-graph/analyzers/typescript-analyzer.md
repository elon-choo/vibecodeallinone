# TypeScript Analyzer

## 개요

TypeScript/JavaScript 코드베이스를 AST 기반으로 분석하여 그래프 노드와 엣지를 추출합니다.

## 분석 도구

```yaml
Primary_Tools:
  ts-morph: "TypeScript AST 조작 라이브러리"
  typescript: "공식 TypeScript 컴파일러 API"

Fallback_Tools:
  @babel/parser: "Babel AST 파서"
  acorn: "경량 JS 파서"

Pattern_Based:
  regex: "간단한 패턴 매칭 (AST 불가 시)"
```

## AST 기반 분석 (ts-morph)

### 프로젝트 초기화
```typescript
import { Project, SourceFile, SyntaxKind } from 'ts-morph';

function initProject(rootDir: string): Project {
  const project = new Project({
    tsConfigFilePath: `${rootDir}/tsconfig.json`,
    skipAddingFilesFromTsConfig: false,
  });

  // 또는 수동으로 파일 추가
  project.addSourceFilesAtPaths([
    `${rootDir}/src/**/*.ts`,
    `${rootDir}/src/**/*.tsx`,
  ]);

  return project;
}
```

### 파일 분석
```typescript
function analyzeFile(sourceFile: SourceFile): FileNode {
  const filePath = sourceFile.getFilePath();

  return {
    id: filePath,
    type: 'file',
    name: sourceFile.getBaseName(),
    path: filePath,
    extension: sourceFile.getExtension(),
    language: 'typescript',
    loc: sourceFile.getEndLineNumber(),
    imports: extractImports(sourceFile),
    exports: extractExports(sourceFile),
    hash: computeHash(sourceFile.getFullText()),
  };
}
```

### Import 추출
```typescript
function extractImports(sourceFile: SourceFile): ImportInfo[] {
  const imports: ImportInfo[] = [];

  // import 문 분석
  sourceFile.getImportDeclarations().forEach(importDecl => {
    const moduleSpecifier = importDecl.getModuleSpecifierValue();
    const namedImports = importDecl.getNamedImports();
    const defaultImport = importDecl.getDefaultImport();
    const namespaceImport = importDecl.getNamespaceImport();

    imports.push({
      source: sourceFile.getFilePath(),
      target: resolveModule(moduleSpecifier, sourceFile),
      type: 'imports',
      importType: defaultImport ? 'default' :
                  namespaceImport ? 'namespace' :
                  namedImports.length > 0 ? 'named' : 'side-effect',
      importedNames: [
        ...(defaultImport ? [defaultImport.getText()] : []),
        ...(namespaceImport ? [namespaceImport.getText()] : []),
        ...namedImports.map(n => n.getName()),
      ],
      isTypeOnly: importDecl.isTypeOnly(),
    });
  });

  // Dynamic import 분석
  sourceFile.getDescendantsOfKind(SyntaxKind.CallExpression)
    .filter(call => call.getExpression().getText() === 'import')
    .forEach(dynamicImport => {
      const arg = dynamicImport.getArguments()[0];
      if (arg) {
        imports.push({
          source: sourceFile.getFilePath(),
          target: arg.getText().replace(/['"]/g, ''),
          type: 'imports',
          importType: 'named',
          importedNames: [],
          isDynamic: true,
        });
      }
    });

  return imports;
}
```

### 함수 추출
```typescript
function extractFunctions(sourceFile: SourceFile): FunctionNode[] {
  const functions: FunctionNode[] = [];

  // 함수 선언
  sourceFile.getFunctions().forEach(func => {
    functions.push(analyzeFunctionDeclaration(func, sourceFile));
  });

  // Arrow 함수 (변수에 할당된)
  sourceFile.getVariableDeclarations().forEach(varDecl => {
    const initializer = varDecl.getInitializer();
    if (initializer?.getKind() === SyntaxKind.ArrowFunction) {
      functions.push(analyzeArrowFunction(varDecl, sourceFile));
    }
  });

  return functions;
}

function analyzeFunctionDeclaration(func: FunctionDeclaration, sourceFile: SourceFile): FunctionNode {
  const name = func.getName() || 'anonymous';
  const filePath = sourceFile.getFilePath();

  return {
    id: `${filePath}:${name}`,
    type: 'function',
    name,
    path: filePath,
    line: func.getStartLineNumber(),
    endLine: func.getEndLineNumber(),
    signature: generateSignature(func),
    fullSignature: func.getSignature()?.getDeclaration().getText() || '',
    params: func.getParameters().map(p => ({
      name: p.getName(),
      type: p.getType().getText(),
      optional: p.isOptional(),
      defaultValue: p.getInitializer()?.getText(),
    })),
    returnType: func.getReturnType().getText(),
    isAsync: func.isAsync(),
    isExported: func.isExported(),
    visibility: 'public',
    complexity: calculateComplexity(func),
    loc: func.getEndLineNumber() - func.getStartLineNumber() + 1,
    docstring: func.getJsDocs()[0]?.getDescription() || undefined,
    calls: extractFunctionCalls(func),
  };
}

function generateSignature(func: FunctionDeclaration): string {
  const name = func.getName() || 'anonymous';
  const params = func.getParameters()
    .map(p => `${p.getName()}: ${simplifyType(p.getType().getText())}`)
    .join(', ');
  const returnType = simplifyType(func.getReturnType().getText());

  return `${name}(${params}): ${returnType}`;
}

function simplifyType(type: string): string {
  // 복잡한 제네릭 단순화
  if (type.length > 50) {
    return type.substring(0, 47) + '...';
  }
  return type;
}
```

### 클래스 추출
```typescript
function extractClasses(sourceFile: SourceFile): ClassNode[] {
  return sourceFile.getClasses().map(cls => {
    const name = cls.getName() || 'AnonymousClass';
    const filePath = sourceFile.getFilePath();

    return {
      id: `${filePath}:${name}`,
      type: 'class',
      name,
      path: filePath,
      line: cls.getStartLineNumber(),
      endLine: cls.getEndLineNumber(),
      isAbstract: cls.isAbstract(),
      isExported: cls.isExported(),
      extends: cls.getExtends()?.getText(),
      implements: cls.getImplements().map(i => i.getText()),
      decorators: cls.getDecorators().map(d => d.getName()),
      properties: cls.getProperties().map(p => ({
        name: p.getName(),
        type: p.getType().getText(),
        visibility: getVisibility(p),
        isStatic: p.isStatic(),
        isReadonly: p.isReadonly(),
      })),
      methods: cls.getMethods().map(m => `${filePath}:${name}.${m.getName()}`),
      constructorParams: cls.getConstructors()[0]?.getParameters().map(p => ({
        name: p.getName(),
        type: p.getType().getText(),
        optional: p.isOptional(),
      })) || [],
      docstring: cls.getJsDocs()[0]?.getDescription(),
    };
  });
}
```

### 함수 호출 추출
```typescript
function extractFunctionCalls(node: Node): string[] {
  const calls: string[] = [];

  node.getDescendantsOfKind(SyntaxKind.CallExpression).forEach(call => {
    const expression = call.getExpression();
    let callName: string;

    if (expression.getKind() === SyntaxKind.PropertyAccessExpression) {
      // this.method() 또는 obj.method()
      callName = expression.getText();
    } else if (expression.getKind() === SyntaxKind.Identifier) {
      // directCall()
      callName = expression.getText();
    } else {
      return;
    }

    // 내장 함수 제외
    if (!isBuiltInFunction(callName)) {
      calls.push(callName);
    }
  });

  return [...new Set(calls)]; // 중복 제거
}

function isBuiltInFunction(name: string): boolean {
  const builtIns = [
    'console.log', 'console.error', 'console.warn',
    'JSON.parse', 'JSON.stringify',
    'Object.keys', 'Object.values', 'Object.entries',
    'Array.isArray', 'Promise.resolve', 'Promise.reject',
    'parseInt', 'parseFloat', 'isNaN', 'isFinite',
    'setTimeout', 'setInterval', 'clearTimeout', 'clearInterval',
  ];
  return builtIns.includes(name) || name.startsWith('Math.');
}
```

### 순환 복잡도 계산
```typescript
function calculateComplexity(node: Node): number {
  let complexity = 1; // 기본 경로

  const countKinds = [
    SyntaxKind.IfStatement,
    SyntaxKind.ConditionalExpression,    // 삼항 연산자
    SyntaxKind.ForStatement,
    SyntaxKind.ForInStatement,
    SyntaxKind.ForOfStatement,
    SyntaxKind.WhileStatement,
    SyntaxKind.DoStatement,
    SyntaxKind.CatchClause,
    SyntaxKind.CaseClause,               // switch case
    SyntaxKind.BinaryExpression,         // && || 연산자
  ];

  countKinds.forEach(kind => {
    const descendants = node.getDescendantsOfKind(kind);
    if (kind === SyntaxKind.BinaryExpression) {
      // && || 만 카운트
      complexity += descendants.filter(d =>
        d.getOperatorToken().getText() === '&&' ||
        d.getOperatorToken().getText() === '||'
      ).length;
    } else {
      complexity += descendants.length;
    }
  });

  return complexity;
}
```

## 패턴 기반 분석 (Fallback)

AST 파싱이 불가능한 경우 정규식 기반 분석:

```typescript
const PATTERNS = {
  // Import
  importStatement: /import\s+(?:type\s+)?(?:(\w+)|{([^}]+)}|\*\s+as\s+(\w+))\s+from\s+['"]([^'"]+)['"]/g,
  dynamicImport: /import\(['"]([^'"]+)['"]\)/g,
  require: /require\(['"]([^'"]+)['"]\)/g,

  // Export
  namedExport: /export\s+(?:const|let|var|function|class|interface|type|enum)\s+(\w+)/g,
  defaultExport: /export\s+default\s+(?:function\s+)?(\w+)?/g,
  reExport: /export\s+{([^}]+)}\s+from\s+['"]([^'"]+)['"]/g,

  // Function
  functionDecl: /(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^\s{]+))?/g,
  arrowFunction: /(?:export\s+)?(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\([^)]*\)\s*(?::\s*[^=]+)?\s*=>/g,

  // Class
  classDecl: /(?:export\s+)?(?:abstract\s+)?class\s+(\w+)(?:\s+extends\s+(\w+))?(?:\s+implements\s+([^\s{]+))?/g,
  classMethod: /(?:async\s+)?(\w+)\s*\(([^)]*)\)(?:\s*:\s*([^\s{]+))?\s*{/g,

  // Interface/Type
  interfaceDecl: /(?:export\s+)?interface\s+(\w+)(?:\s+extends\s+([^\s{]+))?/g,
  typeAlias: /(?:export\s+)?type\s+(\w+)\s*=/g,

  // Function Call
  functionCall: /(?<!function\s)(?<!class\s)(\w+)\s*\(/g,
};

function analyzeWithPatterns(content: string, filePath: string): PartialGraph {
  const nodes: GraphNode[] = [];
  const edges: GraphEdge[] = [];

  // Import 추출
  let match;
  while ((match = PATTERNS.importStatement.exec(content)) !== null) {
    const [_, defaultImport, namedImports, namespaceImport, modulePath] = match;
    edges.push({
      source: filePath,
      target: modulePath,
      type: 'imports',
      importedNames: [defaultImport, namespaceImport, ...(namedImports?.split(',').map(s => s.trim()) || [])].filter(Boolean),
    });
  }

  // Function 추출
  while ((match = PATTERNS.functionDecl.exec(content)) !== null) {
    const [fullMatch, name, params, returnType] = match;
    const line = content.substring(0, match.index).split('\n').length;
    nodes.push({
      id: `${filePath}:${name}`,
      type: 'function',
      name,
      path: filePath,
      line,
      signature: `${name}(${params}): ${returnType || 'void'}`,
    });
  }

  // Class 추출
  while ((match = PATTERNS.classDecl.exec(content)) !== null) {
    const [_, name, extendsClass, implementsInterfaces] = match;
    const line = content.substring(0, match.index).split('\n').length;
    nodes.push({
      id: `${filePath}:${name}`,
      type: 'class',
      name,
      path: filePath,
      line,
      extends: extendsClass,
      implements: implementsInterfaces?.split(',').map(s => s.trim()) || [],
    });
  }

  return { nodes, edges };
}
```

## NestJS 특화 분석

```typescript
const NESTJS_DECORATORS = {
  // Controller 관련
  Controller: { type: 'controller', routePrefix: true },
  Get: { type: 'route', method: 'GET' },
  Post: { type: 'route', method: 'POST' },
  Put: { type: 'route', method: 'PUT' },
  Delete: { type: 'route', method: 'DELETE' },
  Patch: { type: 'route', method: 'PATCH' },

  // 서비스 관련
  Injectable: { type: 'service' },

  // 모듈 관련
  Module: { type: 'module' },

  // Guard, Pipe 등
  UseGuards: { type: 'guard' },
  UsePipes: { type: 'pipe' },
  UseInterceptors: { type: 'interceptor' },
};

function analyzeNestJSDecorators(cls: ClassDeclaration): NestJSMetadata {
  const decorators = cls.getDecorators();
  const metadata: NestJSMetadata = {
    type: 'unknown',
    routes: [],
    dependencies: [],
  };

  decorators.forEach(dec => {
    const name = dec.getName();
    const config = NESTJS_DECORATORS[name];

    if (config) {
      metadata.type = config.type;

      if (config.routePrefix) {
        // @Controller('users')
        const arg = dec.getArguments()[0];
        metadata.routePrefix = arg?.getText().replace(/['"]/g, '');
      }
    }
  });

  // 메서드의 라우트 데코레이터 분석
  cls.getMethods().forEach(method => {
    method.getDecorators().forEach(dec => {
      const name = dec.getName();
      const config = NESTJS_DECORATORS[name];

      if (config?.type === 'route') {
        const arg = dec.getArguments()[0];
        metadata.routes.push({
          method: config.method,
          path: arg?.getText().replace(/['"]/g, '') || '',
          handler: method.getName(),
        });
      }
    });
  });

  // 생성자 의존성 주입 분석
  const constructor = cls.getConstructors()[0];
  if (constructor) {
    constructor.getParameters().forEach(param => {
      const type = param.getType().getText();
      if (!type.startsWith('string') && !type.startsWith('number')) {
        metadata.dependencies.push(type);
      }
    });
  }

  return metadata;
}
```

## 분석 성능 최적화

```typescript
// 병렬 처리
async function analyzeFilesInParallel(
  files: string[],
  concurrency: number = 4
): Promise<GraphNode[]> {
  const results: GraphNode[] = [];
  const chunks = chunkArray(files, concurrency);

  for (const chunk of chunks) {
    const chunkResults = await Promise.all(
      chunk.map(file => analyzeFile(file))
    );
    results.push(...chunkResults.flat());
  }

  return results;
}

// 증분 분석
async function incrementalAnalysis(
  project: Project,
  previousHashes: Record<string, string>
): Promise<IncrementalResult> {
  const changedFiles: string[] = [];
  const addedFiles: string[] = [];
  const removedFiles: string[] = [];

  const currentFiles = new Set(project.getSourceFiles().map(f => f.getFilePath()));
  const previousFiles = new Set(Object.keys(previousHashes));

  // 변경/추가 파일 감지
  for (const file of currentFiles) {
    const content = project.getSourceFile(file)?.getFullText() || '';
    const currentHash = computeHash(content);

    if (!previousFiles.has(file)) {
      addedFiles.push(file);
    } else if (previousHashes[file] !== currentHash) {
      changedFiles.push(file);
    }
  }

  // 삭제된 파일 감지
  for (const file of previousFiles) {
    if (!currentFiles.has(file)) {
      removedFiles.push(file);
    }
  }

  return { changedFiles, addedFiles, removedFiles };
}
```
