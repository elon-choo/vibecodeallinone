# Python Clean Code & Security

## Pythonic Code

### PEP 8 Essentials
```python
# Naming conventions
variable_name = "snake_case"       # Variables, functions
CONSTANT_VALUE = 42                 # Constants
ClassName = "PascalCase"            # Classes
_private_var = "leading underscore" # Private
__mangled = "double underscore"     # Name mangling

# Line length: 79 characters (code), 72 (docstrings)
# Indent: 4 spaces (never tabs)
```

### Type Hints (Python 3.9+)
```python
from typing import Optional, Union
from collections.abc import Sequence

# Function signatures
def greet(name: str, times: int = 1) -> str:
    return f"Hello, {name}! " * times

# Optional (can be None)
def find_user(user_id: str) -> Optional[User]:
    return db.get(user_id)

# Modern union syntax (3.10+)
def process(value: int | str) -> None:
    pass

# Generic collections
def process_items(items: list[int]) -> dict[str, int]:
    return {str(i): i for i in items}
```

### Dataclasses
```python
from dataclasses import dataclass, field
from datetime import datetime

# Instead of verbose __init__
@dataclass
class User:
    id: str
    email: str
    name: str
    created_at: datetime = field(default_factory=datetime.now)
    is_active: bool = True

    def __post_init__(self):
        self.email = self.email.lower()

# Immutable dataclass
@dataclass(frozen=True)
class Point:
    x: float
    y: float
```

### Context Managers
```python
# Always use context managers for resources
# BAD
f = open('file.txt')
data = f.read()
f.close()

# GOOD
with open('file.txt') as f:
    data = f.read()

# Custom context manager
from contextlib import contextmanager

@contextmanager
def database_transaction(db):
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
```

---

## Clean Code Patterns

### List Comprehensions (Readable)
```python
# Simple transformation - use comprehension
squares = [x**2 for x in range(10)]

# With condition
evens = [x for x in numbers if x % 2 == 0]

# TOO COMPLEX - use regular loop
# BAD
result = [transform(x) for x in items if validate(x) and check(x) for y in x.children]

# GOOD
result = []
for x in items:
    if not validate(x) or not check(x):
        continue
    for y in x.children:
        result.append(transform(x))
```

### Generator Expressions
```python
# For large data - use generators (lazy evaluation)
# BAD - loads everything into memory
total = sum([x**2 for x in range(1_000_000)])

# GOOD - processes one at a time
total = sum(x**2 for x in range(1_000_000))

# Generator function
def read_large_file(path: str):
    with open(path) as f:
        for line in f:
            yield line.strip()
```

### Enumerate and Zip
```python
# BAD - manual index
for i in range(len(items)):
    print(i, items[i])

# GOOD
for i, item in enumerate(items):
    print(i, item)

# Multiple iterables
for name, age in zip(names, ages):
    print(f"{name} is {age}")

# With strict (Python 3.10+)
for name, age in zip(names, ages, strict=True):
    pass  # Raises if lengths differ
```

### EAFP vs LBYL
```python
# LBYL (Look Before You Leap) - NOT Pythonic
if key in dictionary:
    value = dictionary[key]
else:
    value = default

# EAFP (Easier to Ask Forgiveness) - Pythonic
try:
    value = dictionary[key]
except KeyError:
    value = default

# Even better - use .get()
value = dictionary.get(key, default)
```

---

## Security Patterns

### Command Injection Prevention
```python
import subprocess
import shlex

# BAD - Shell injection vulnerable
user_input = "; rm -rf /"
os.system(f"echo {user_input}")

# GOOD - Use subprocess with list args
subprocess.run(["echo", user_input], check=True)

# If shell=True is needed, quote properly
subprocess.run(
    f"echo {shlex.quote(user_input)}",
    shell=True,
    check=True
)
```

### SQL Injection Prevention
```python
# BAD - SQL Injection vulnerable
query = f"SELECT * FROM users WHERE id = '{user_id}'"
cursor.execute(query)

# GOOD - Parameterized query
query = "SELECT * FROM users WHERE id = %s"
cursor.execute(query, (user_id,))

# SQLAlchemy ORM
user = session.query(User).filter(User.id == user_id).first()

# SQLAlchemy Core with parameters
from sqlalchemy import text
result = conn.execute(
    text("SELECT * FROM users WHERE id = :id"),
    {"id": user_id}
)
```

### Path Traversal Prevention
```python
from pathlib import Path

UPLOAD_DIR = Path("/app/uploads")

# BAD
def read_file(filename: str) -> bytes:
    return open(filename, 'rb').read()

# GOOD
def read_file(filename: str) -> bytes:
    # Resolve to absolute path
    file_path = (UPLOAD_DIR / filename).resolve()

    # Verify it's within allowed directory
    if not file_path.is_relative_to(UPLOAD_DIR):
        raise SecurityError("Path traversal detected")

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {filename}")

    return file_path.read_bytes()
```

