# Test Anti-Patterns Quick Reference

## 20+ Common Anti-Patterns

### 1. Fake Assertion Anti-Patterns

| Anti-Pattern | Bad | Good |
|--------------|-----|------|
| Existence-Only | `expect(user).toBeDefined()` | `expect(user).toEqual({id: '123', ...})` |
| Boolean Ambiguity | `expect(isValid).toBeTruthy()` | `expect(isValid).toBe(true)` |
| Length-Only | `expect(arr.length).toBeGreaterThan(0)` | `expect(arr).toHaveLength(3)` |
| Any Object | `expect(x).toEqual(expect.any(Object))` | `expect(x).toMatchObject({key: value})` |
| Snapshot Abuse | `expect(tree).toMatchSnapshot()` | `expect(screen.getByText('...')).toBeInTheDocument()` |

### 2. Test Structure Anti-Patterns

```typescript
// ❌ Empty Test Block
it('should handle edge case', () => {
  // TODO: implement
});

// ❌ Title-Content Mismatch
it('should throw error on invalid input', () => {
  const result = validate('valid-input');
  expect(result).toBe(true);  // No error test!
});

// ❌ Multiple Unrelated Assertions
it('should work correctly', async () => {
  expect(await service.getUser('1')).toBeDefined();
  expect(await service.getUsers()).toHaveLength(5);
  expect(await service.createUser(data)).toHaveProperty('id');
});
```

### 3. Mocking Anti-Patterns

```typescript
// ❌ Over-mocking (everything mocked)
it('should process order', async () => {
  jest.spyOn(validator, 'validate').mockReturnValue(true);
  jest.spyOn(calculator, 'calculateTotal').mockReturnValue(100);
  jest.spyOn(inventory, 'checkStock').mockResolvedValue(true);
  jest.spyOn(payment, 'charge').mockResolvedValue({ success: true });
  // Nothing is actually tested!
});

// ❌ Implementation Testing
it('should call repository.save', async () => {
  await service.createUser(data);
  expect(repository.save).toHaveBeenCalledTimes(1);
  // Tests implementation, not behavior
});

// ❌ Always-Success Mock
beforeEach(() => {
  jest.spyOn(api, 'fetch').mockResolvedValue({ data: mockData });
  // Never tests failure scenarios
});
```

### 4. Async Anti-Patterns

```typescript
// ❌ Missing Await
it('should create user', () => {
  const result = service.createUser(data);  // No await!
  expect(result).toBeDefined();  // Tests Promise object
});

// ❌ Not Testing Rejection
it('should throw on invalid id', async () => {
  try {
    await service.getUser('invalid');
  } catch (e) {
    expect(e).toBeDefined();  // Weak assertion
  }
});

// ✅ Good: Using rejects matcher
it('should throw NotFoundException', async () => {
  await expect(service.getUser('invalid'))
    .rejects
    .toThrow(NotFoundException);
});

// ❌ Race Condition
it('should debounce calls', () => {
  component.handleChange('abc');
  setTimeout(() => {
    expect(api.search).toHaveBeenCalledTimes(1);  // Flaky!
  }, 500);
});

// ✅ Good: Fake timers
it('should debounce calls', () => {
  jest.useFakeTimers();
  component.handleChange('abc');
  jest.advanceTimersByTime(500);
  expect(api.search).toHaveBeenCalledTimes(1);
});
```

### 5. Setup/Teardown Anti-Patterns

```typescript
// ❌ Shared Mutable State
let user: User;

beforeAll(() => {
  user = { id: '1', name: 'Test' };
});

it('test 1', () => {
  user.name = 'Modified';  // Affects other tests!
});

// ✅ Good: Fresh instance each test
const createUser = () => ({ id: '1', name: 'Test' });

it('test 1', () => {
  const user = createUser();
  user.name = 'Modified';  // Independent
});

// ❌ Not Cleaning Up
it('should subscribe to events', () => {
  emitter.on('event', handler);
  // No cleanup - affects next test
});

// ✅ Good: Always cleanup
afterEach(() => {
  emitter.removeAllListeners();
});
```

### 6. React Testing Anti-Patterns

```typescript
// ❌ Testing Implementation Details
it('should update state', () => {
  const { result } = renderHook(() => useState(0));
  expect(result.current[0]).toBe(0);
});

// ✅ Good: Test user behavior
it('should increment counter', async () => {
  const user = userEvent.setup();
  render(<Counter />);
  await user.click(screen.getByRole('button', { name: /increment/i }));
  expect(screen.getByText('Count: 1')).toBeInTheDocument();
});

// ❌ Container Queries
const { container } = render(<Button />);
const button = container.querySelector('button');

// ✅ Good: Screen queries
render(<Button />);
expect(screen.getByRole('button')).toBeInTheDocument();

// ❌ fireEvent (not realistic)
fireEvent.click(screen.getByRole('button'));

// ✅ Good: userEvent (realistic)
const user = userEvent.setup();
await user.click(screen.getByRole('button'));
```

### 7. Coverage Anti-Patterns

```typescript
// ❌ Coverage Gaming
it('should cover all lines', () => {
  service.method1();
  service.method2();
  service.method3();
  // No expect!
});

// ❌ Happy Path Only
it('should calculate discount for premium user', () => {
  expect(calculateDiscount({ isPremium: true }, 50)).toBe(10);
  // No test for non-premium or edge cases
});

// ✅ Good: All branches
describe('calculateDiscount', () => {
  it('should give 20% for premium users', () => {
    expect(calculateDiscount({ isPremium: true }, 50)).toBe(10);
  });

  it('should give 10% for orders over 100', () => {
    expect(calculateDiscount({ isPremium: false }, 150)).toBe(15);
  });

  it('should give 0 for regular small orders', () => {
    expect(calculateDiscount({ isPremium: false }, 50)).toBe(0);
  });
});
```

## Quick Reference Table

| Category | Count | Key Rule |
|----------|-------|----------|
| Fake Assertions | 5 | 구체적 값 검증 |
| Test Structure | 4 | 제목-내용 일치 |
| Mocking | 4 | 외부 의존성만 mock |
| Async | 4 | await + rejects 사용 |
| Setup/Teardown | 3 | 독립적 + cleanup |
| React | 4 | 사용자 관점 테스트 |
| Coverage | 2 | 모든 분기 테스트 |
