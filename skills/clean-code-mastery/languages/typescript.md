# TypeScript/JavaScript Clean Code & Security

## TypeScript Best Practices

### Strict Mode
```json
// tsconfig.json - Always enable strict mode
{
  "compilerOptions": {
    "strict": true,
    "noImplicitAny": true,
    "strictNullChecks": true,
    "noImplicitReturns": true,
    "noFallthroughCasesInSwitch": true,
    "noUncheckedIndexedAccess": true
  }
}
```

### Type Safety

#### Avoid `any`
```typescript
// BAD
function processData(data: any) {
  return data.value;  // No type safety
}

// GOOD
interface DataItem {
  value: string;
  timestamp: number;
}

function processData(data: DataItem): string {
  return data.value;
}
```

#### Use Union Types Over Enums
```typescript
// PREFER - Tree-shakeable, simpler
type Status = 'pending' | 'active' | 'completed';

// AVOID - Complex transpilation
enum Status {
  Pending,
  Active,
  Completed
}
```

#### Discriminated Unions
```typescript
// Type-safe state handling
type LoadingState =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: Data }
  | { status: 'error'; error: Error };

function handleState(state: LoadingState) {
  switch (state.status) {
    case 'idle':
      return <Idle />;
    case 'loading':
      return <Spinner />;
    case 'success':
      return <Content data={state.data} />; // data is typed!
    case 'error':
      return <Error error={state.error} />; // error is typed!
  }
}
```

### Null Safety

#### Use Optional Chaining
```typescript
// BAD
const city = user && user.address && user.address.city;

// GOOD
const city = user?.address?.city;
```

#### Nullish Coalescing
```typescript
// BAD - Treats 0, '', false as falsy
const value = input || 'default';

// GOOD - Only null/undefined trigger default
const value = input ?? 'default';
```

#### Assertion Functions
```typescript
function assertDefined<T>(value: T | null | undefined, message?: string): asserts value is T {
  if (value === null || value === undefined) {
    throw new Error(message ?? 'Value is not defined');
  }
}

// Usage
const user = getUser();
assertDefined(user, 'User not found');
user.name; // TypeScript knows user is defined
```

---

## Async/Await Patterns

### Always Handle Errors
```typescript
// BAD - Unhandled rejection
async function fetchData() {
  const response = await fetch(url);
  return response.json();
}

// GOOD - Proper error handling
async function fetchData(): Promise<Result<Data, Error>> {
  try {
    const response = await fetch(url);
    if (!response.ok) {
      throw new HttpError(response.status);
    }
    return { ok: true, data: await response.json() };
  } catch (error) {
    return { ok: false, error: error instanceof Error ? error : new Error(String(error)) };
  }
}
```

### Parallel vs Sequential
```typescript
// SEQUENTIAL - Slow
const user = await getUser(id);
const orders = await getOrders(id);
const payments = await getPayments(id);

// PARALLEL - Fast
const [user, orders, payments] = await Promise.all([
  getUser(id),
  getOrders(id),
  getPayments(id)
]);

// PARALLEL with error handling
const results = await Promise.allSettled([
  getUser(id),
  getOrders(id),
  getPayments(id)
]);

results.forEach((result, i) => {
  if (result.status === 'rejected') {
    console.error(`Request ${i} failed:`, result.reason);
  }
});
```

---

## Security Patterns

### XSS Prevention
```typescript
// NEVER use innerHTML with user data
// BAD
element.innerHTML = userInput;

// GOOD - Use textContent
element.textContent = userInput;

// Or sanitize explicitly
import DOMPurify from 'dompurify';
element.innerHTML = DOMPurify.sanitize(userInput);
```

### Prototype Pollution Prevention
```typescript
// BAD - Vulnerable to __proto__ injection
function merge(target: any, source: any) {
  for (const key in source) {
    target[key] = source[key];
  }
}

// GOOD - Protect against prototype pollution
function safeMerge<T extends object>(target: T, source: Partial<T>): T {
  const dangerousKeys = ['__proto__', 'constructor', 'prototype'];

  for (const key of Object.keys(source) as (keyof T)[]) {
    if (dangerousKeys.includes(key as string)) continue;
    if (!Object.prototype.hasOwnProperty.call(source, key)) continue;

    target[key] = source[key] as T[keyof T];
  }
  return target;
}
```

### Safe JSON Parsing
```typescript
// BAD - Can throw
const data = JSON.parse(userInput);

// GOOD - Safe parsing
function safeJsonParse<T>(json: string, fallback: T): T {
  try {
    return JSON.parse(json) as T;
  } catch {
    return fallback;
  }
}

// With Zod validation
import { z } from 'zod';

const UserSchema = z.object({
  id: z.string().uuid(),
  email: z.string().email(),
  age: z.number().int().positive().optional(),
});

function parseUser(json: string): User | null {
  try {
    const data = JSON.parse(json);
    return UserSchema.parse(data);
  } catch {
    return null;
  }
}
```

