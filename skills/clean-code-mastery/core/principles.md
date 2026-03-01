# Clean Code Core Principles

## SOLID Principles

### S - Single Responsibility Principle (SRP)
```
A class/function should have only ONE reason to change.
```

**Bad:**
```typescript
class User {
  saveToDatabase() { /* DB logic */ }
  sendEmail() { /* Email logic */ }
  generateReport() { /* Report logic */ }
}
```

**Good:**
```typescript
class User { /* Only user data */ }
class UserRepository { saveToDatabase(user: User) { } }
class EmailService { sendEmail(to: string) { } }
class ReportGenerator { generate(user: User) { } }
```

### O - Open/Closed Principle (OCP)
```
Open for extension, closed for modification.
```

**Bad:**
```typescript
function calculateArea(shape: any) {
  if (shape.type === 'circle') return Math.PI * shape.radius ** 2;
  if (shape.type === 'rectangle') return shape.width * shape.height;
  // Adding new shape = modifying this function
}
```

**Good:**
```typescript
interface Shape { calculateArea(): number; }
class Circle implements Shape { calculateArea() { return Math.PI * this.radius ** 2; } }
class Rectangle implements Shape { calculateArea() { return this.width * this.height; } }
// Adding new shape = new class, no modification
```

### L - Liskov Substitution Principle (LSP)
```
Subtypes must be substitutable for their base types.
```

**Bad:**
```typescript
class Bird { fly() { } }
class Penguin extends Bird { fly() { throw new Error("Can't fly!"); } }
```

**Good:**
```typescript
class Bird { }
class FlyingBird extends Bird { fly() { } }
class Penguin extends Bird { swim() { } }
```

### I - Interface Segregation Principle (ISP)
```
Many specific interfaces > One general interface.
```

**Bad:**
```typescript
interface Worker {
  work(): void;
  eat(): void;
  sleep(): void;
}
class Robot implements Worker {
  eat() { throw new Error("Robots don't eat"); }
  sleep() { throw new Error("Robots don't sleep"); }
}
```

**Good:**
```typescript
interface Workable { work(): void; }
interface Eatable { eat(): void; }
interface Sleepable { sleep(): void; }
class Robot implements Workable { work() { } }
class Human implements Workable, Eatable, Sleepable { }
```

### D - Dependency Inversion Principle (DIP)
```
Depend on abstractions, not concretions.
```

**Bad:**
```typescript
class MySQLDatabase { query() { } }
class UserService {
  private db = new MySQLDatabase(); // Tightly coupled
}
```

**Good:**
```typescript
interface Database { query(): void; }
class UserService {
  constructor(private db: Database) { } // Loosely coupled
}
```

---

## DRY (Don't Repeat Yourself)

```
Every piece of knowledge must have a single,
unambiguous, authoritative representation.
```

**Signs of DRY violation:**
- Copy-pasted code blocks
- Same logic in multiple places
- Repeated string literals/magic numbers
- Duplicated validation rules

**Solutions:**
- Extract to functions/methods
- Use constants for magic values
- Create shared utilities
- Apply inheritance/composition

**Example:**
```typescript
// BAD: Repeated validation
function validateEmail(email: string) { /* regex */ }
function validateUserEmail(email: string) { /* same regex */ }

// GOOD: Single source of truth
const EMAIL_REGEX = /^[^\s@]+@[^\s@]+\.[^\s@]+$/;
function validateEmail(email: string): boolean {
  return EMAIL_REGEX.test(email);
}
```

---

## KISS (Keep It Simple, Stupid)

```
Simplicity is the ultimate sophistication.
Most systems work best when kept simple.
```

**Guidelines:**
- Prefer clear over clever code
- Avoid premature optimization
- Use straightforward control flow
- Minimize nesting levels (max 3)
- Functions: 20 lines or less
- Parameters: 3 or fewer

**Bad:**
```typescript
const result = items.reduce((acc, item) =>
  item.active ? { ...acc, [item.id]: item.value * (item.premium ? 1.5 : 1) } : acc, {});
```

**Good:**
```typescript
const result: Record<string, number> = {};
for (const item of items) {
  if (item.active) {
    const multiplier = item.premium ? 1.5 : 1;
    result[item.id] = item.value * multiplier;
  }
}
```

---

## YAGNI (You Aren't Gonna Need It)

```
Don't implement something until it's necessary.
```

**Guidelines:**
- Implement only current requirements
- Avoid "just in case" features
- Don't add unused abstractions
- Delete dead code immediately
- Refactor when requirements change

**Questions before adding:**
1. Is this needed RIGHT NOW?
2. Is there a concrete use case TODAY?
3. Can this be added later easily?

---

## Law of Demeter (LoD)

```
Only talk to your immediate friends.
Don't talk to strangers.
```

**Bad:**
```typescript
// Reaching through multiple objects
order.getCustomer().getAddress().getCity();
```

**Good:**
```typescript
// Tell, don't ask
order.getDeliveryCity();
```

**Rules:**
- Method M of object O may only call methods of:
  - O itself
  - M's parameters
  - Objects created within M
  - O's direct component objects

---

## Composition Over Inheritance

```
Favor object composition over class inheritance.
```

**Why:**
- Inheritance creates tight coupling
- Composition is more flexible
- Multiple behaviors can be combined
- Easier testing with mocks

**Example:**
```typescript
// Instead of: class FlyingSwimmingBird extends FlyingBird, SwimmingBird

// Use composition:
class Duck {
  private flyBehavior: FlyBehavior;
  private swimBehavior: SwimBehavior;

  fly() { this.flyBehavior.execute(); }
  swim() { this.swimBehavior.execute(); }
}
```

---

## Clean Code Metrics

| Metric | Target |
|--------|--------|
| Function Length | ≤ 20 lines |
| Function Parameters | ≤ 3 |
| Cyclomatic Complexity | ≤ 10 |
| Nesting Depth | ≤ 3 |
| Class Methods | ≤ 10 |
| File Length | ≤ 400 lines |

---

## Naming Conventions

### Variables
```
- Use meaningful, pronounceable names
- Use searchable names (no single letters except loops)
- Avoid mental mapping
- Use domain vocabulary
```

### Functions
```
- Start with verb: get, set, calculate, validate, create
- Be specific: getUserById() not getUser()
- No side effects in getters
```

### Classes
```
- Use nouns: User, OrderProcessor, PaymentGateway
- Avoid generic names: Manager, Processor, Data, Info
```

### Booleans
```
- Prefix: is, has, can, should, will
- Examples: isActive, hasPermission, canDelete
```

---

## Error Handling

### Use Exceptions, Not Return Codes
```typescript
// BAD
function withdraw(amount: number): number {
  if (balance < amount) return -1;  // Magic number
  return balance -= amount;
}

// GOOD
function withdraw(amount: number): number {
  if (balance < amount) {
    throw new InsufficientFundsError(balance, amount);
  }
  return balance -= amount;
}
```

### Don't Return Null
```typescript
// BAD
function findUser(id: string): User | null {
  return users.get(id) || null;
}

// GOOD
function findUser(id: string): User {
  const user = users.get(id);
  if (!user) throw new UserNotFoundError(id);
  return user;
}

// Or use Optional pattern
function findUser(id: string): Optional<User> {
  return Optional.ofNullable(users.get(id));
}
```

### Fail Fast
```typescript
function processOrder(order: Order) {
  // Validate early
  if (!order) throw new InvalidOrderError();
  if (!order.items.length) throw new EmptyOrderError();
  if (!order.customer) throw new NoCustomerError();

  // Process only if all validations pass
  return executeOrder(order);
}
```
