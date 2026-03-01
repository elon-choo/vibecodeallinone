# Code Smell Detection

## Code Smell 카테고리

```yaml
Code_Smells:
  Bloaters:
    - Long_Method: "20줄 이상 함수"
    - Large_Class: "300줄 이상 클래스"
    - Long_Parameter_List: "4개 이상 파라미터"
    - Data_Clumps: "반복되는 데이터 그룹"

  Object_Orientation_Abusers:
    - Switch_Statements: "복잡한 switch/case"
    - Refused_Bequest: "사용하지 않는 상속"
    - Alternative_Classes: "동일 인터페이스 다른 구현"

  Change_Preventers:
    - Divergent_Change: "한 클래스가 여러 이유로 변경"
    - Shotgun_Surgery: "한 변경이 여러 클래스에 영향"
    - Parallel_Inheritance: "병렬 상속 계층"

  Dispensables:
    - Comments: "불필요한 주석 (코드로 표현 가능)"
    - Duplicate_Code: "중복 코드"
    - Dead_Code: "사용되지 않는 코드"
    - Speculative_Generality: "미래를 위한 과도한 추상화"

  Couplers:
    - Feature_Envy: "다른 클래스 데이터에 과도한 접근"
    - Inappropriate_Intimacy: "클래스 간 과도한 결합"
    - Message_Chains: "긴 메서드 체인"
    - Middle_Man: "단순 위임만 하는 클래스"
```

## 탐지 패턴

```typescript
const CODE_SMELL_PATTERNS = {
  // Long Method
  longMethod: {
    detect: (code: string) => {
      const functions = extractFunctions(code);
      return functions.filter(f => f.lines > 20).map(f => ({
        smell: 'Long Method',
        location: f.name,
        lines: f.lines,
        suggestion: `함수 '${f.name}'을 더 작은 함수로 분리하세요 (현재 ${f.lines}줄)`,
      }));
    },
  },

  // Long Parameter List
  longParameterList: {
    detect: (code: string) => {
      const pattern = /function\s+\w+\s*\(([^)]+)\)|(\w+)\s*=\s*(?:async\s*)?\(([^)]+)\)\s*=>/g;
      const matches = [...code.matchAll(pattern)];
      return matches
        .filter(m => {
          const params = (m[1] || m[3] || '').split(',').filter(Boolean);
          return params.length > 4;
        })
        .map(m => ({
          smell: 'Long Parameter List',
          location: m[0].substring(0, 50),
          suggestion: '파라미터 객체로 그룹화하세요',
        }));
    },
  },

  // Duplicate Code
  duplicateCode: {
    detect: (code: string) => {
      const duplicates = findDuplicateBlocks(code, 5);
      return duplicates.map(d => ({
        smell: 'Duplicate Code',
        locations: d.locations,
        lines: d.lines,
        suggestion: `${d.lines}줄의 중복 코드를 공통 함수로 추출하세요`,
      }));
    },
  },

  // Feature Envy / Message Chain
  featureEnvy: {
    detect: (code: string) => {
      const pattern = /(\w+)\.((?:\w+\.){3,})/g;
      const matches = [...code.matchAll(pattern)];
      return matches.map(m => ({
        smell: 'Feature Envy / Message Chain',
        code: m[0],
        suggestion: '중간 객체에 메서드를 위임하거나, 필요한 데이터만 전달하세요',
      }));
    },
  },

  // God Function
  godFunction: {
    detect: (code: string) => {
      const functions = extractFunctions(code);
      return functions
        .filter(f => f.lines > 30 && f.functionCalls > 5 && f.branches > 3)
        .map(f => ({
          smell: 'God Function',
          location: f.name,
          suggestion: '단일 책임 원칙에 따라 여러 함수로 분리하세요',
        }));
    },
  },
};
```

## Code Smell 심각도

```typescript
type SmellSeverity = 'critical' | 'major' | 'minor' | 'info';

const SMELL_SEVERITY: Record<string, SmellSeverity> = {
  // Critical - 즉시 수정 필요
  'God Function': 'critical',
  'Duplicate Code': 'critical',
  'Feature Envy': 'critical',

  // Major - 가능한 빨리 수정
  'Long Method': 'major',
  'Large Class': 'major',
  'Long Parameter List': 'major',
  'Message Chain': 'major',

  // Minor - 리팩토링 시 수정
  'Dead Code': 'minor',
  'Switch Statements': 'minor',
  'Middle Man': 'minor',

  // Info - 참고용
  'Comments': 'info',
  'Speculative Generality': 'info',
};
```

## 중복 코드 탐지

```typescript
function findDuplicateBlocks(code: string, minLines: number): DuplicateBlock[] {
  const lines = code.split('\n');
  const duplicates: DuplicateBlock[] = [];
  const seen = new Map<string, number[]>();

  for (let i = 0; i < lines.length - minLines; i++) {
    const block = lines.slice(i, i + minLines).join('\n').trim();
    if (block.length < 50) continue;

    const normalized = normalizeCode(block);
    if (seen.has(normalized)) {
      seen.get(normalized)!.push(i + 1);
    } else {
      seen.set(normalized, [i + 1]);
    }
  }

  seen.forEach((locations, block) => {
    if (locations.length > 1) {
      duplicates.push({
        lines: minLines,
        locations: locations.map(l => `Line ${l}`),
      });
    }
  });

  return duplicates;
}

function normalizeCode(code: string): string {
  return code
    .replace(/\s+/g, ' ')
    .replace(/['"`][^'"`]*['"`]/g, 'STRING')
    .replace(/\b\d+\b/g, 'NUM')
    .trim();
}
```
