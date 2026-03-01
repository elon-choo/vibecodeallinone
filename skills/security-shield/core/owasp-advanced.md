# OWASP Top 10 (2021) Advanced Patterns

> **Base Knowledge**: clean-code-mastery/core/security.md 참조
> 이 문서는 고급 패턴과 NestJS 구현에 집중합니다.

## A01: Broken Access Control

### IDOR Prevention

```typescript
// BAD: 권한 검증 없이 리소스 접근
@Get('orders/:id')
async getOrder(@Param('id') id: string) {
  return this.ordersService.findById(id);  // 누구나 모든 주문 조회 가능!
}

// GOOD: 소유권 검증
@Get('orders/:id')
@UseGuards(JwtAuthGuard)
async getOrder(
  @Param('id') id: string,
  @CurrentUser() user: User,
) {
  const order = await this.ordersService.findById(id);

  if (order.userId !== user.id && user.role !== 'admin') {
    throw new ForbiddenException('이 주문에 접근할 권한이 없습니다');
  }

  return order;
}
```

### RBAC Implementation

```typescript
// roles.decorator.ts
import { SetMetadata } from '@nestjs/common';

export const ROLES_KEY = 'roles';
export const Roles = (...roles: string[]) => SetMetadata(ROLES_KEY, roles);

// roles.guard.ts
@Injectable()
export class RolesGuard implements CanActivate {
  constructor(private reflector: Reflector) {}

  canActivate(context: ExecutionContext): boolean {
    const requiredRoles = this.reflector.getAllAndOverride<string[]>(ROLES_KEY, [
      context.getHandler(),
      context.getClass(),
    ]);

    if (!requiredRoles) return true;

    const { user } = context.switchToHttp().getRequest();
    if (!user) throw new UnauthorizedException();

    const hasRole = requiredRoles.some(role => user.roles?.includes(role));
    if (!hasRole) {
      throw new ForbiddenException(
        `이 작업에는 ${requiredRoles.join(' 또는 ')} 역할이 필요합니다`
      );
    }

    return true;
  }
}

// 사용
@Controller('admin')
@UseGuards(JwtAuthGuard, RolesGuard)
export class AdminController {
  @Delete('users/:id')
  @Roles('super-admin')
  async deleteUser(@Param('id') id: string) {
    return this.usersService.delete(id);
  }
}
```

## A02: Cryptographic Failures

### Secure Password Hashing

```typescript
import * as bcrypt from 'bcrypt';

@Injectable()
export class PasswordService {
  private readonly SALT_ROUNDS = 12;

  async hash(password: string): Promise<string> {
    return bcrypt.hash(password, this.SALT_ROUNDS);
  }

  async verify(password: string, hash: string): Promise<boolean> {
    return bcrypt.compare(password, hash);
  }
}
```

### AES-256-GCM Encryption

```typescript
import { createCipheriv, createDecipheriv, randomBytes, scrypt } from 'crypto';

@Injectable()
export class EncryptionService {
  private readonly ALGORITHM = 'aes-256-gcm';

  async encrypt(plaintext: string): Promise<string> {
    const salt = randomBytes(16);
    const iv = randomBytes(16);
    const key = await this.deriveKey(salt);

    const cipher = createCipheriv(this.ALGORITHM, key, iv);
    const encrypted = Buffer.concat([
      cipher.update(plaintext, 'utf8'),
      cipher.final(),
    ]);
    const authTag = cipher.getAuthTag();

    return Buffer.concat([salt, iv, authTag, encrypted]).toString('base64');
  }

  async decrypt(ciphertext: string): Promise<string> {
    const data = Buffer.from(ciphertext, 'base64');
    const salt = data.subarray(0, 16);
    const iv = data.subarray(16, 32);
    const authTag = data.subarray(32, 48);
    const encrypted = data.subarray(48);

    const key = await this.deriveKey(salt);
    const decipher = createDecipheriv(this.ALGORITHM, key, iv);
    decipher.setAuthTag(authTag);

    return Buffer.concat([
      decipher.update(encrypted),
      decipher.final(),
    ]).toString('utf8');
  }
}
```

## A03: Injection (Command)

```typescript
import { execFile } from 'child_process';

// BAD: Command Injection
async function convertImage(filename: string) {
  exec(`convert ${filename} output.png`);
  // 공격: filename = "; rm -rf /"
}

// GOOD: execFile 사용
async function convertImageSafe(filename: string) {
  const sanitizedFilename = filename.replace(/[^a-zA-Z0-9._-]/g, '');
  await execFileAsync('convert', [sanitizedFilename, 'output.png']);
}
```

## A04-A10 Quick Reference

```yaml
A04_Insecure_Design:
  prevention:
    - "위협 모델링 수행"
    - "Rate limiting 적용"
  example: |
    @UseGuards(ThrottlerGuard)
    @Throttle(5, 60)  // 60초에 5회
    async function login(email, password) { ... }

A05_Security_Misconfiguration:
  checklist:
    - "[ ] Debug 모드 비활성화"
    - "[ ] 기본 에러 페이지 커스터마이징"
    - "[ ] CORS 올바르게 설정"

A06_Vulnerable_Components:
  commands:
    - "npm audit"
    - "npm audit fix"
    - "npx npm-check-updates"

A07_Auth_Failures:
  example: |
    JwtModule.register({
      secret: process.env.JWT_SECRET,
      signOptions: { expiresIn: '15m' },
    })

A08_Software_Data_Integrity:
  prevention:
    - "package-lock.json 커밋"
    - "npm ci 사용"

A09_Logging_Monitoring:
  what_to_log:
    - "로그인 성공/실패"
    - "권한 변경"
    - "민감 데이터 접근"

A10_SSRF:
  prevention:
    - "URL 화이트리스트"
    - "내부 IP 차단"
```
