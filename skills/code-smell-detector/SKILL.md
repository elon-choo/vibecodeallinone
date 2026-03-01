---
name: code-smell-detector
description: "**CODE SMELL DETECTOR** — Early detection of 22 bad code patterns including God Object, Long Method, Feature Envy, and more. Activates during code writing or review. Suggests refactoring before problems escalate."
license: MIT
allowed-tools:
  - Read
  - Glob
  - Grep
---

# Code Smell Detector Skill v1.0

**코드 스멜 탐지기** - 문제가 작을 때 잡아서 산불 방지

## 핵심 철학

```yaml
Core_Philosophy:
  원칙: "불씨가 산불 되기 전에 끄자"
  목표: "리팩토링이 필요한 시점을 조기에 알려줌"

  왜_중요한가:
    - 기술 부채 누적 방지
    - 유지보수 비용 절감
    - 버그 발생 가능성 감소
    - 코드 가독성 유지

  탐지_시점:
    - 코드 작성 직후 (즉시 피드백)
    - 코드 리뷰 시 (PR 검토)
    - 리팩토링 계획 시 (부채 정리)
```

## 자동 발동 조건

```yaml
Auto_Trigger_Conditions:
  Always_Active:
    - "Write tool로 코드 작성 시"
    - "Edit tool로 코드 수정 시"
    - "코드 리뷰 요청 시"

  Keywords:
    - "코드 리뷰", "리뷰해줘"
    - "코드 스멜", "나쁜 코드"
    - "리팩토링", "개선"
    - "냄새나는 코드", "문제 있어?"
```

## 코드 스멜 분류

### 🔴 Critical - 즉시 수정

```yaml
God_Object:
  설명: "너무 많은 책임을 가진 클래스/모듈"
  탐지_기준:
    - 메서드 수 > 20개
    - 프로퍼티 수 > 15개
    - 파일 라인 수 > 500줄
    - 의존성 수 > 10개
  문제점:
    - 수정 시 영향 범위 파악 불가
    - 테스트 어려움
    - 재사용 불가능
  해결책:
    - 단일 책임 원칙(SRP) 적용
    - 관련 기능별로 클래스 분리
  예시:
    Bad: |
      class UserManager {
        createUser() {}
        deleteUser() {}
        sendEmail() {}
        generateReport() {}
        processPayment() {}
        validateData() {}
        // ... 50개 더
      }
    Good: |
      class UserService { /* 사용자 CRUD */ }
      class EmailService { /* 이메일 발송 */ }
      class ReportService { /* 리포트 생성 */ }
      class PaymentService { /* 결제 처리 */ }

Long_Method:
  설명: "너무 긴 함수/메서드"
  탐지_기준:
    - 라인 수 > 50줄
    - 들여쓰기 깊이 > 4단계
    - 파라미터 수 > 5개
    - 지역 변수 > 10개
  문제점:
    - 이해하기 어려움
    - 테스트 어려움
    - 재사용 불가능
  해결책:
    - 의미 있는 단위로 함수 분리
    - 조기 반환(Early Return) 적용
  예시:
    Bad: |
      function processOrder(order) {
        // 100줄의 로직...
        if (condition1) {
          if (condition2) {
            if (condition3) {
              // 깊은 중첩...
            }
          }
        }
      }
    Good: |
      function processOrder(order) {
        validateOrder(order);
        calculateTotal(order);
        applyDiscount(order);
        saveOrder(order);
        sendConfirmation(order);
      }

Duplicate_Code:
  설명: "중복된 코드"
  탐지_기준:
    - 3줄 이상 동일 코드 2곳 이상
    - 유사한 로직 패턴 반복
  문제점:
    - 수정 시 모든 곳 수정 필요
    - 일부만 수정하면 불일치 발생
  해결책:
    - 공통 함수/모듈로 추출
    - 템플릿 메서드 패턴 적용
```

### 🟠 Warning - 빠른 수정 권장

```yaml
Feature_Envy:
  설명: "다른 클래스의 데이터를 과도하게 사용"
  탐지_기준:
    - 다른 객체 메서드 3회 이상 연속 호출
    - 다른 객체 프로퍼티 5개 이상 접근
  문제점:
    - 책임 분리 위반
    - 캡슐화 위반
  해결책:
    - 메서드를 데이터가 있는 클래스로 이동
  예시:
    Bad: |
      function getFullAddress(user) {
        return user.street + user.city + user.country + user.zipCode;
      }
    Good: |
      class User {
        getFullAddress() {
          return this.street + this.city + this.country + this.zipCode;
        }
      }

Data_Clumps:
  설명: "항상 함께 다니는 데이터 그룹"
  탐지_기준:
    - 같은 파라미터 조합 3곳 이상
    - 같은 필드 조합 반복
  문제점:
    - 중복된 검증 로직
    - 변경 시 여러 곳 수정
  해결책:
    - 데이터 클래스/인터페이스로 묶기
  예시:
    Bad: |
      function createOrder(street, city, zipCode, country) {}
      function validateAddress(street, city, zipCode, country) {}
      function formatAddress(street, city, zipCode, country) {}
    Good: |
      interface Address { street, city, zipCode, country }
      function createOrder(address: Address) {}
      function validateAddress(address: Address) {}

Primitive_Obsession:
  설명: "기본 타입 남용"
  탐지_기준:
    - 문자열로 특수 값 표현 (status: "active")
    - 숫자로 코드 값 표현
    - 배열 인덱스로 의미 부여
  문제점:
    - 타입 안전성 없음
    - 유효성 검증 반복
  해결책:
    - 값 객체(Value Object) 생성
    - enum 사용
  예시:
    Bad: |
      const status = "active"; // 오타 가능
      const phone = "010-1234-5678"; // 검증 안됨
    Good: |
      enum Status { ACTIVE, INACTIVE }
      class PhoneNumber { constructor(value) { this.validate(value); } }

Long_Parameter_List:
  설명: "파라미터가 너무 많은 함수"
  탐지_기준:
    - 파라미터 > 4개
    - Boolean 파라미터 2개 이상
  문제점:
    - 호출 시 순서 혼동
    - 가독성 저하
  해결책:
    - 파라미터 객체로 묶기
    - 빌더 패턴 사용
  예시:
    Bad: |
      createUser(name, email, age, city, country, phone, isAdmin, isActive)
    Good: |
      createUser({ name, email, age, address: { city, country }, phone, roles })
```

