# Context Detection

## 컨텍스트 분석

```typescript
interface WorkContext {
  // 프로젝트 컨텍스트
  project: {
    type: 'monorepo' | 'single' | 'library';
    framework: string[];     // ['nestjs', 'react', 'next']
    language: 'typescript' | 'javascript';
    hasTests: boolean;
    hasCICD: boolean;
  };

  // 파일 컨텍스트
  file: {
    path: string;
    type: FileType;
    layer: 'controller' | 'service' | 'repository' | 'util' | 'test' | 'config';
    imports: string[];
    exports: string[];
  };

  // 변경 컨텍스트
  change: {
    type: 'create' | 'modify' | 'delete' | 'rename';
    linesAdded: number;
    linesRemoved: number;
    affectedAreas: string[];
  };
}
```

## 파일 타입 감지

```typescript
type FileType =
  | 'controller'    // *.controller.ts
  | 'service'       // *.service.ts
  | 'repository'    // *.repository.ts
  | 'dto'           // *.dto.ts
  | 'entity'        // *.entity.ts
  | 'module'        // *.module.ts
  | 'test'          // *.test.ts, *.spec.ts
  | 'config'        // *.config.ts, .env*
  | 'util'          // utils/, helpers/
  | 'type'          // *.types.ts, *.d.ts
  | 'component'     // *.tsx (React)
  | 'hook'          // use*.ts
  | 'store'         // *Store.ts, *Slice.ts
  | 'unknown';

function detectFileType(filePath: string): FileType {
  const fileName = path.basename(filePath);
  const patterns: [RegExp, FileType][] = [
    [/\.controller\.ts$/, 'controller'],
    [/\.service\.ts$/, 'service'],
    [/\.repository\.ts$/, 'repository'],
    [/\.dto\.ts$/, 'dto'],
    [/\.entity\.ts$/, 'entity'],
    [/\.module\.ts$/, 'module'],
    [/\.(test|spec)\.tsx?$/, 'test'],
    [/\.config\.(ts|js)$/, 'config'],
    [/^\.env/, 'config'],
    [/\.types?\.ts$/, 'type'],
    [/\.d\.ts$/, 'type'],
    [/\.tsx$/, 'component'],
    [/^use[A-Z].*\.ts$/, 'hook'],
    [/(Store|Slice)\.ts$/, 'store'],
  ];

  for (const [pattern, type] of patterns) {
    if (pattern.test(fileName)) return type;
  }

  // 경로 기반 감지
  if (filePath.includes('/utils/') || filePath.includes('/helpers/')) return 'util';

  return 'unknown';
}
```

## 프로젝트 타입 감지

```typescript
async function detectProjectType(rootPath: string): Promise<ProjectContext> {
  const context: ProjectContext = {
    type: 'single',
    framework: [],
    language: 'typescript',
    hasTests: false,
    hasCICD: false,
  };

  // 1. package.json 분석
  const packageJson = await readPackageJson(rootPath);
  if (packageJson) {
    // 프레임워크 감지
    const deps = { ...packageJson.dependencies, ...packageJson.devDependencies };
    if (deps['@nestjs/core']) context.framework.push('nestjs');
    if (deps['react']) context.framework.push('react');
    if (deps['next']) context.framework.push('next');
    if (deps['express']) context.framework.push('express');
    if (deps['vue']) context.framework.push('vue');

    // 테스트 프레임워크 감지
    if (deps['jest'] || deps['vitest'] || deps['mocha']) {
      context.hasTests = true;
    }
  }

  // 2. 모노레포 감지
  const hasWorkspaces = packageJson?.workspaces ||
                        await fileExists(`${rootPath}/lerna.json`) ||
                        await fileExists(`${rootPath}/pnpm-workspace.yaml`) ||
                        await fileExists(`${rootPath}/nx.json`);
  if (hasWorkspaces) context.type = 'monorepo';

  // 3. CI/CD 감지
  const ciFiles = [
    '.github/workflows',
    '.gitlab-ci.yml',
    'Jenkinsfile',
    '.circleci/config.yml',
  ];
  for (const ciFile of ciFiles) {
    if (await fileExists(`${rootPath}/${ciFile}`)) {
      context.hasCICD = true;
      break;
    }
  }

  return context;
}
```

