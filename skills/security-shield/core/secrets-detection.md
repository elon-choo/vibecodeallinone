# Hardcoded Secrets Detection Patterns

## 40+ Detection Patterns

### API Keys

```yaml
pattern_1:
  name: "Generic API Key"
  regex: "(api[_-]?key|apikey)\\s*[=:]\\s*['\"][a-zA-Z0-9_\\-]{20,}['\"]"
  severity: critical
  message: "API 키가 코드에 하드코딩됨"

pattern_2:
  name: "AWS Access Key"
  regex: "AKIA[0-9A-Z]{16}"
  severity: critical
  message: "AWS Access Key 발견"

pattern_3:
  name: "AWS Secret Key"
  regex: "['\"][a-zA-Z0-9/+=]{40}['\"]"
  severity: critical
  message: "AWS Secret Key 가능성"

pattern_4:
  name: "Google API Key"
  regex: "AIza[0-9A-Za-z\\-_]{35}"
  severity: critical
  message: "Google API Key 발견"

pattern_5:
  name: "Stripe API Key"
  regex: "(sk|pk)_(live|test)_[0-9a-zA-Z]{24,}"
  severity: critical
  message: "Stripe API Key 발견"

pattern_6:
  name: "OpenAI API Key"
  regex: "sk-[a-zA-Z0-9]{48}"
  severity: critical
  message: "OpenAI API Key 발견"

pattern_7:
  name: "GitHub Token"
  regex: "ghp_[a-zA-Z0-9]{36}|github_pat_[a-zA-Z0-9]{22}_[a-zA-Z0-9]{59}"
  severity: critical
  message: "GitHub Personal Access Token 발견"

pattern_8:
  name: "Slack Token"
  regex: "xox[baprs]-[0-9]{10,13}-[0-9]{10,13}[a-zA-Z0-9-]*"
  severity: critical
  message: "Slack Token 발견"
```

### Passwords

```yaml
pattern_9:
  name: "Password Assignment"
  regex: "(password|passwd|pwd)\\s*[=:]\\s*['\"][^'\"]{8,}['\"]"
  severity: critical
  message: "비밀번호가 코드에 하드코딩됨"

pattern_10:
  name: "DB Password"
  regex: "(db_?password|database_?password)\\s*[=:]\\s*['\"][^'\"]+['\"]"
  severity: critical
  message: "DB 비밀번호가 코드에 하드코딩됨"

pattern_11:
  name: "Admin Password"
  regex: "(admin_?password|root_?password)\\s*[=:]\\s*['\"][^'\"]+['\"]"
  severity: critical
  message: "관리자 비밀번호가 코드에 하드코딩됨"
```

### Tokens

```yaml
pattern_12:
  name: "JWT Token"
  regex: "eyJ[a-zA-Z0-9_-]*\\.eyJ[a-zA-Z0-9_-]*\\.[a-zA-Z0-9_-]*"
  severity: high
  message: "JWT 토큰이 코드에 하드코딩됨"

pattern_13:
  name: "Bearer Token"
  regex: "(bearer|token)\\s*[=:]\\s*['\"][a-zA-Z0-9_\\-\\.]{20,}['\"]"
  severity: high
  message: "Bearer 토큰이 코드에 하드코딩됨"

pattern_14:
  name: "OAuth Token"
  regex: "(oauth|access_?token|refresh_?token)\\s*[=:]\\s*['\"][^'\"]{20,}['\"]"
  severity: critical
  message: "OAuth 토큰이 코드에 하드코딩됨"
```

### Private Keys

```yaml
pattern_15:
  name: "RSA Private Key"
  regex: "-----BEGIN RSA PRIVATE KEY-----"
  severity: critical
  message: "RSA Private Key가 코드에 포함됨"

pattern_16:
  name: "EC Private Key"
  regex: "-----BEGIN EC PRIVATE KEY-----"
  severity: critical
  message: "EC Private Key가 코드에 포함됨"

pattern_17:
  name: "Generic Private Key"
  regex: "-----BEGIN PRIVATE KEY-----"
  severity: critical
  message: "Private Key가 코드에 포함됨"

pattern_18:
  name: "SSH Private Key"
  regex: "-----BEGIN OPENSSH PRIVATE KEY-----"
  severity: critical
  message: "SSH Private Key가 코드에 포함됨"
```

### Connection Strings

```yaml
pattern_19:
  name: "MongoDB Connection"
  regex: "mongodb(\\+srv)?://[^\\s'\"]+:[^\\s'\"]+@"
  severity: critical
  message: "MongoDB 연결 문자열에 인증 정보 포함"

pattern_20:
  name: "PostgreSQL Connection"
  regex: "postgres(ql)?://[^\\s'\"]+:[^\\s'\"]+@"
  severity: critical
  message: "PostgreSQL 연결 문자열에 인증 정보 포함"

pattern_21:
  name: "MySQL Connection"
  regex: "mysql://[^\\s'\"]+:[^\\s'\"]+@"
  severity: critical
  message: "MySQL 연결 문자열에 인증 정보 포함"

pattern_22:
  name: "Redis Connection"
  regex: "redis://:[^\\s'\"]+@"
  severity: critical
  message: "Redis 연결 문자열에 비밀번호 포함"

pattern_23:
  name: "Supabase Connection"
  regex: "postgres://postgres\\.[^:]+:[^@]+@"
  severity: critical
  message: "Supabase 연결 문자열에 인증 정보 포함"
```

### Webhook URLs

```yaml
pattern_24:
  name: "Slack Webhook"
  regex: "https://hooks\\.slack\\.com/services/T[A-Z0-9]+/B[A-Z0-9]+/[a-zA-Z0-9]+"
  severity: high
  message: "Slack Webhook URL 발견"

pattern_25:
  name: "Discord Webhook"
  regex: "https://discord(app)?\\.com/api/webhooks/[0-9]+/[a-zA-Z0-9_-]+"
  severity: high
  message: "Discord Webhook URL 발견"
```

## Safe Alternatives

### Environment Variables (NestJS)

```typescript
// .env (절대 커밋하지 않음!)
// API_KEY=sk-1234567890abcdef

// app.module.ts
import { ConfigModule, ConfigService } from '@nestjs/config';

@Module({
  imports: [
    ConfigModule.forRoot({
      isGlobal: true,
      envFilePath: `.env.${process.env.NODE_ENV}`,
    }),
  ],
})
export class AppModule {}

// 서비스에서 사용
@Injectable()
export class ApiService {
  constructor(private configService: ConfigService) {}

  async callApi() {
    const apiKey = this.configService.get<string>('API_KEY');
    if (!apiKey) {
      throw new Error('API_KEY is not configured');
    }
  }
}
```

### Environment Variables (Next.js)

```javascript
// next.config.js
module.exports = {
  env: {
    // PUBLIC_ prefix = 클라이언트에 노출 가능
    NEXT_PUBLIC_API_URL: process.env.NEXT_PUBLIC_API_URL,
  },
  // 서버 전용 (클라이언트에 노출 안 됨)
  serverRuntimeConfig: {
    apiSecret: process.env.API_SECRET,
  },
};
```

## .env File Management

```yaml
File_Structure:
  ".env": "로컬 개발용 (절대 커밋 금지)"
  ".env.example": "템플릿 (값 없이 키만, 커밋 가능)"
  ".env.development": "개발 환경용"
  ".env.production": "프로덕션용 (절대 커밋 금지)"
  ".env.test": "테스트 환경용"

Gitignore_Must_Include:
  - ".env"
  - ".env.local"
  - ".env.*.local"
  - ".env.production"
  - "*.pem"
  - "*.key"
```