### 🟡 Info - 검토 권장

```yaml
Dead_Code:
  설명: "사용되지 않는 코드"
  탐지_기준:
    - 호출되지 않는 함수
    - 도달 불가능한 코드
    - 주석 처리된 코드
  해결책: "삭제"

Speculative_Generality:
  설명: "미래를 위해 만든 사용 안 하는 추상화"
  탐지_기준:
    - 구현체가 1개인 인터페이스
    - 사용 안 되는 파라미터
    - 오버엔지니어링된 패턴
  해결책: "YAGNI - 필요할 때 만들기"

Comments:
  설명: "코드를 설명하는 주석"
  탐지_기준:
    - What 설명 주석 (코드로 알 수 있음)
    - 오래된 주석 (코드와 불일치)
  해결책:
    - 코드 자체를 명확하게
    - Why 주석만 유지

Magic_Numbers:
  설명: "의미 없는 숫자/문자열 리터럴"
  탐지_기준:
    - 하드코딩된 숫자 (if count > 100)
    - 반복되는 문자열
  해결책: "상수로 추출"
  예시:
    Bad: "if (status === 1) { ... }"
    Good: "if (status === STATUS.ACTIVE) { ... }"

Nested_Conditionals:
  설명: "깊게 중첩된 조건문"
  탐지_기준:
    - if 중첩 > 3단계
    - else if 체인 > 4개
  해결책:
    - 조기 반환 (Early Return)
    - 전략 패턴
    - 다형성
  예시:
    Bad: |
      if (user) {
        if (user.isActive) {
          if (user.hasPermission) {
            // do something
          }
        }
      }
    Good: |
      if (!user) return;
      if (!user.isActive) return;
      if (!user.hasPermission) return;
      // do something
```

## 탐지 임계값

```yaml
Thresholds:
  파일:
    max_lines: 300
    max_functions: 15
    max_imports: 15

  함수:
    max_lines: 30
    max_params: 4
    max_depth: 3
    max_complexity: 10

  클래스:
    max_methods: 15
    max_properties: 10
    max_dependencies: 7

  중복:
    min_duplicate_lines: 3
    min_occurrences: 2
```

## 심각도 점수 체계

```yaml
Severity_Score:
  계산: "각 스멜별 점수 합산"

  점수_기준:
    Critical: 10점
    Warning: 5점
    Info: 2점

  등급:
    A: "0-10점 - 깨끗함"
    B: "11-25점 - 양호"
    C: "26-50점 - 주의 필요"
    D: "51-100점 - 리팩토링 필요"
    F: "100점+ - 심각"
```

## 출력 형식

```markdown
## 🔍 코드 스멜 분석 결과

### 요약
- **파일**: user.service.ts
- **점수**: 35점 (C등급 - 주의 필요)
- **Critical**: 1개
- **Warning**: 3개
- **Info**: 5개

---

### 🔴 Critical Issues

#### 1. Long Method (line 45-120)
- **함수**: `processUserRegistration`
- **문제**: 75줄, 들여쓰기 5단계
- **권장**:
  ```typescript
  // Before: 모든 로직이 한 함수에
  // After: 책임별로 분리
  async function processUserRegistration(data) {
    const validated = await validateUserData(data);
    const user = await createUser(validated);
    await sendWelcomeEmail(user);
    await setupDefaultSettings(user);
    return user;
  }
  ```

---

### 🟠 Warning Issues

#### 1. Data Clumps (multiple locations)
- **위치**: line 15, 45, 78
- **패턴**: (street, city, zipCode) 반복
- **권장**: Address 타입으로 묶기

---

### 🟡 Info Issues

#### 1. Magic Number (line 23)
- **코드**: `if (retryCount > 3)`
- **권장**: `const MAX_RETRY = 3;`

---

### 권장 조치
1. processUserRegistration 함수 분리 (우선순위 높음)
2. Address 타입 생성
3. 상수 추출
```

## Quick Commands

| 명령 | 동작 |
|-----|------|
| smell check | 현재 파일 스멜 검사 |
| smell score | 스멜 점수 계산 |
| smell fix | 자동 수정 가능한 것 수정 |

## 체크리스트

```markdown
### 함수
[ ] 30줄 이하인가?
[ ] 파라미터 4개 이하인가?
[ ] 들여쓰기 3단계 이하인가?
[ ] 하나의 일만 하는가?

### 클래스
[ ] 메서드 15개 이하인가?
[ ] 단일 책임인가?
[ ] 의존성 7개 이하인가?

### 전체
[ ] 중복 코드가 없는가?
[ ] 매직 넘버가 없는가?
[ ] 죽은 코드가 없는가?
```

---

**Version**: 1.0.0
**Auto-Active**: 코드 작성/리뷰 시
**Integration**: clean-code-mastery, naming-convention-guard
