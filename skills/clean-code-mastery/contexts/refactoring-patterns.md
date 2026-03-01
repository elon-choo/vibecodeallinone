# Refactoring Patterns

Based on Martin Fowler's Refactoring Catalog

---

## Extract Method

**When**: You have a code fragment that can be grouped together.

```typescript
// BEFORE
function printOwing() {
  printBanner();

  // Print details
  console.log("name: " + name);
  console.log("amount: " + getOutstanding());
}

// AFTER
function printOwing() {
  printBanner();
  printDetails();
}

function printDetails() {
  console.log("name: " + name);
  console.log("amount: " + getOutstanding());
}
```

**Benefits**: Improves readability, enables reuse, reduces duplication.

---

## Inline Method

**When**: A method body is just as clear as its name.

```typescript
// BEFORE
function getRating(): number {
  return moreThanFiveLateDeliveries() ? 2 : 1;
}

function moreThanFiveLateDeliveries(): boolean {
  return numberOfLateDeliveries > 5;
}

// AFTER
function getRating(): number {
  return numberOfLateDeliveries > 5 ? 2 : 1;
}
```

---

## Extract Variable

**When**: You have a complicated expression.

```typescript
// BEFORE
if (
  platform.toUpperCase().indexOf("MAC") > -1 &&
  browser.toUpperCase().indexOf("IE") > -1 &&
  wasInitialized() &&
  resize > 0
) { }

// AFTER
const isMacOs = platform.toUpperCase().indexOf("MAC") > -1;
const isIE = browser.toUpperCase().indexOf("IE") > -1;
const wasResized = resize > 0;

if (isMacOs && isIE && wasInitialized() && wasResized) { }
```

---

## Replace Temp with Query

**When**: A temporary variable holds the result of an expression.

```typescript
// BEFORE
function calculateTotal() {
  const basePrice = quantity * itemPrice;
  if (basePrice > 1000) {
    return basePrice * 0.95;
  }
  return basePrice * 0.98;
}

// AFTER
function calculateTotal() {
  if (basePrice() > 1000) {
    return basePrice() * 0.95;
  }
  return basePrice() * 0.98;
}

function basePrice() {
  return quantity * itemPrice;
}
```

---

## Replace Conditional with Polymorphism

**When**: You have a conditional that chooses behavior based on type.

```typescript
// BEFORE
function getSpeed(vehicle: Vehicle): number {
  switch (vehicle.type) {
    case "car":
      return vehicle.baseSpeed;
    case "bicycle":
      return vehicle.baseSpeed - 10;
    case "plane":
      return vehicle.baseSpeed * 3;
  }
}

// AFTER
interface Vehicle {
  getSpeed(): number;
}

class Car implements Vehicle {
  getSpeed(): number { return this.baseSpeed; }
}

class Bicycle implements Vehicle {
  getSpeed(): number { return this.baseSpeed - 10; }
}

class Plane implements Vehicle {
  getSpeed(): number { return this.baseSpeed * 3; }
}
```

---

## Replace Nested Conditional with Guard Clauses

**When**: You have nested conditions obscuring the main logic.

```typescript
// BEFORE
function getPayAmount(): number {
  let result: number;
  if (isDead) {
    result = deadAmount();
  } else {
    if (isSeparated) {
      result = separatedAmount();
    } else {
      if (isRetired) {
        result = retiredAmount();
      } else {
        result = normalPayAmount();
      }
    }
  }
  return result;
}

// AFTER
function getPayAmount(): number {
  if (isDead) return deadAmount();
  if (isSeparated) return separatedAmount();
  if (isRetired) return retiredAmount();
  return normalPayAmount();
}
```

---

## Replace Magic Number with Constant

**When**: You have a literal number with special meaning.

```typescript
// BEFORE
function potentialEnergy(mass: number, height: number): number {
  return mass * height * 9.81;
}

// AFTER
const GRAVITATIONAL_CONSTANT = 9.81;

function potentialEnergy(mass: number, height: number): number {
  return mass * height * GRAVITATIONAL_CONSTANT;
}
```

---

## Introduce Parameter Object

**When**: Multiple parameters naturally group together.

```typescript
// BEFORE
function amountInvoiced(startDate: Date, endDate: Date): number { }
function amountReceived(startDate: Date, endDate: Date): number { }
function amountOverdue(startDate: Date, endDate: Date): number { }

// AFTER
interface DateRange {
  start: Date;
  end: Date;
}

function amountInvoiced(range: DateRange): number { }
function amountReceived(range: DateRange): number { }
function amountOverdue(range: DateRange): number { }
```

---

## Replace Constructor with Factory Method

**When**: You need more flexibility than a simple constructor provides.

```typescript
// BEFORE
class Employee {
  constructor(public name: string, public type: string) {
    // ...
  }
}

// AFTER
class Employee {
  constructor(public name: string) { }

  static createEngineer(name: string): Employee {
    const employee = new Employee(name);
    employee.type = "engineer";
    return employee;
  }

  static createManager(name: string): Employee {
    const employee = new Employee(name);
    employee.type = "manager";
    return employee;
  }
}
```

---

## Extract Class

**When**: A class is doing the work of two.

