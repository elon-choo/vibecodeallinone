# Real Assertions Rule

## Forbidden Assertion Patterns

```typescript
// ═══════════════════════════════════════════════════════════════
// 🚨 FORBIDDEN PATTERNS - 단독 사용 금지
// ═══════════════════════════════════════════════════════════════

// Pattern 1: toBeDefined 단독
it('should create user', async () => {
  const result = await service.createUser(validData);
  expect(result).toBeDefined();  // 🚨 무엇이든 있으면 통과
});

// Pattern 2: toBeTruthy 단독
it('should validate email', () => {
  const result = validateEmail('test@test.com');
  expect(result).toBeTruthy();  // 🚨 null/undefined/0/'' 아니면 통과
});

// Pattern 3: not.toBeNull 단독
it('should find user', async () => {
  const user = await service.findById('123');
  expect(user).not.toBeNull();  // 🚨 실제 user 내용 검증 없음
});

// Pattern 4: toMatchSnapshot 남용
it('should render correctly', () => {
  const tree = renderer.create(<Component />).toJSON();
  expect(tree).toMatchSnapshot();  // 🚨 뭘 테스트하는지 불명확
});

// Pattern 5: any로 검증 회피
it('should return data', async () => {
  const result = await api.getData();
  expect(result).toEqual(expect.any(Object));  // 🚨 구조 검증 없음
});
```

## Required Assertion Patterns

```typescript
// ═══════════════════════════════════════════════════════════════
// ✅ REQUIRED PATTERNS - 구체적 값 검증
// ═══════════════════════════════════════════════════════════════

// Pattern 1: 구체적 값 검증
it('should create user with correct data', async () => {
  const result = await service.createUser({
    email: 'test@test.com',
    name: 'John Doe'
  });

  // ✅ 각 필드를 구체적으로 검증
  expect(result.id).toMatch(/^[a-f0-9-]{36}$/);  // UUID 형식
  expect(result.email).toBe('test@test.com');
  expect(result.name).toBe('John Doe');
  expect(result.createdAt).toBeInstanceOf(Date);
});

// Pattern 2: 객체 구조 검증
it('should return user profile', async () => {
  const profile = await service.getProfile('user-123');

  // ✅ 전체 구조 검증
  expect(profile).toEqual({
    id: 'user-123',
    email: expect.stringMatching(/@/),
    name: expect.any(String),
    role: expect.stringMatching(/^(admin|user|guest)$/),
    createdAt: expect.any(Date)
  });
});

// Pattern 3: 배열 검증
it('should return user list', async () => {
  const users = await service.findAll();

  // ✅ 배열 길이와 각 요소 검증
  expect(users).toHaveLength(3);
  expect(users[0]).toMatchObject({
    id: expect.any(String),
    email: expect.stringContaining('@')
  });
  expect(users.map(u => u.email)).toContain('admin@test.com');
});

// Pattern 4: 에러 검증
it('should throw NotFoundError for invalid id', async () => {
  // ✅ 에러 타입과 메시지 검증
  await expect(
    service.findById('invalid-id')
  ).rejects.toThrow(NotFoundError);

  await expect(
    service.findById('invalid-id')
  ).rejects.toMatchObject({
    message: expect.stringContaining('not found'),
    statusCode: 404
  });
});

// Pattern 5: 비동기 동작 검증
it('should complete within timeout', async () => {
  const startTime = Date.now();
  await service.processData();
  const duration = Date.now() - startTime;

  // ✅ 성능 검증
  expect(duration).toBeLessThan(1000);  // 1초 이내
});
```

## Assertion Conversion Guide

```typescript
// ═══════════════════════════════════════════════════════════════
// 변환 가이드: Bad → Good
// ═══════════════════════════════════════════════════════════════

// Case 1: toBeDefined → 구체적 검증
// 🚨 Bad
expect(user).toBeDefined();
// ✅ Good
expect(user).toMatchObject({
  id: expect.any(String),
  email: 'test@test.com'
});

// Case 2: toBeTruthy → 명시적 boolean
// 🚨 Bad
expect(isValid).toBeTruthy();
// ✅ Good
expect(isValid).toBe(true);

// Case 3: not.toBeNull → 값 검증
// 🚨 Bad
expect(result).not.toBeNull();
// ✅ Good
expect(result).toEqual(expectedValue);
// 또는
expect(result).toMatchObject({ key: 'value' });

// Case 4: toMatchSnapshot → 구체적 구조
// 🚨 Bad
expect(component).toMatchSnapshot();
// ✅ Good
expect(component).toHaveTextContent('Expected Text');
expect(screen.getByRole('button')).toBeEnabled();
expect(screen.getByTestId('user-name')).toHaveTextContent('John');

// Case 5: expect.any → 구체적 패턴
// 🚨 Bad
expect(id).toEqual(expect.any(String));
// ✅ Good
expect(id).toMatch(/^[a-f0-9-]{36}$/);  // UUID
expect(id).toMatch(/^usr_[a-zA-Z0-9]{10}$/);  // Custom ID
```
