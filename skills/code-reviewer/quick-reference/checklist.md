# Review Checklist Templates

## Quick Review (단일 함수/메서드)

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

## Standard Review (파일 레벨)

```markdown
## Standard Review Checklist

### 파일 구조
- [ ] 파일 크기가 300줄 이하인가?
- [ ] import 순서가 올바른가?
- [ ] export가 파일 하단에 있는가?
- [ ] 관련 코드가 함께 그룹화되어 있는가?

### 코드 품질
- [ ] 중복 코드가 없는가?
- [ ] 매직 넘버/문자열이 상수화되어 있는가?
- [ ] 복잡도가 허용 범위 내인가?
- [ ] 네이밍 규칙을 따르는가?

### 의존성
- [ ] 순환 의존성이 없는가?
- [ ] 의존성 방향이 올바른가?
- [ ] 불필요한 의존성이 없는가?

### 문서화
- [ ] export된 항목에 JSDoc이 있는가?
- [ ] 복잡한 로직에 설명이 있는가?

### 보안
- [ ] 하드코딩된 시크릿이 없는가?
- [ ] 사용자 입력이 검증되는가?
- [ ] SQL/NoSQL 인젝션 방지가 되어 있는가?

### 테스트
- [ ] 단위 테스트가 있는가?
- [ ] 테스트 커버리지가 80% 이상인가?
- [ ] 테스트가 실제 동작을 검증하는가?
```

## Deep Review (여러 파일)

```markdown
## Deep Review Checklist

### 아키텍처
- [ ] 레이어 분리가 올바른가?
- [ ] 도메인 로직이 올바른 위치에 있는가?
- [ ] 인터페이스/추상화가 적절한가?
- [ ] SOLID 원칙을 따르는가?

### 데이터 흐름
- [ ] 데이터 변환이 명확한가?
- [ ] 불필요한 데이터 복사가 없는가?
- [ ] 캐싱 전략이 적절한가?

### 에러 처리
- [ ] 에러가 적절히 전파되는가?
- [ ] 사용자 친화적인 에러 메시지인가?
- [ ] 에러 로깅이 되어 있는가?

### 성능
- [ ] N+1 쿼리 문제가 없는가?
- [ ] 불필요한 API 호출이 없는가?
- [ ] 메모리 누수 가능성이 없는가?

### API 설계
- [ ] RESTful 규칙을 따르는가?
- [ ] 응답 형식이 일관적인가?
- [ ] Swagger 문서화가 완료되었는가?

### 통합 테스트
- [ ] API 엔드포인트 테스트가 있는가?
- [ ] 외부 서비스 Mock이 적절한가?
```

## Documentation Requirements

```yaml
Mandatory:
  exported_functions:
    - JSDoc comment required
    - "@param" for each parameter
    - "@returns" description
    - "@throws" for exceptions

  exported_classes:
    - Class description
    - "@example" usage

  public_methods:
    - Method description
    - "@param" and "@returns"

Forbidden:
  obvious_comments:
    - "// increment i" (i++)
    - "// return result" (return result)
```