```typescript
// BEFORE
class Person {
  name: string;
  officeAreaCode: string;
  officeNumber: string;

  getTelephoneNumber(): string {
    return `(${this.officeAreaCode}) ${this.officeNumber}`;
  }
}

// AFTER
class Person {
  name: string;
  telephoneNumber: TelephoneNumber;
}

class TelephoneNumber {
  areaCode: string;
  number: string;

  getTelephoneNumber(): string {
    return `(${this.areaCode}) ${this.number}`;
  }
}
```

---

## Move Method

**When**: A method uses more features of another class than its own.

```typescript
// BEFORE
class Account {
  overdraftCharge(): number {
    if (this.type.isPremium()) {
      const baseCharge = 10;
      if (this.daysOverdrawn > 7) {
        return baseCharge + (this.daysOverdrawn - 7) * 0.85;
      }
      return baseCharge;
    }
    return this.daysOverdrawn * 1.75;
  }
}

// AFTER
class AccountType {
  overdraftCharge(daysOverdrawn: number): number {
    if (this.isPremium()) {
      const baseCharge = 10;
      if (daysOverdrawn > 7) {
        return baseCharge + (daysOverdrawn - 7) * 0.85;
      }
      return baseCharge;
    }
    return daysOverdrawn * 1.75;
  }
}
```

---

## Replace Type Code with Subclasses

**When**: You have a type code that affects behavior.

```typescript
// BEFORE
class Employee {
  type: "engineer" | "manager" | "salesman";

  get bonus(): number {
    switch (this.type) {
      case "engineer": return 0;
      case "manager": return 1000;
      case "salesman": return this.sales * 0.1;
    }
  }
}

// AFTER
abstract class Employee {
  abstract get bonus(): number;
}

class Engineer extends Employee {
  get bonus(): number { return 0; }
}

class Manager extends Employee {
  get bonus(): number { return 1000; }
}

class Salesman extends Employee {
  get bonus(): number { return this.sales * 0.1; }
}
```

---

## Decompose Conditional

**When**: Complex conditional (if-then-else) is hard to understand.

```typescript
// BEFORE
if (date.before(SUMMER_START) || date.after(SUMMER_END)) {
  charge = quantity * winterRate + winterServiceCharge;
} else {
  charge = quantity * summerRate;
}

// AFTER
if (isSummer(date)) {
  charge = summerCharge(quantity);
} else {
  charge = winterCharge(quantity);
}

function isSummer(date: Date): boolean {
  return !date.before(SUMMER_START) && !date.after(SUMMER_END);
}

function summerCharge(quantity: number): number {
  return quantity * summerRate;
}

function winterCharge(quantity: number): number {
  return quantity * winterRate + winterServiceCharge;
}
```

---

## Combine Functions into Class

**When**: A group of functions operate on the same data.

```typescript
// BEFORE
function baseRate(reading: Reading) { }
function taxableCharge(reading: Reading) { }
function calculateBaseCharge(reading: Reading) { }

// AFTER
class Reading {
  constructor(private data: ReadingData) { }

  get baseRate(): number { }
  get taxableCharge(): number { }
  get baseCharge(): number { }
}
```

---

## Split Phase

**When**: Code deals with two different things.

```typescript
// BEFORE
function priceOrder(product: Product, quantity: number, shippingMethod: ShippingMethod) {
  const basePrice = product.basePrice * quantity;
  const discount = Math.max(quantity - 500, 0) * product.basePrice * 0.05;
  const shippingPerCase = (basePrice > 100)
    ? shippingMethod.discountedFee
    : shippingMethod.feePerCase;
  const shippingCost = quantity * shippingPerCase;
  const price = basePrice - discount + shippingCost;
  return price;
}

// AFTER
function priceOrder(product: Product, quantity: number, shippingMethod: ShippingMethod) {
  const priceData = calculatePricingData(product, quantity);
  return applyShipping(priceData, shippingMethod);
}

function calculatePricingData(product: Product, quantity: number) {
  const basePrice = product.basePrice * quantity;
  const discount = Math.max(quantity - 500, 0) * product.basePrice * 0.05;
  return { basePrice, quantity, discount };
}

function applyShipping(priceData: PriceData, shippingMethod: ShippingMethod) {
  const shippingPerCase = (priceData.basePrice > 100)
    ? shippingMethod.discountedFee
    : shippingMethod.feePerCase;
  const shippingCost = priceData.quantity * shippingPerCase;
  return priceData.basePrice - priceData.discount + shippingCost;
}
```

---

## Refactoring Decision Matrix

| Code Smell | Refactoring |
|------------|-------------|
| Long Method | Extract Method |
| Long Parameter List | Introduce Parameter Object |
| Duplicated Code | Extract Method, Pull Up Method |
| Feature Envy | Move Method |
| Data Clumps | Extract Class |
| Primitive Obsession | Replace Primitive with Object |
| Switch Statements | Replace with Polymorphism |
| Lazy Class | Inline Class |
| Speculative Generality | Remove |
| Temporary Field | Extract Class |
| Message Chains | Hide Delegate |
| Middle Man | Remove Middle Man |
| Comments | Extract Method, Rename |

---

## Safe Refactoring Steps

1. **Ensure tests pass** before starting
2. **Make small changes** one at a time
3. **Run tests** after each change
4. **Commit frequently** with clear messages
5. **Review diff** before pushing
