# Rust Clean Code & Security

## Rust Idioms

### Naming Conventions
```rust
// snake_case: functions, variables, modules
fn calculate_total() {}
let user_count = 42;
mod user_service;

// PascalCase: types, traits, enums
struct UserAccount {}
trait Serializable {}
enum Status { Active, Inactive }

// SCREAMING_SNAKE_CASE: constants, statics
const MAX_CONNECTIONS: u32 = 100;
static GLOBAL_CONFIG: Config = Config::new();
```

### Ownership & Borrowing
```rust
// Prefer borrowing over ownership transfer
// BAD - Takes ownership unnecessarily
fn print_name(name: String) {
    println!("{}", name);
}

// GOOD - Borrows reference
fn print_name(name: &str) {
    println!("{}", name);
}

// Use &mut only when modification needed
fn increment(value: &mut i32) {
    *value += 1;
}

// Clone only when necessary
let s1 = String::from("hello");
let s2 = s1.clone(); // Explicit, intentional copy
```

### Error Handling
```rust
use std::error::Error;
use std::fmt;

// Custom error type
#[derive(Debug)]
enum AppError {
    NotFound(String),
    Validation(String),
    Database(String),
}

impl fmt::Display for AppError {
    fn fmt(&self, f: &mut fmt::Formatter) -> fmt::Result {
        match self {
            AppError::NotFound(msg) => write!(f, "Not found: {}", msg),
            AppError::Validation(msg) => write!(f, "Validation error: {}", msg),
            AppError::Database(msg) => write!(f, "Database error: {}", msg),
        }
    }
}

impl Error for AppError {}

// Using Result with ?
fn process_user(id: &str) -> Result<User, AppError> {
    let user = find_user(id)?;  // Propagates error
    validate_user(&user)?;
    Ok(user)
}

// Using thiserror for cleaner error types
use thiserror::Error;

#[derive(Error, Debug)]
enum MyError {
    #[error("User {0} not found")]
    NotFound(String),

    #[error("Database error")]
    Database(#[from] sqlx::Error),
}
```

### Option Handling
```rust
// Use combinators instead of explicit matching
// BAD
let value = match opt {
    Some(v) => v,
    None => default_value,
};

// GOOD
let value = opt.unwrap_or(default_value);
let value = opt.unwrap_or_else(|| expensive_default());

// Chaining options
let result = get_user(id)
    .map(|u| u.email)
    .filter(|e| !e.is_empty())
    .unwrap_or_default();

// Never use unwrap in production
// BAD
let value = opt.unwrap();  // Panics on None

// GOOD - Handle the None case
let value = opt.ok_or(MyError::NotFound)?;
```

---

## Type System

### Newtype Pattern
```rust
// Prevent mixing up similar types
struct UserId(String);
struct OrderId(String);

fn find_order(user_id: UserId, order_id: OrderId) -> Order {
    // Can't accidentally swap arguments
}

// With validation
struct Email(String);

impl Email {
    pub fn new(value: &str) -> Result<Self, ValidationError> {
        if !value.contains('@') {
            return Err(ValidationError::InvalidEmail);
        }
        Ok(Email(value.to_string()))
    }

    pub fn as_str(&self) -> &str {
        &self.0
    }
}
```

### Builder Pattern
```rust
#[derive(Default)]
struct RequestBuilder {
    url: Option<String>,
    method: Option<String>,
    headers: Vec<(String, String)>,
    timeout: Option<Duration>,
}

impl RequestBuilder {
    pub fn new() -> Self {
        Self::default()
    }

    pub fn url(mut self, url: impl Into<String>) -> Self {
        self.url = Some(url.into());
        self
    }

    pub fn method(mut self, method: impl Into<String>) -> Self {
        self.method = Some(method.into());
        self
    }

    pub fn header(mut self, key: impl Into<String>, value: impl Into<String>) -> Self {
        self.headers.push((key.into(), value.into()));
        self
    }

    pub fn build(self) -> Result<Request, BuildError> {
        Ok(Request {
            url: self.url.ok_or(BuildError::MissingUrl)?,
            method: self.method.unwrap_or_else(|| "GET".to_string()),
            headers: self.headers,
            timeout: self.timeout,
        })
    }
}

// Usage
let request = RequestBuilder::new()
    .url("https://api.example.com")
    .method("POST")
    .header("Content-Type", "application/json")
    .build()?;
```

---

## Security Patterns

### Memory Safety (Built-in)
```rust
// Rust prevents common vulnerabilities by design:
// - Buffer overflows: Bounds checking
// - Use-after-free: Ownership system
// - Double-free: Single owner
// - Data races: Borrow checker

// Safe indexing
let items = vec![1, 2, 3];
// items[10]  // Panics at runtime

// Use .get() for safe access
if let Some(item) = items.get(10) {
    println!("{}", item);
}
```

### Input Validation
```rust
use validator::Validate;

#[derive(Validate)]
struct UserInput {
    #[validate(length(min = 1, max = 100))]
    name: String,

    #[validate(email)]
    email: String,

    #[validate(range(min = 0, max = 150))]
    age: u8,
}

fn create_user(input: UserInput) -> Result<User, ValidationError> {
    input.validate()?;
    // Process validated input
}
```

