# React Security Template

## XSS Prevention

### Safe Rendering

```typescript
// GOOD: React 자동 이스케이프 활용
function CommentDisplay({ comment }: { comment: string }) {
  return <div>{comment}</div>;  // 자동 이스케이프
}
// "<script>" → "&lt;script&gt;"

// BAD: dangerouslySetInnerHTML
function UnsafeComment({ comment }: { comment: string }) {
  return (
    <div dangerouslySetInnerHTML={{ __html: comment }} />  // XSS!
  );
}
```

### Safe HTML with DOMPurify

```typescript
import DOMPurify from 'dompurify';

function RichTextDisplay({ html }: { html: string }) {
  const sanitizedHtml = DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br'],
    ALLOWED_ATTR: ['href', 'target'],
    ALLOW_DATA_ATTR: false,
  });

  return (
    <div dangerouslySetInnerHTML={{ __html: sanitizedHtml }} />
  );
}
```

### Safe URL Handling

```typescript
function SafeLink({ url, children }: { url: string; children: React.ReactNode }) {
  const isSafeUrl = (url: string): boolean => {
    try {
      const parsed = new URL(url);
      return ['http:', 'https:', 'mailto:'].includes(parsed.protocol);
    } catch {
      return false;
    }
  };

  if (!isSafeUrl(url)) {
    return <span>{children}</span>;  // 위험한 URL은 링크로 만들지 않음
  }

  return (
    <a href={url} target="_blank" rel="noopener noreferrer">
      {children}
    </a>
  );
}
```

## Secure Form Handling

### With React Hook Form + Zod

```typescript
import { useForm } from 'react-hook-form';
import { zodResolver } from '@hookform/resolvers/zod';
import { z } from 'zod';

const loginSchema = z.object({
  email: z.string().email('유효한 이메일을 입력하세요'),
  password: z.string().min(8, '비밀번호는 8자 이상이어야 합니다'),
});

type LoginInput = z.infer<typeof loginSchema>;

function LoginForm() {
  const {
    register,
    handleSubmit,
    formState: { errors },
  } = useForm<LoginInput>({
    resolver: zodResolver(loginSchema),
  });

  const onSubmit = async (data: LoginInput) => {
    // data는 검증됨
    await login(data);
  };

  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input
        {...register('email')}
        type="email"
        autoComplete="email"
      />
      {errors.email && <span>{errors.email.message}</span>}

      <input
        {...register('password')}
        type="password"
        autoComplete="current-password"
      />
      {errors.password && <span>{errors.password.message}</span>}

      <button type="submit">로그인</button>
    </form>
  );
}
```

## Secure API Calls

### Axios with Interceptor

```typescript
import axios from 'axios';

const api = axios.create({
  baseURL: process.env.NEXT_PUBLIC_API_URL,
  timeout: 10000,
  withCredentials: true,  // 쿠키 전송
});

// Request Interceptor - Token 추가
api.interceptors.request.use(
  (config) => {
    const token = localStorage.getItem('accessToken');
    if (token) {
      config.headers.Authorization = `Bearer ${token}`;
    }
    return config;
  },
  (error) => Promise.reject(error)
);

// Response Interceptor - Token Refresh
api.interceptors.response.use(
  (response) => response,
  async (error) => {
    const originalRequest = error.config;

    if (error.response?.status === 401 && !originalRequest._retry) {
      originalRequest._retry = true;

      try {
        const { data } = await axios.post('/auth/refresh');
        localStorage.setItem('accessToken', data.accessToken);

        originalRequest.headers.Authorization = `Bearer ${data.accessToken}`;
        return api(originalRequest);
      } catch (refreshError) {
        // Refresh 실패 시 로그아웃
        localStorage.removeItem('accessToken');
        window.location.href = '/login';
        return Promise.reject(refreshError);
      }
    }

    return Promise.reject(error);
  }
);
```

## Secure Storage

### Token Storage Guidelines

```typescript
// DO: httpOnly 쿠키 사용 (Refresh Token)
// Server sets: Set-Cookie: refreshToken=...; HttpOnly; Secure; SameSite=Strict

// Access Token: 메모리 또는 단기 localStorage
class TokenManager {
  private accessToken: string | null = null;

  setAccessToken(token: string) {
    this.accessToken = token;
    // 옵션: 짧은 시간만 localStorage에 저장
    sessionStorage.setItem('accessToken', token);
  }

  getAccessToken(): string | null {
    return this.accessToken || sessionStorage.getItem('accessToken');
  }

  clearTokens() {
    this.accessToken = null;
    sessionStorage.removeItem('accessToken');
  }
}

export const tokenManager = new TokenManager();
```

## Environment Variables

### Next.js Environment Security

```typescript
// .env.local (절대 커밋하지 않음)
API_SECRET=server-only-secret
NEXT_PUBLIC_API_URL=https://api.example.com

// 클라이언트에서 접근
// NEXT_PUBLIC_ prefix가 있는 것만 접근 가능
const apiUrl = process.env.NEXT_PUBLIC_API_URL;

// 서버에서만 접근
// API routes, getServerSideProps 등에서만
export async function getServerSideProps() {
  const secret = process.env.API_SECRET;
}
```

## Security Checklist

```markdown
- [ ] dangerouslySetInnerHTML 사용 시 DOMPurify 적용
- [ ] 외부 URL은 프로토콜 검증
- [ ] 모든 폼에 Zod 검증 적용
- [ ] Access Token은 메모리/sessionStorage
- [ ] Refresh Token은 httpOnly 쿠키
- [ ] HTTPS만 사용 (Secure 쿠키)
- [ ] CSRF 토큰 또는 SameSite=Strict
- [ ] 환경변수에 민감 정보
```
