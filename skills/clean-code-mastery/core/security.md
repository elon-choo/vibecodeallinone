# Security Principles (OWASP-Based)

## OWASP Top 10 Summary

| # | Vulnerability | Prevention |
|---|---------------|------------|
| A01 | Broken Access Control | RBAC, deny by default |
| A02 | Cryptographic Failures | Strong encryption, no secrets in code |
| A03 | Injection | Parameterized queries, input validation |
| A04 | Insecure Design | Threat modeling, secure patterns |
| A05 | Security Misconfiguration | Secure defaults, minimal exposure |
| A06 | Vulnerable Components | Update dependencies, scan regularly |
| A07 | Auth Failures | MFA, secure session management |
| A08 | Data Integrity Failures | Verify signatures, integrity checks |
| A09 | Logging Failures | Comprehensive audit logs |
| A10 | SSRF | Validate URLs, whitelist domains |

---

## Input Validation

### Always Validate
```typescript
// NEVER trust user input
function processUserInput(input: unknown): SafeData {
  // 1. Type check
  if (typeof input !== 'string') {
    throw new ValidationError('Expected string');
  }

  // 2. Length check
  if (input.length > MAX_LENGTH) {
    throw new ValidationError('Input too long');
  }

  // 3. Pattern check (whitelist approach)
  if (!/^[a-zA-Z0-9_]+$/.test(input)) {
    throw new ValidationError('Invalid characters');
  }

  // 4. Sanitize
  return sanitize(input);
}
```

### Validation Rules
- **Whitelist over blacklist**: Accept known-good, not reject known-bad
- **Validate on server**: Never trust client-side validation
- **Validate early**: Check input at entry points
- **Fail securely**: Reject on any doubt

---

## Output Encoding

### HTML Context
```typescript
// Prevent XSS
function escapeHtml(unsafe: string): string {
  return unsafe
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#039;");
}
```

### URL Context
```typescript
// Always encode URL parameters
const safeUrl = `https://api.example.com/search?q=${encodeURIComponent(userInput)}`;
```

### JavaScript Context
```typescript
// Never directly embed user data in JS
// BAD:
const script = `var data = "${userInput}";`;

// GOOD: Use data attributes
element.dataset.value = JSON.stringify(sanitizedInput);
```

---

## SQL Injection Prevention

### Always Use Parameterized Queries
```typescript
// BAD - SQL Injection vulnerable
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// GOOD - Parameterized
const query = 'SELECT * FROM users WHERE id = $1';
const result = await db.query(query, [userId]);
```

### ORM Best Practices
```typescript
// GOOD - ORM parameterization
const user = await User.findOne({ where: { id: userId } });

// BAD - Raw query with interpolation
const user = await db.raw(`SELECT * FROM users WHERE id = ${userId}`);
```

---

## Authentication & Session

### Password Storage
```typescript
// ALWAYS hash passwords
import * as bcrypt from 'bcrypt';

const SALT_ROUNDS = 12;

async function hashPassword(password: string): Promise<string> {
  return bcrypt.hash(password, SALT_ROUNDS);
}

async function verifyPassword(password: string, hash: string): Promise<boolean> {
  return bcrypt.compare(password, hash);
}
```

### Session Security
```typescript
// Secure session configuration
const sessionConfig = {
  secret: process.env.SESSION_SECRET!, // From environment
  name: 'sessionId',                   // Custom name
  cookie: {
    httpOnly: true,                    // No JS access
    secure: true,                      // HTTPS only
    sameSite: 'strict',                // CSRF protection
    maxAge: 3600000,                   // 1 hour
  },
  resave: false,
  saveUninitialized: false,
};
```

### Token Security
```typescript
// JWT best practices
const tokenConfig = {
  algorithm: 'RS256',           // Asymmetric (not HS256)
  expiresIn: '15m',             // Short-lived
  issuer: 'your-app',
  audience: 'your-api',
};

// Always verify all claims
function verifyToken(token: string): TokenPayload {
  return jwt.verify(token, publicKey, {
    algorithms: ['RS256'],
    issuer: 'your-app',
    audience: 'your-api',
  });
}
```

---

## Secret Management

### Never Hardcode Secrets
```typescript
// BAD
const apiKey = "sk-1234567890abcdef";
const password = "admin123";

// GOOD
const apiKey = process.env.API_KEY;
const password = process.env.DB_PASSWORD;

