# TDD Workflow - Red-Green-Refactor

## The TDD Cycle

```
┌─────────────────────────────────────────────────────────────────┐
│                     TDD 3단계 사이클                             │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│   ┌─────────┐         ┌─────────┐         ┌─────────┐          │
│   │   RED   │ ──────► │  GREEN  │ ──────► │REFACTOR │          │
│   │ (실패)  │         │ (통과)  │         │ (개선)  │          │
│   └────┬────┘         └────┬────┘         └────┬────┘          │
│        │                   │                   │                │
│        ▼                   ▼                   ▼                │
│   실패하는 테스트      테스트 통과하는       코드 품질 개선     │
│   먼저 작성           최소한의 코드         (테스트 유지)       │
│                                                                 │
│   ◄──────────────────────────────────────────────────────────   │
│                        반복                                     │
└─────────────────────────────────────────────────────────────────┘
```

## AI 워크플로우에서의 TDD 적용

```yaml
Step_1_Requirement_Analysis:
  actions:
    - 요구사항을 테스트 케이스 목록으로 변환
    - 각 케이스의 입력/출력 명확화
  output: |
    ## 테스트 케이스 목록
    1. [Happy] 유효한 이메일로 사용자 생성 → User 반환
    2. [Error] 중복 이메일 → ConflictError
    3. [Error] 잘못된 이메일 형식 → ValidationError
    4. [Boundary] 빈 이름 → ValidationError
    5. [Boundary] 최대 길이 이름 → 성공

Step_2_Write_Failing_Test:
  rule: "구현 코드 없이 테스트만 먼저 작성"
  verification: "테스트 실행 시 반드시 실패해야 함"
  example: |
    // ✅ 올바른 순서: 테스트 먼저
    describe('UserService', () => {
      it('should create user with valid email', async () => {
        const result = await service.createUser({
          email: 'test@test.com',
          name: 'Test User'
        });

        expect(result.id).toMatch(/^[a-f0-9-]{36}$/);  // UUID 형식
        expect(result.email).toBe('test@test.com');
        expect(result.name).toBe('Test User');
      });
    });
    // 이 시점에서 createUser 메서드가 없으므로 테스트 실패

Step_3_Write_Minimal_Code:
  rule: "테스트를 통과하는 최소한의 코드만 작성"
  anti_pattern: |
    // 🚨 Bad: 불필요한 기능까지 구현
    class UserService {
      async createUser(data) {
        // 캐싱 추가 (요청 안 함)
        // 로깅 추가 (요청 안 함)
        // 알림 추가 (요청 안 함)
        return this.repo.save(data);
      }
    }
  good_pattern: |
    // ✅ Good: 테스트 통과에 필요한 것만
    class UserService {
      async createUser(data: CreateUserDto) {
        return this.repo.save(data);
      }
    }

Step_4_Refactor:
  rule: "테스트가 통과하는 상태에서만 리팩토링"
  checklist:
    - "[ ] 테스트 통과 상태 유지"
    - "[ ] 중복 제거"
    - "[ ] 명명 개선"
    - "[ ] 복잡도 감소"
```

## 예외 상황 처리

```yaml
Bug_Fix_TDD:
  workflow:
    1: "버그 재현하는 테스트 먼저 작성"
    2: "테스트 실패 확인"
    3: "버그 수정"
    4: "테스트 통과 확인"
  example: |
    // 버그: 이메일에 대문자가 있으면 중복 체크 실패
    it('should detect duplicate email case-insensitively', async () => {
      await service.createUser({ email: 'test@test.com' });

      // 대문자로 시도
      await expect(
        service.createUser({ email: 'TEST@test.com' })
      ).rejects.toThrow(ConflictError);
    });

Legacy_Code:
  workflow:
    1: "기존 동작을 확인하는 테스트 작성 (characterization test)"
    2: "테스트 통과 확인"
    3: "리팩토링"
    4: "테스트 여전히 통과 확인"
```