### Path Traversal Prevention
```typescript
import path from 'path';

// BAD - Allows ../../../etc/passwd
function readFile(filename: string) {
  return fs.readFileSync(filename);
}

// GOOD - Restrict to allowed directory
function readFile(filename: string): Buffer {
  const ALLOWED_DIR = '/app/uploads';
  const normalized = path.normalize(filename);
  const resolved = path.resolve(ALLOWED_DIR, normalized);

  // Ensure path is within allowed directory
  if (!resolved.startsWith(ALLOWED_DIR)) {
    throw new SecurityError('Path traversal attempt');
  }

  return fs.readFileSync(resolved);
}
```

### ReDoS Prevention
```typescript
// BAD - Catastrophic backtracking
const emailRegex = /^([a-zA-Z0-9_\.\-])+\@(([a-zA-Z0-9\-])+\.)+([a-zA-Z0-9]{2,4})+$/;

// GOOD - Use proven libraries
import { isEmail } from 'validator';

function validateEmail(email: string): boolean {
  return isEmail(email);
}

// Or use atomic groups / possessive quantifiers
const safeEmailRegex = /^[\w.+-]+@[\w-]+\.[\w.-]+$/;
```

---

## React-Specific Patterns

### Component Props
```typescript
// Use interface for props
interface ButtonProps {
  label: string;
  onClick: () => void;
  variant?: 'primary' | 'secondary';
  disabled?: boolean;
}

// Destructure with defaults
function Button({
  label,
  onClick,
  variant = 'primary',
  disabled = false
}: ButtonProps) {
  return (
    <button
      className={`btn btn-${variant}`}
      onClick={onClick}
      disabled={disabled}
    >
      {label}
    </button>
  );
}
```

### Secure Event Handlers
```typescript
// BAD - Possible XSS via href
<a href={userUrl}>Link</a>

// GOOD - Validate URL
function SafeLink({ url, children }: { url: string; children: React.ReactNode }) {
  const isValid = url.startsWith('https://') || url.startsWith('/');

  if (!isValid) {
    console.warn('Invalid URL blocked:', url);
    return <span>{children}</span>;
  }

  return <a href={url}>{children}</a>;
}
```

### State Management
```typescript
// BAD - Mutating state directly
const [items, setItems] = useState<Item[]>([]);
items.push(newItem);  // Mutation!

// GOOD - Immutable updates
setItems(prev => [...prev, newItem]);
setItems(prev => prev.filter(item => item.id !== id));
setItems(prev => prev.map(item =>
  item.id === id ? { ...item, ...updates } : item
));
```

---

## Error Handling Patterns

### Custom Error Classes
```typescript
class AppError extends Error {
  constructor(
    message: string,
    public code: string,
    public statusCode: number = 500
  ) {
    super(message);
    this.name = this.constructor.name;
    Error.captureStackTrace(this, this.constructor);
  }
}

class ValidationError extends AppError {
  constructor(message: string) {
    super(message, 'VALIDATION_ERROR', 400);
  }
}

class NotFoundError extends AppError {
  constructor(resource: string) {
    super(`${resource} not found`, 'NOT_FOUND', 404);
  }
}
```

### Result Type Pattern
```typescript
type Result<T, E = Error> =
  | { ok: true; value: T }
  | { ok: false; error: E };

async function findUser(id: string): Promise<Result<User>> {
  try {
    const user = await db.users.findUnique({ where: { id } });
    if (!user) {
      return { ok: false, error: new NotFoundError('User') };
    }
    return { ok: true, value: user };
  } catch (error) {
    return { ok: false, error: error as Error };
  }
}

// Usage
const result = await findUser(id);
if (result.ok) {
  console.log(result.value.name);
} else {
  console.error(result.error.message);
}
```

---

## Code Smells to Avoid

### God Objects
```typescript
// BAD - Does everything
class UserManager {
  createUser() { }
  deleteUser() { }
  sendEmail() { }
  generateReport() { }
  processPayment() { }
}

// GOOD - Single responsibility
class UserService { createUser() { } deleteUser() { } }
class EmailService { sendEmail() { } }
class ReportService { generateReport() { } }
class PaymentService { processPayment() { } }
```

### Long Parameter Lists
```typescript
// BAD
function createOrder(
  userId: string,
  productId: string,
  quantity: number,
  price: number,
  discount: number,
  shipping: string,
  notes: string
) { }

// GOOD - Use object parameter
interface CreateOrderParams {
  userId: string;
  productId: string;
  quantity: number;
  price: number;
  discount?: number;
  shipping: string;
  notes?: string;
}

function createOrder(params: CreateOrderParams) { }
```

### Magic Numbers
```typescript
// BAD
if (status === 1) { }
if (age >= 18) { }

// GOOD
const STATUS_ACTIVE = 1;
const MINIMUM_AGE = 18;

if (status === STATUS_ACTIVE) { }
if (age >= MINIMUM_AGE) { }
```
