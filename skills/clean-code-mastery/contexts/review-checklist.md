# Code Review Checklist

## Quick Review (5 minutes)

### ✅ Readability
- [ ] Clear, descriptive names (variables, functions, classes)
- [ ] Functions are short (≤20 lines ideal)
- [ ] No deeply nested code (max 3 levels)
- [ ] Comments explain "why", not "what"
- [ ] No commented-out code

### ✅ Structure
- [ ] Single responsibility per function/class
- [ ] No code duplication (DRY)
- [ ] Appropriate abstraction level
- [ ] Dependencies are injected, not hardcoded

### ✅ Error Handling
- [ ] All errors are handled appropriately
- [ ] No silent failures (empty catch blocks)
- [ ] User-friendly error messages
- [ ] No sensitive data in error messages

---

## Detailed Review (15+ minutes)

### 📋 Code Quality

#### Naming
| Check | Status |
|-------|--------|
| Variables describe their content | [ ] |
| Functions describe their action (verb) | [ ] |
| Boolean names start with is/has/can/should | [ ] |
| No abbreviations unless universal | [ ] |
| Consistent naming convention | [ ] |

#### Functions
| Check | Status |
|-------|--------|
| Single responsibility | [ ] |
| ≤3 parameters (use object for more) | [ ] |
| No side effects in getters | [ ] |
| Pure functions where possible | [ ] |
| Appropriate return type (not void when value expected) | [ ] |

#### Classes
| Check | Status |
|-------|--------|
| Single responsibility | [ ] |
| Small, focused interface | [ ] |
| Composition over inheritance | [ ] |
| No god classes | [ ] |
| Dependencies injected | [ ] |

### 🔒 Security

#### Input Validation
| Check | Status |
|-------|--------|
| All user input validated | [ ] |
| Input length limits enforced | [ ] |
| Whitelist approach (not blacklist) | [ ] |
| Type validation | [ ] |
| Range/format validation | [ ] |

#### Injection Prevention
| Check | Status |
|-------|--------|
| Parameterized SQL queries | [ ] |
| No string concatenation in queries | [ ] |
| HTML/JS output encoded | [ ] |
| Command arguments escaped | [ ] |
| Path traversal prevented | [ ] |

#### Authentication & Authorization
| Check | Status |
|-------|--------|
| Passwords properly hashed | [ ] |
| Sessions secured (HttpOnly, Secure, SameSite) | [ ] |
| Authorization checked on every request | [ ] |
| Principle of least privilege | [ ] |
| No credentials in code | [ ] |

#### Data Protection
| Check | Status |
|-------|--------|
| Sensitive data encrypted at rest | [ ] |
| TLS for data in transit | [ ] |
| PII properly handled | [ ] |
| Logs don't contain secrets | [ ] |
| Error messages don't leak info | [ ] |

### ⚡ Performance

#### Efficiency
| Check | Status |
|-------|--------|
| No N+1 queries | [ ] |
| Appropriate data structures | [ ] |
| No unnecessary loops | [ ] |
| Resources properly closed | [ ] |
| Caching where appropriate | [ ] |

#### Memory
| Check | Status |
|-------|--------|
| No memory leaks | [ ] |
| Large objects properly disposed | [ ] |
| Streams/buffers closed | [ ] |
| Event listeners removed | [ ] |

### 🧪 Testability

| Check | Status |
|-------|--------|
| Code is testable (dependencies injectable) | [ ] |
| Pure functions preferred | [ ] |
| No hidden dependencies | [ ] |
| Appropriate test coverage | [ ] |
| Tests follow AAA pattern | [ ] |

---

## Language-Specific Checks

### TypeScript/JavaScript
- [ ] `strict` mode enabled
- [ ] No `any` types (unless necessary)
- [ ] Async errors handled (try/catch or .catch())
- [ ] No `==` comparisons (use `===`)
- [ ] No prototype pollution risks

### Python
- [ ] Type hints used
- [ ] No mutable default arguments
- [ ] Context managers for resources
- [ ] EAFP pattern where appropriate
- [ ] No `eval()` or `exec()` with user input

### Go
- [ ] All errors checked
- [ ] No goroutine leaks
- [ ] Defer used for cleanup
- [ ] Context propagated
- [ ] Proper error wrapping

### Java/Kotlin
- [ ] Null safety handled
- [ ] Resources in try-with-resources
- [ ] No raw types
- [ ] Immutability preferred
- [ ] Proper exception handling

### Rust
- [ ] No `unwrap()` in production
- [ ] Proper error propagation
- [ ] Lifetimes correctly specified
- [ ] No unnecessary clones
- [ ] Safe abstractions for unsafe code

### C++
- [ ] Smart pointers used (no raw new/delete)
- [ ] RAII for resources
- [ ] Move semantics utilized
- [ ] No buffer overflows
- [ ] No undefined behavior

---

## Review Response Template

```markdown
## Code Review Summary

### 🟢 Strengths
- [What's good about this code]

### 🟡 Suggestions
- [Optional improvements]

### 🔴 Issues (Must Fix)
- [Critical issues that must be addressed]

### 🔒 Security
- [Security-related findings]

### Score: [X]/100

| Category | Score |
|----------|-------|
| Readability | /20 |
| Structure | /20 |
| Security | /25 |
| Error Handling | /15 |
| Performance | /10 |
| Testability | /10 |
```

---

## Severity Levels

| Level | Description | Action |
|-------|-------------|--------|
| 🔴 Critical | Security vulnerability, data loss risk | Must fix before merge |
| 🟠 Major | Bug, significant code smell | Should fix before merge |
| 🟡 Minor | Style issue, minor improvement | Can fix later |
| 🟢 Suggestion | Optional enhancement | Nice to have |

---

## Common Review Comments

### Code Style
```
Consider extracting this into a separate function for better readability.
This name doesn't clearly convey the purpose. Suggest: [alternative]
This logic could be simplified using [pattern/technique].
```

### Security
```
⚠️ SECURITY: User input must be validated before use.
⚠️ SECURITY: Use parameterized queries to prevent SQL injection.
⚠️ SECURITY: Sensitive data should not be logged.
```

### Performance
```
Consider using [data structure] for O(1) lookup instead of O(n).
This could cause N+1 query problem. Consider batch loading.
Resource not properly closed - potential memory leak.
```

### Error Handling
```
Empty catch block silently swallows errors. Handle or log appropriately.
Error message exposes internal details. Use generic message for users.
Consider what happens if [operation] fails here.
```
