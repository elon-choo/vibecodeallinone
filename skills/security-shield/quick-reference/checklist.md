# Security Quick Checklist

## 5 Core Security Principles

```yaml
1. Defense in Depth: "여러 겹의 보안 레이어"
2. Least Privilege: "최소 권한 원칙"
3. Fail Secure: "에러 시 접근 거부"
4. Input Validation: "모든 입력은 검증 후 사용"
5. Output Encoding: "모든 출력은 컨텍스트에 맞게 인코딩"
```

## Instant Security Checklist

### Secrets Management

```markdown
- [ ] 코드에 API 키, 비밀번호, 토큰 없음?
- [ ] 환경변수 또는 Secret Manager 사용?
- [ ] .env 파일이 .gitignore에 있음?
- [ ] .env.example은 값 없이 키만?
```

### Input Validation

```markdown
- [ ] 모든 사용자 입력에 검증 있음?
- [ ] DTO에 class-validator 데코레이터?
- [ ] SQL은 parameterized query 사용?
- [ ] 파일 업로드 타입/크기 제한?
```

### Authentication/Authorization

```markdown
- [ ] 모든 보호 엔드포인트에 Guard 적용?
- [ ] 역할 기반 접근 제어(RBAC) 구현?
- [ ] 비밀번호는 bcrypt/argon2로 해시?
- [ ] JWT 만료 시간 적절? (Access: 15분, Refresh: 7일)
```

### XSS/Injection Prevention

```markdown
- [ ] dangerouslySetInnerHTML 사용 안 함?
- [ ] 사용자 입력을 raw SQL에 넣지 않음?
- [ ] HTML 출력 시 이스케이프?
- [ ] exec()에 사용자 입력 없음?
```

### Error Handling

```markdown
- [ ] 에러 메시지에 민감 정보 없음?
- [ ] 스택 트레이스가 프로덕션에 노출 안 됨?
- [ ] 인증 실패 시 일관된 메시지?
```

## Pre-Deployment Checklist

### Security Headers

```markdown
- [ ] Helmet 미들웨어 적용?
- [ ] Content-Security-Policy 설정?
- [ ] X-Content-Type-Options: nosniff?
- [ ] X-Frame-Options: DENY?
- [ ] CORS 올바르게 설정?
```

### Tokens & Sessions

```markdown
- [ ] Access Token 만료: 15분 이하?
- [ ] Refresh Token 만료: 7일 이하?
- [ ] Refresh Token은 httpOnly 쿠키?
- [ ] Token Rotation 적용?
- [ ] 로그아웃 시 토큰 무효화?
```

### Rate Limiting

```markdown
- [ ] 로그인 API Rate Limiting?
- [ ] 회원가입 API Rate Limiting?
- [ ] 일반 API Rate Limiting?
```

### Dependencies

```markdown
- [ ] npm audit 통과?
- [ ] 취약한 패키지 업데이트?
- [ ] 불필요한 의존성 제거?
```

### Logging

```markdown
- [ ] 보안 이벤트 로깅?
- [ ] 민감 정보 로그에 기록 안 함?
- [ ] 알림 시스템 구축?
```

## OWASP Top 10 Quick Check

| # | Name | Quick Check |
|---|------|-------------|
| A01 | Broken Access Control | 모든 리소스에 소유권/권한 검증? |
| A02 | Cryptographic Failures | bcrypt, AES-256-GCM 사용? |
| A03 | Injection | ORM/parameterized query? |
| A04 | Insecure Design | Rate limiting, 위협 모델링? |
| A05 | Security Misconfiguration | Debug 비활성화, 보안 헤더? |
| A06 | Vulnerable Components | npm audit 통과? |
| A07 | Auth Failures | MFA, 강력한 비밀번호 정책? |
| A08 | Data Integrity | 코드 서명, CI/CD 보안? |
| A09 | Logging Failures | 보안 이벤트 로깅? |
| A10 | SSRF | URL 화이트리스트, 내부 IP 차단? |

## Severity Guide

| Severity | Action | Example |
|----------|--------|---------|
| Critical | 즉시 수정 | 하드코딩된 시크릿, SQL Injection |
| High | 24시간 내 수정 | XSS, Command Injection |
| Medium | 다음 스프린트 | 약한 해시 알고리즘 |
| Low | 백로그 | 로깅 개선 |
