# Mock Guidelines

## What to Mock vs What to Test Real

```yaml
# ═══════════════════════════════════════════════════════════════
# Mock Guidelines
# ═══════════════════════════════════════════════════════════════

Should_Mock:
  external_services:
    - "HTTP APIs (외부 서비스)"
    - "Database (unit test에서)"
    - "File system"
    - "Email services"
    - "Payment gateways"
  reason: "외부 의존성은 불안정하고 느림"

Should_NOT_Mock:
  business_logic:
    - "Domain models"
    - "Utility functions"
    - "Validation logic"
    - "Data transformations"
  reason: "실제 비즈니스 로직이 테스트되어야 함"

Minimal_Mocking_Principle:
  rule: "테스트 대상 코드 외의 것만 mock"
  example: |
    // Service를 테스트할 때:
    // ✅ Mock: Repository (DB 접근)
    // ❌ Mock: Service 자체의 private 메서드

Over_Mocking_Signs:
  - "모든 의존성이 mock됨"
  - "테스트가 구현을 미러링함"
  - "리팩토링하면 테스트가 깨짐"
  - "테스트 설정이 테스트보다 김"
```

## Good vs Bad Mocking Examples

```typescript
// ═══════════════════════════════════════════════════════════════
// Mock 사용 예시
// ═══════════════════════════════════════════════════════════════

// 🚨 BAD: Over-mocking (모든 것을 mock)
describe('OrderService - Bad', () => {
  it('should process order', async () => {
    // 모든 것을 mock
    jest.spyOn(validator, 'validate').mockReturnValue(true);
    jest.spyOn(calculator, 'calculateTotal').mockReturnValue(100);
    jest.spyOn(inventory, 'checkStock').mockResolvedValue(true);
    jest.spyOn(payment, 'charge').mockResolvedValue({ success: true });
    jest.spyOn(repository, 'save').mockResolvedValue(mockOrder);
    jest.spyOn(email, 'send').mockResolvedValue(true);

    const result = await service.processOrder(orderData);

    // 🚨 이 테스트는 아무것도 테스트하지 않음
    // 모든 로직이 mock되어서 실제 비즈니스 로직 검증 불가
    expect(result.success).toBe(true);
  });
});

// ✅ GOOD: Minimal mocking (외부 의존성만 mock)
describe('OrderService - Good', () => {
  it('should process order with correct total calculation', async () => {
    // 외부 의존성만 mock
    jest.spyOn(payment, 'charge').mockResolvedValue({ success: true });
    jest.spyOn(repository, 'save').mockImplementation(order =>
      Promise.resolve({ ...order, id: 'order-123' })
    );

    const orderData = {
      items: [
        { productId: 'prod-1', price: 100, quantity: 2 },
        { productId: 'prod-2', price: 50, quantity: 1 },
      ],
    };

    const result = await service.processOrder(orderData);

    // ✅ 실제 비즈니스 로직 검증
    expect(result.total).toBe(250);  // 실제 계산 검증
    expect(payment.charge).toHaveBeenCalledWith(250);
  });

  it('should reject order with insufficient stock', async () => {
    // 재고 부족 시나리오
    jest.spyOn(inventory, 'checkStock').mockResolvedValue(false);

    await expect(service.processOrder(orderData))
      .rejects.toThrow(InsufficientStockError);

    // 결제가 시도되지 않아야 함
    expect(payment.charge).not.toHaveBeenCalled();
  });
});
```

## Mock Implementation Patterns

```typescript
// ═══════════════════════════════════════════════════════════════
// Mock 구현 패턴
// ═══════════════════════════════════════════════════════════════

// Pattern 1: Factory Function
const createMockUser = (overrides = {}) => ({
  id: 'user-123',
  email: 'test@test.com',
  name: 'Test User',
  ...overrides,
});

// Pattern 2: Mock Repository
const createMockRepository = <T>() => ({
  find: jest.fn(),
  findOne: jest.fn(),
  save: jest.fn(),
  delete: jest.fn(),
  create: jest.fn(),
});

// Pattern 3: Mock Service with Default Behavior
const createMockUserService = () => ({
  findById: jest.fn().mockResolvedValue(createMockUser()),
  create: jest.fn().mockImplementation((data) =>
    Promise.resolve({ id: 'new-id', ...data })
  ),
  update: jest.fn().mockImplementation((id, data) =>
    Promise.resolve({ id, ...data })
  ),
  delete: jest.fn().mockResolvedValue(true),
});
```

## Anti-Pattern: Mocking What You Don't Own

```typescript
// 🚨 Bad: 외부 라이브러리 내부 mock
jest.mock('lodash', () => ({
  ...jest.requireActual('lodash'),
  debounce: fn => fn,  // 라이브러리 동작 변경
}));

// ✅ Good: Wrapper 만들어서 mock
// src/utils/debounce.ts
export const debouncedFn = debounce(fn, 300);

// test
jest.mock('@/utils/debounce', () => ({
  debouncedFn: jest.fn(fn => fn()),
}));
```
