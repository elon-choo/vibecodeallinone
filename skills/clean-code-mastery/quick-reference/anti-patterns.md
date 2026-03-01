# Anti-Pattern Catalog

## Code Smells (Detection → Solution)

---

### Bloaters

#### Long Method
**Detection**: Function > 20 lines, does multiple things
**Solution**: Extract Method, Replace Temp with Query

```typescript
// SMELL: 50+ lines handling multiple concerns
function processOrder(order) {
  // validate (10 lines)
  // calculate (15 lines)
  // update inventory (10 lines)
  // notify (15 lines)
}

// FIX: Single responsibility
function processOrder(order) {
  const validated = validateOrder(order);
  const calculated = calculateTotals(validated);
  updateInventory(calculated);
  notifyCustomer(calculated);
}
```

#### Long Parameter List
**Detection**: Function with > 3 parameters
**Solution**: Introduce Parameter Object, Builder Pattern

```typescript
// SMELL
function createUser(name, email, age, address, phone, role, department) {}

// FIX
interface CreateUserParams {
  name: string;
  email: string;
  age?: number;
  address?: Address;
  phone?: string;
  role?: Role;
  department?: string;
}

function createUser(params: CreateUserParams) {}
```

#### Large Class (God Class)
**Detection**: Class with > 10 methods, > 500 lines, multiple responsibilities
**Solution**: Extract Class, Single Responsibility

```typescript
// SMELL
class UserManager {
  createUser() {}
  deleteUser() {}
  sendEmail() {}
  generateReport() {}
  processPayment() {}
  validateInput() {}
  formatData() {}
  logActivity() {}
}

// FIX
class UserService { createUser() {} deleteUser() {} }
class EmailService { sendEmail() {} }
class ReportService { generateReport() {} }
class PaymentService { processPayment() {} }
```

---

### Object-Orientation Abusers

#### Switch Statements
**Detection**: Same switch in multiple places, switching on type
**Solution**: Replace with Polymorphism

```typescript
// SMELL
function calculateArea(shape) {
  switch (shape.type) {
    case 'circle': return Math.PI * shape.radius ** 2;
    case 'rectangle': return shape.width * shape.height;
    case 'triangle': return 0.5 * shape.base * shape.height;
  }
}

// FIX
interface Shape { calculateArea(): number; }
class Circle implements Shape { calculateArea() { return Math.PI * this.radius ** 2; } }
class Rectangle implements Shape { calculateArea() { return this.width * this.height; } }
```

#### Refused Bequest
**Detection**: Subclass doesn't use inherited methods/properties
**Solution**: Replace Inheritance with Delegation

```typescript
// SMELL
class Stack extends ArrayList {
  // Only uses add/remove from end, but inherits get(index), etc.
}

// FIX
class Stack {
  private items = [];
  push(item) { this.items.push(item); }
  pop() { return this.items.pop(); }
}
```

#### Primitive Obsession
**Detection**: Using primitives for domain concepts (email as string)
**Solution**: Replace Primitive with Object

```typescript
// SMELL
function sendEmail(to: string, subject: string) {
  if (!to.includes('@')) throw new Error('Invalid email');
}

// FIX
class Email {
  constructor(private value: string) {
    if (!value.includes('@')) throw new Error('Invalid email');
  }
  toString() { return this.value; }
}

function sendEmail(to: Email, subject: string) {}
```

---

### Change Preventers

#### Divergent Change
**Detection**: One class changed for multiple different reasons
**Solution**: Extract Class (split responsibilities)

```typescript
// SMELL: Changes for both DB and export reasons
class Order {
  saveToDatabase() {}  // Changes when DB schema changes
  exportToJson() {}    // Changes when JSON format changes
  exportToCsv() {}     // Changes when CSV format changes
}

// FIX
class Order { /* pure domain logic */ }
class OrderRepository { save(order: Order) {} }
class OrderExporter {
  toJson(order: Order) {}
  toCsv(order: Order) {}
}
```

#### Shotgun Surgery
**Detection**: One change requires editing many classes
**Solution**: Move Method, Inline Class

```typescript
// SMELL: Changing fee calculation requires editing 5 classes
class Order { calculateFee() { return this.amount * 0.05; } }
class Invoice { calculateFee() { return this.total * 0.05; } }
class Payment { calculateFee() { return this.value * 0.05; } }

// FIX: Centralize
class FeeCalculator {
  static calculate(amount: number): number {
    return amount * 0.05;
  }
}
```

---

### Dispensables

#### Dead Code
**Detection**: Unreachable code, unused variables/functions
**Solution**: Delete it

```typescript
// SMELL
function process(data) {
  const unused = "this is never used";  // DELETE
  if (false) {  // DELETE
    doSomething();
  }
  return data;
}
```

#### Speculative Generality
**Detection**: "We might need this someday" abstractions
**Solution**: Delete unused abstractions