## 레이어 감지

```typescript
function detectLayer(filePath: string): string {
  const layerPatterns: [RegExp | string, string][] = [
    [/\/controllers?\//, 'controller'],
    [/\/services?\//, 'service'],
    [/\/repositor(y|ies)\//, 'repository'],
    [/\/dto\//, 'dto'],
    [/\/entities?\//, 'entity'],
    [/\/models?\//, 'model'],
    [/\/utils?\//, 'util'],
    [/\/helpers?\//, 'util'],
    [/\/lib\//, 'util'],
    [/\/config\//, 'config'],
    [/\/tests?\//, 'test'],
    [/\/__tests__\//, 'test'],
    [/\/components?\//, 'component'],
    [/\/hooks?\//, 'hook'],
    [/\/stores?\//, 'store'],
    [/\/pages?\//, 'page'],
    [/\/api\//, 'api'],
  ];

  for (const [pattern, layer] of layerPatterns) {
    if (typeof pattern === 'string') {
      if (filePath.includes(pattern)) return layer;
    } else {
      if (pattern.test(filePath)) return layer;
    }
  }

  return 'unknown';
}
```

## 변경 영향 분석

```typescript
interface ChangeImpact {
  directlyAffected: string[];    // 직접 영향 받는 파일
  indirectlyAffected: string[];  // 간접 영향 받는 파일
  riskLevel: 'low' | 'medium' | 'high' | 'critical';
  requiredTests: string[];       // 필요한 테스트
}

function analyzeChangeImpact(change: ChangeContext): ChangeImpact {
  const impact: ChangeImpact = {
    directlyAffected: [],
    indirectlyAffected: [],
    riskLevel: 'low',
    requiredTests: [],
  };

  // 위험도 계산
  const riskFactors = {
    isSecurityRelated: /auth|security|password|token|session/i.test(change.filePath),
    isPaymentRelated: /payment|billing|subscription/i.test(change.filePath),
    isDataLayer: /repository|entity|model|schema/i.test(change.filePath),
    isHighTraffic: /api|controller/i.test(change.filePath),
    hasLargeChange: change.linesAdded + change.linesRemoved > 100,
  };

  const riskScore = Object.values(riskFactors).filter(Boolean).length;

  if (riskScore >= 3) impact.riskLevel = 'critical';
  else if (riskScore >= 2) impact.riskLevel = 'high';
  else if (riskScore >= 1) impact.riskLevel = 'medium';

  return impact;
}
```

## 컨텍스트 기반 스킬 매칭

```typescript
function matchSkillsToContext(context: WorkContext): SkillMatch[] {
  const matches: SkillMatch[] = [];

  // 1. 파일 타입 기반 매칭
  const fileTypeSkills: Record<FileType, string[]> = {
    controller: ['api-first-design', 'security-shield'],
    service: ['clean-code-mastery'],
    repository: ['clean-code-mastery', 'security-shield'],
    dto: ['api-first-design'],
    test: ['tdd-guardian'],
    config: ['security-shield'],
    component: ['clean-code-mastery'],
    hook: ['clean-code-mastery', 'tdd-guardian'],
  };

  const skills = fileTypeSkills[context.file.type] || ['clean-code-mastery'];
  matches.push(...skills.map(s => ({ skill: s, reason: 'file-type' })));

  // 2. 레이어 기반 추가
  if (context.file.layer === 'api') {
    matches.push({ skill: 'api-first-design', reason: 'layer' });
  }

  // 3. 변경 위험도 기반 추가
  if (context.change.type !== 'delete' &&
      analyzeChangeImpact(context.change).riskLevel !== 'low') {
    matches.push({ skill: 'security-shield', reason: 'risk-level' });
  }

  return deduplicateMatches(matches);
}
```
