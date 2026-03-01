# Edge Case Coverage

## Mandatory Test Categories

```yaml
Every_Function_Must_Have:
  1_Happy_Path:
    description: "정상 입력 → 정상 출력"
    count: "최소 1개, 주요 시나리오별 추가"

  2_Error_Path:
    description: "잘못된 입력 → 적절한 에러"
    count: "각 에러 타입별 최소 1개"

  3_Boundary_Cases:
    description: "경계값 테스트"
    count: "각 입력 파라미터별 최소 2개"

  4_Async_Errors:
    description: "비동기 실패 상황"
    count: "외부 의존성당 최소 1개"
```

## Boundary Test Examples

```typescript
// ═══════════════════════════════════════════════════════════════
// 경계값 테스트 완전 가이드
// ═══════════════════════════════════════════════════════════════

describe('validateUsername', () => {
  // ───────────────────────────────────────────────────────────
  // String Boundaries
  // ───────────────────────────────────────────────────────────

  describe('string length boundaries', () => {
    it('should reject empty string', () => {
      expect(() => validateUsername('')).toThrow(ValidationError);
    });

    it('should accept minimum length (3 chars)', () => {
      expect(validateUsername('abc')).toBe(true);
    });

    it('should reject below minimum (2 chars)', () => {
      expect(() => validateUsername('ab')).toThrow(ValidationError);
    });

    it('should accept maximum length (20 chars)', () => {
      expect(validateUsername('a'.repeat(20))).toBe(true);
    });

    it('should reject above maximum (21 chars)', () => {
      expect(() => validateUsername('a'.repeat(21))).toThrow(ValidationError);
    });
  });

  // ───────────────────────────────────────────────────────────
  // Special Characters
  // ───────────────────────────────────────────────────────────

  describe('special character handling', () => {
    it('should handle unicode characters', () => {
      expect(validateUsername('user_한글')).toBe(true);
    });

    it('should reject SQL injection attempts', () => {
      expect(() => validateUsername("'; DROP TABLE--")).toThrow();
    });

    it('should reject XSS attempts', () => {
      expect(() => validateUsername('<script>alert(1)</script>')).toThrow();
    });
  });
});

describe('calculatePrice', () => {
  // ───────────────────────────────────────────────────────────
  // Numeric Boundaries
  // ───────────────────────────────────────────────────────────

  describe('numeric boundaries', () => {
    it('should handle zero quantity', () => {
      expect(calculatePrice(100, 0)).toBe(0);
    });

    it('should handle negative price', () => {
      expect(() => calculatePrice(-100, 1)).toThrow(ValidationError);
    });

    it('should handle very large numbers', () => {
      expect(calculatePrice(Number.MAX_SAFE_INTEGER, 1))
        .toBe(Number.MAX_SAFE_INTEGER);
    });

    it('should handle floating point precision', () => {
      // 0.1 + 0.2 = 0.30000000000000004 문제
      expect(calculatePrice(0.1, 3)).toBeCloseTo(0.3, 10);
    });

    it('should handle NaN', () => {
      expect(() => calculatePrice(NaN, 1)).toThrow(ValidationError);
    });

    it('should handle Infinity', () => {
      expect(() => calculatePrice(Infinity, 1)).toThrow(ValidationError);
    });
  });
});

describe('processArray', () => {
  // ───────────────────────────────────────────────────────────
  // Array Boundaries
  // ───────────────────────────────────────────────────────────

  describe('array boundaries', () => {
    it('should handle empty array', () => {
      expect(processArray([])).toEqual([]);
    });

    it('should handle single element', () => {
      expect(processArray([1])).toEqual([1]);
    });

    it('should handle large array', () => {
      const largeArray = Array(10000).fill(1);
      expect(() => processArray(largeArray)).not.toThrow();
    });

    it('should handle array with nulls', () => {
      expect(processArray([1, null, 2])).toEqual([1, 2]);
    });

    it('should handle array with undefined', () => {
      expect(processArray([1, undefined, 2])).toEqual([1, 2]);
    });
  });
});

describe('parseDate', () => {
  // ───────────────────────────────────────────────────────────
  // Date Boundaries
  // ───────────────────────────────────────────────────────────

  describe('date boundaries', () => {
    it('should handle ISO string', () => {
      expect(parseDate('2024-01-15T00:00:00Z')).toEqual(new Date('2024-01-15'));
    });

    it('should handle invalid date string', () => {
      expect(() => parseDate('not-a-date')).toThrow(ValidationError);
    });

    it('should handle leap year', () => {
      expect(parseDate('2024-02-29')).toEqual(new Date('2024-02-29'));
    });

    it('should reject invalid leap year date', () => {
      expect(() => parseDate('2023-02-29')).toThrow(ValidationError);
    });

    it('should handle timezone edge cases', () => {
      // UTC vs local time
      const date = parseDate('2024-01-01T00:00:00+09:00');
      expect(date.getUTCDate()).toBe(31); // Dec 31 in UTC
    });
  });
});
```