```typescript
// SMELL: Abstract factory for only one type
interface ShapeFactory { create(): Shape; }
class CircleFactory implements ShapeFactory { create() { return new Circle(); } }
// No other factories exist or planned

// FIX: YAGNI - Just use simple construction
const circle = new Circle();
```

#### Comments (as smell)
**Detection**: Comments explaining what code does (not why)
**Solution**: Extract Method with good name, Rename

```typescript
// SMELL
// Check if the user is an adult
if (user.age >= 18) {}

// FIX
if (user.isAdult()) {}

// or
const isAdult = user.age >= 18;
if (isAdult) {}
```

#### Duplicate Code
**Detection**: Same code in multiple places
**Solution**: Extract Method, Pull Up Method, Template Method

```typescript
// SMELL
class Admin {
  getName() { return this.firstName + ' ' + this.lastName; }
}
class Customer {
  getName() { return this.firstName + ' ' + this.lastName; }
}

// FIX
class Person {
  getName() { return this.firstName + ' ' + this.lastName; }
}
class Admin extends Person {}
class Customer extends Person {}
```

---

### Couplers

#### Feature Envy
**Detection**: Method uses more features of another class
**Solution**: Move Method

```typescript
// SMELL
class Order {
  calculateDiscount() {
    // Uses customer properties more than order properties
    if (this.customer.loyaltyPoints > 1000 &&
        this.customer.memberSince.getFullYear() < 2020 &&
        this.customer.totalPurchases > 10000) {
      return 0.15;
    }
    return 0;
  }
}

// FIX: Move to Customer
class Customer {
  getDiscountRate(): number {
    if (this.loyaltyPoints > 1000 &&
        this.memberSince.getFullYear() < 2020 &&
        this.totalPurchases > 10000) {
      return 0.15;
    }
    return 0;
  }
}
```

#### Inappropriate Intimacy
**Detection**: Classes that know too much about each other's internals
**Solution**: Move Method, Extract Class, Hide Delegate

```typescript
// SMELL
class Order {
  getCustomerAddress() {
    return this.customer._privateAddressData.street;  // Accessing private!
  }
}

// FIX
class Customer {
  getShippingAddress(): string {
    return this.addressData.street;
  }
}
class Order {
  getCustomerAddress() {
    return this.customer.getShippingAddress();
  }
}
```

#### Message Chains
**Detection**: a.getB().getC().getD()
**Solution**: Hide Delegate, Extract Method

```typescript
// SMELL
const city = order.getCustomer().getAddress().getCity();

// FIX: Tell, don't ask
class Order {
  getShippingCity(): string {
    return this.customer.getShippingCity();
  }
}

class Customer {
  getShippingCity(): string {
    return this.address.city;
  }
}

const city = order.getShippingCity();
```

#### Middle Man
**Detection**: Class that only delegates to another class
**Solution**: Remove Middle Man, Inline Method

```typescript
// SMELL
class Manager {
  getDepartment() { return this.department; }
}
class Person {
  getDepartment() { return this.manager.getDepartment(); }  // Just delegates
}

// FIX: Direct access
class Person {
  get department() { return this.manager.department; }
}
```

---

## Security Anti-Patterns

### Hardcoded Secrets
```typescript
// SMELL
const API_KEY = "sk-1234567890abcdef";

// FIX
const API_KEY = process.env.API_KEY;
```

### SQL String Concatenation
```typescript
// SMELL
const query = `SELECT * FROM users WHERE id = '${userId}'`;

// FIX
const query = 'SELECT * FROM users WHERE id = $1';
db.query(query, [userId]);
```

### Trusting User Input
```typescript
// SMELL
app.get('/file/:name', (req, res) => {
  res.sendFile('/uploads/' + req.params.name);
});

// FIX
app.get('/file/:name', (req, res) => {
  const safeName = path.basename(req.params.name);
  const fullPath = path.join('/uploads', safeName);
  if (!fullPath.startsWith('/uploads/')) {
    return res.status(403).send('Forbidden');
  }
  res.sendFile(fullPath);
});
```

### Silent Failures
```typescript
// SMELL
try {
  await riskyOperation();
} catch (e) {
  // Silent failure - bad!
}

// FIX
try {
  await riskyOperation();
} catch (e) {
  logger.error('Operation failed', { error: e });
  throw new OperationError('Failed to complete operation');
}
```

---

## Quick Detection Checklist

| Smell | Quick Check |
|-------|-------------|
| Long Method | > 20 lines? Multiple loops/conditions? |
| Long Parameter List | > 3 parameters? |
| God Class | > 500 lines? > 10 public methods? |
| Feature Envy | Method uses other class more? |
| Duplicate Code | Copy-paste feeling? |
| Dead Code | `// TODO: remove`? Unreachable? |
| Magic Numbers | Unexplained literals? |
| Comments | Explaining "what" not "why"? |
| Deep Nesting | > 3 levels of indentation? |
| Primitive Obsession | String for email/phone/money? |