### Pickle Security
```python
import pickle
import json

# NEVER unpickle untrusted data
# BAD - Remote code execution risk
data = pickle.loads(user_input)

# GOOD - Use JSON for untrusted data
data = json.loads(user_input)

# If pickle is necessary, use hmac verification
import hmac
import hashlib

SECRET_KEY = os.environ["PICKLE_SECRET"].encode()

def secure_pickle_dumps(obj: object) -> bytes:
    data = pickle.dumps(obj)
    sig = hmac.new(SECRET_KEY, data, hashlib.sha256).digest()
    return sig + data

def secure_pickle_loads(signed_data: bytes) -> object:
    sig, data = signed_data[:32], signed_data[32:]
    expected_sig = hmac.new(SECRET_KEY, data, hashlib.sha256).digest()
    if not hmac.compare_digest(sig, expected_sig):
        raise SecurityError("Invalid signature")
    return pickle.loads(data)
```

### YAML Security
```python
import yaml

# BAD - Arbitrary code execution
data = yaml.load(user_input)  # Dangerous!

# GOOD - Safe loader
data = yaml.safe_load(user_input)
```

### Secrets Management
```python
import os
import secrets

# Generate secure random tokens
token = secrets.token_urlsafe(32)
api_key = secrets.token_hex(32)

# Constant-time comparison (prevent timing attacks)
def verify_token(user_token: str, stored_token: str) -> bool:
    return secrets.compare_digest(user_token, stored_token)

# Environment variables for secrets
DATABASE_URL = os.environ["DATABASE_URL"]
API_KEY = os.environ["API_KEY"]

# Validate at startup
def validate_env():
    required = ["DATABASE_URL", "API_KEY", "SECRET_KEY"]
    missing = [var for var in required if var not in os.environ]
    if missing:
        raise ValueError(f"Missing env vars: {missing}")
```

---

## Error Handling

### Custom Exceptions
```python
class AppError(Exception):
    """Base exception for application"""
    def __init__(self, message: str, code: str = "UNKNOWN"):
        self.message = message
        self.code = code
        super().__init__(message)

class ValidationError(AppError):
    def __init__(self, message: str, field: str = None):
        super().__init__(message, "VALIDATION_ERROR")
        self.field = field

class NotFoundError(AppError):
    def __init__(self, resource: str, id: str):
        super().__init__(f"{resource} with id {id} not found", "NOT_FOUND")
        self.resource = resource
        self.id = id
```

### Exception Handling
```python
# BAD - Bare except
try:
    risky_operation()
except:
    pass  # Silently swallows ALL exceptions

# BAD - Too broad
try:
    risky_operation()
except Exception:
    pass

# GOOD - Specific exceptions
try:
    user = get_user(user_id)
except UserNotFoundError:
    return None
except DatabaseError as e:
    logger.error(f"Database error: {e}")
    raise

# Re-raise with context (Python 3)
try:
    process_data(data)
except ValueError as e:
    raise ProcessingError(f"Failed to process: {data}") from e
```

### Result Pattern
```python
from dataclasses import dataclass
from typing import TypeVar, Generic

T = TypeVar('T')
E = TypeVar('E', bound=Exception)

@dataclass
class Ok(Generic[T]):
    value: T

@dataclass
class Err(Generic[E]):
    error: E

Result = Ok[T] | Err[E]

def find_user(user_id: str) -> Result[User, NotFoundError]:
    user = db.get(user_id)
    if user is None:
        return Err(NotFoundError("User", user_id))
    return Ok(user)

# Usage
result = find_user("123")
match result:
    case Ok(user):
        print(user.name)
    case Err(error):
        print(f"Error: {error.message}")
```

---

## Testing Best Practices

### Pytest Patterns
```python
import pytest
from unittest.mock import Mock, patch

# Fixtures for setup
@pytest.fixture
def user():
    return User(id="1", name="Test", email="test@example.com")

@pytest.fixture
def db_session():
    session = create_session()
    yield session
    session.rollback()
    session.close()

# Parameterized tests
@pytest.mark.parametrize("input,expected", [
    ("hello", "HELLO"),
    ("world", "WORLD"),
    ("", ""),
])
def test_uppercase(input: str, expected: str):
    assert input.upper() == expected

# Mocking
def test_send_email(user):
    with patch('myapp.email.send') as mock_send:
        mock_send.return_value = True
        result = notify_user(user)
        assert result is True
        mock_send.assert_called_once_with(user.email, ANY)
```

---

## Code Smells

### Mutable Default Arguments
```python
# BAD - Shared mutable default
def append_to(item, target=[]):  # Same list instance!
    target.append(item)
    return target

# GOOD
def append_to(item, target=None):
    if target is None:
        target = []
    target.append(item)
    return target
```

### God Functions
```python
# BAD - Does too much
def process_order(order):
    # validate order (20 lines)
    # calculate totals (30 lines)
    # apply discounts (25 lines)
    # process payment (40 lines)
    # send confirmation (15 lines)
    pass

# GOOD - Single responsibility
def process_order(order: Order) -> OrderResult:
    validated = validate_order(order)
    totals = calculate_totals(validated)
    discounted = apply_discounts(totals)
    payment = process_payment(discounted)
    send_confirmation(payment)
    return payment
```

### Magic Numbers
```python
# BAD
if status == 1:
    pass
if age >= 18:
    pass

# GOOD
from enum import Enum, auto

class Status(Enum):
    PENDING = auto()
    ACTIVE = auto()
    COMPLETED = auto()

MINIMUM_AGE = 18

if status == Status.ACTIVE:
    pass
if age >= MINIMUM_AGE:
    pass
```