## Async Error Testing

```typescript
// ═══════════════════════════════════════════════════════════════
// 비동기 에러 테스트 패턴
// ═══════════════════════════════════════════════════════════════

describe('ExternalApiService', () => {
  // ───────────────────────────────────────────────────────────
  // Network Errors
  // ───────────────────────────────────────────────────────────

  describe('network error handling', () => {
    it('should handle timeout', async () => {
      jest.spyOn(httpService, 'get').mockRejectedValue(
        new Error('ETIMEDOUT')
      );

      await expect(service.fetchData())
        .rejects.toThrow(TimeoutError);
    });

    it('should handle connection refused', async () => {
      jest.spyOn(httpService, 'get').mockRejectedValue(
        new Error('ECONNREFUSED')
      );

      await expect(service.fetchData())
        .rejects.toThrow(ConnectionError);
    });

    it('should retry on temporary failure', async () => {
      const spy = jest.spyOn(httpService, 'get')
        .mockRejectedValueOnce(new Error('ETIMEDOUT'))
        .mockRejectedValueOnce(new Error('ETIMEDOUT'))
        .mockResolvedValue({ data: 'success' });

      const result = await service.fetchData();

      expect(spy).toHaveBeenCalledTimes(3);
      expect(result).toBe('success');
    });
  });

  // ───────────────────────────────────────────────────────────
  // Database Errors
  // ───────────────────────────────────────────────────────────

  describe('database error handling', () => {
    it('should handle connection lost', async () => {
      jest.spyOn(repository, 'find').mockRejectedValue(
        new Error('Connection lost')
      );

      await expect(service.getUsers())
        .rejects.toThrow(DatabaseError);
    });

    it('should handle unique constraint violation', async () => {
      jest.spyOn(repository, 'save').mockRejectedValue({
        code: '23505',  // PostgreSQL unique violation
        detail: 'Key (email)=(test@test.com) already exists'
      });

      await expect(service.createUser({ email: 'test@test.com' }))
        .rejects.toThrow(ConflictError);
    });

    it('should rollback transaction on error', async () => {
      const queryRunner = mockQueryRunner();
      jest.spyOn(queryRunner, 'commitTransaction')
        .mockRejectedValue(new Error('Commit failed'));

      await expect(service.transferFunds(100, 'A', 'B'))
        .rejects.toThrow();

      expect(queryRunner.rollbackTransaction).toHaveBeenCalled();
    });
  });

  // ───────────────────────────────────────────────────────────
  // Race Conditions
  // ───────────────────────────────────────────────────────────

  describe('race condition handling', () => {
    it('should handle concurrent updates', async () => {
      // 동시에 같은 자원 업데이트 시도
      const update1 = service.updateBalance('user-1', 100);
      const update2 = service.updateBalance('user-1', 200);

      const results = await Promise.allSettled([update1, update2]);

      // 하나는 성공, 하나는 OptimisticLockError
      expect(results.filter(r => r.status === 'fulfilled')).toHaveLength(1);
      expect(results.filter(r => r.status === 'rejected')).toHaveLength(1);
    });
  });
});
```