// Validate at startup
if (!apiKey) {
  throw new Error('API_KEY environment variable required');
}
```

### Environment Variables
```typescript
// Use strict validation
import { z } from 'zod';

const envSchema = z.object({
  DATABASE_URL: z.string().url(),
  API_KEY: z.string().min(32),
  NODE_ENV: z.enum(['development', 'production', 'test']),
});

const env = envSchema.parse(process.env);
```

---

## Access Control

### Deny by Default
```typescript
// Start with no access, grant explicitly
function checkAccess(user: User, resource: Resource): boolean {
  // Default: deny
  if (!user.isAuthenticated) return false;

  // Check explicit permissions
  return user.permissions.includes(resource.requiredPermission);
}
```

### RBAC Implementation
```typescript
enum Role {
  GUEST = 'guest',
  USER = 'user',
  ADMIN = 'admin',
}

const permissions: Record<Role, string[]> = {
  [Role.GUEST]: ['read:public'],
  [Role.USER]: ['read:public', 'read:own', 'write:own'],
  [Role.ADMIN]: ['read:all', 'write:all', 'delete:all'],
};

function hasPermission(role: Role, permission: string): boolean {
  return permissions[role]?.includes(permission) ?? false;
}
```

---

## Secure Error Handling

### Don't Leak Information
```typescript
// BAD - Reveals system info
catch (error) {
  return res.status(500).json({
    error: error.message,
    stack: error.stack,
    query: sql
  });
}

// GOOD - Generic error, log details internally
catch (error) {
  logger.error('Database error', { error, query, userId });
  return res.status(500).json({
    error: 'An unexpected error occurred',
    requestId: generateRequestId()
  });
}
```

### Secure Logging
```typescript
// Never log sensitive data
function logRequest(req: Request) {
  logger.info('API Request', {
    method: req.method,
    path: req.path,
    userId: req.user?.id,
    // DON'T log: passwords, tokens, full credit cards
  });
}

// Mask sensitive data
function maskEmail(email: string): string {
  const [name, domain] = email.split('@');
  return `${name[0]}***@${domain}`;
}
```

---

## CSRF Protection

### Token-Based
```typescript
// Generate CSRF token
function generateCsrfToken(session: Session): string {
  const token = crypto.randomBytes(32).toString('hex');
  session.csrfToken = token;
  return token;
}

// Verify on state-changing requests
function verifyCsrf(req: Request): boolean {
  const headerToken = req.headers['x-csrf-token'];
  const sessionToken = req.session.csrfToken;
  return headerToken === sessionToken;
}
```

### SameSite Cookies
```typescript
// Modern CSRF protection
res.cookie('session', sessionId, {
  sameSite: 'strict',  // or 'lax'
  httpOnly: true,
  secure: true,
});
```

---

## Rate Limiting

```typescript
import rateLimit from 'express-rate-limit';

// General API rate limit
const apiLimiter = rateLimit({
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100,                  // 100 requests per window
  message: 'Too many requests',
  standardHeaders: true,
});

// Stricter for auth endpoints
const authLimiter = rateLimit({
  windowMs: 60 * 60 * 1000, // 1 hour
  max: 5,                    // 5 attempts
  skipSuccessfulRequests: true,
});

app.use('/api/', apiLimiter);
app.use('/api/auth/', authLimiter);
```

---

## Security Headers

```typescript
// Essential security headers
app.use((req, res, next) => {
  res.setHeader('X-Content-Type-Options', 'nosniff');
  res.setHeader('X-Frame-Options', 'DENY');
  res.setHeader('X-XSS-Protection', '1; mode=block');
  res.setHeader('Strict-Transport-Security', 'max-age=31536000; includeSubDomains');
  res.setHeader('Content-Security-Policy', "default-src 'self'");
  res.setHeader('Referrer-Policy', 'strict-origin-when-cross-origin');
  next();
});
```

---

## Dependency Security

### Regular Audits
```bash
# Check for vulnerabilities
npm audit
npm audit fix

# Use security-focused tools
npx snyk test
```

### Lock Dependencies
```json
// package.json - Use exact versions in production
{
  "dependencies": {
    "express": "4.18.2",  // Not "^4.18.2"
  }
}
```

### Update Strategy
- Review changelogs before updating
- Test thoroughly after updates
- Monitor security advisories
- Automate with Dependabot/Renovate