### SQL Injection Prevention
```rust
use sqlx::{query_as, PgPool};

// GOOD - Parameterized queries
async fn find_user(pool: &PgPool, id: &str) -> Result<User, sqlx::Error> {
    query_as!(
        User,
        r#"SELECT id, name, email FROM users WHERE id = $1"#,
        id
    )
    .fetch_one(pool)
    .await
}

// sqlx verifies queries at compile time!
```

### Path Traversal Prevention
```rust
use std::path::{Path, PathBuf};

const UPLOAD_DIR: &str = "/app/uploads";

fn safe_read_file(filename: &str) -> Result<Vec<u8>, std::io::Error> {
    let base = Path::new(UPLOAD_DIR).canonicalize()?;
    let requested = base.join(filename).canonicalize()?;

    // Verify path is within allowed directory
    if !requested.starts_with(&base) {
        return Err(std::io::Error::new(
            std::io::ErrorKind::PermissionDenied,
            "Path traversal detected"
        ));
    }

    std::fs::read(requested)
}
```

### Secrets Management
```rust
use secrecy::{Secret, ExposeSecret};

struct Config {
    api_key: Secret<String>,
    db_password: Secret<String>,
}

impl Config {
    fn from_env() -> Result<Self, ConfigError> {
        Ok(Config {
            api_key: Secret::new(
                std::env::var("API_KEY")
                    .map_err(|_| ConfigError::MissingApiKey)?
            ),
            db_password: Secret::new(
                std::env::var("DB_PASSWORD")
                    .map_err(|_| ConfigError::MissingDbPassword)?
            ),
        })
    }
}

// Access secret only when needed
fn make_request(config: &Config) {
    let key = config.api_key.expose_secret();
    // Use key...
}

// Secrets are automatically zeroed on drop
// Debug printing shows "[REDACTED]" not actual value
```

### Cryptography
```rust
use argon2::{self, Config};
use rand::Rng;

// Password hashing
fn hash_password(password: &str) -> String {
    let salt: [u8; 32] = rand::thread_rng().gen();
    let config = Config::default();
    argon2::hash_encoded(password.as_bytes(), &salt, &config)
        .expect("hashing failed")
}

fn verify_password(hash: &str, password: &str) -> bool {
    argon2::verify_encoded(hash, password.as_bytes())
        .unwrap_or(false)
}

// Constant-time comparison
use subtle::ConstantTimeEq;

fn verify_token(provided: &[u8], expected: &[u8]) -> bool {
    provided.ct_eq(expected).into()
}
```

---

## Async Patterns

### Async Error Handling
```rust
use anyhow::{Context, Result};

async fn fetch_user_data(id: &str) -> Result<UserData> {
    let user = fetch_user(id)
        .await
        .context("Failed to fetch user")?;

    let profile = fetch_profile(user.profile_id)
        .await
        .context("Failed to fetch profile")?;

    Ok(UserData { user, profile })
}
```

### Concurrency
```rust
use tokio::task;
use futures::future::join_all;

// Parallel execution
async fn fetch_all(ids: Vec<String>) -> Vec<Result<User, Error>> {
    let tasks: Vec<_> = ids
        .into_iter()
        .map(|id| task::spawn(async move { fetch_user(&id).await }))
        .collect();

    join_all(tasks)
        .await
        .into_iter()
        .map(|r| r.unwrap())
        .collect()
}

// With concurrency limit
use futures::stream::{self, StreamExt};

async fn fetch_with_limit(ids: Vec<String>, limit: usize) -> Vec<User> {
    stream::iter(ids)
        .map(|id| async move { fetch_user(&id).await })
        .buffer_unordered(limit)
        .filter_map(|r| async { r.ok() })
        .collect()
        .await
}
```

---

## Testing

### Unit Tests
```rust
#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add() {
        assert_eq!(add(2, 2), 4);
    }

    #[test]
    fn test_error_case() {
        let result = validate("");
        assert!(result.is_err());
        assert!(matches!(result, Err(ValidationError::Empty)));
    }

    #[test]
    #[should_panic(expected = "division by zero")]
    fn test_panic() {
        divide(1, 0);
    }
}
```

### Property-Based Testing
```rust
use proptest::prelude::*;

proptest! {
    #[test]
    fn test_parse_roundtrip(s in "[a-z]+") {
        let parsed = parse(&s)?;
        let serialized = serialize(&parsed);
        prop_assert_eq!(s, serialized);
    }

    #[test]
    fn test_no_panic(n in any::<i32>()) {
        let _ = process(n);  // Should never panic
    }
}
```

---

## Code Smells

### Unwrap Abuse
```rust
// BAD - Panics in production
let value = some_option.unwrap();
let data = result.unwrap();

// GOOD - Proper error handling
let value = some_option.ok_or(MyError::NotFound)?;
let data = result.map_err(|e| MyError::Processing(e))?;
```

### Clone Overuse
```rust
// BAD - Unnecessary clones
fn process(data: &Data) {
    let owned = data.clone();  // Why?
    do_something(owned);
}

// GOOD - Borrow when possible
fn process(data: &Data) {
    do_something(data);
}
```

### Stringly Typed
```rust
// BAD
fn set_status(status: &str) {
    match status {
        "active" => {},
        "inactive" => {},
        _ => panic!("invalid status"),
    }
}

// GOOD - Use enums
enum Status { Active, Inactive }

fn set_status(status: Status) {
    match status {
        Status::Active => {},
        Status::Inactive => {},
    }
}
```
