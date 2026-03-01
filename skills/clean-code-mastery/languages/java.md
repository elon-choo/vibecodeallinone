# Java Clean Code & Security

## Java Idioms

### Naming Conventions
```java
// Classes: PascalCase (nouns)
public class UserService {}
public class OrderRepository {}

// Interfaces: PascalCase (often adjective or capability)
public interface Serializable {}
public interface UserRepository {}

// Methods: camelCase (verbs)
public void calculateTotal() {}
public User findById(String id) {}

// Variables: camelCase
private String userName;
private int orderCount;

// Constants: SCREAMING_SNAKE_CASE
public static final int MAX_CONNECTIONS = 100;
public static final String DEFAULT_TIMEZONE = "UTC";

// Packages: lowercase
package com.example.userservice;
```

### Modern Java (17+)

#### Records (Immutable Data)
```java
// Instead of verbose POJOs
public record User(
    String id,
    String name,
    String email,
    Instant createdAt
) {
    // Compact constructor for validation
    public User {
        Objects.requireNonNull(id, "id cannot be null");
        Objects.requireNonNull(email, "email cannot be null");
    }
}
```

#### Sealed Classes
```java
public sealed interface Result<T>
    permits Success, Failure {
}

public record Success<T>(T value) implements Result<T> {}
public record Failure<T>(Exception error) implements Result<T> {}
```

#### Pattern Matching
```java
// instanceof pattern matching
if (obj instanceof String s) {
    System.out.println(s.length());
}

// Switch expressions (Java 21+)
String result = switch (status) {
    case ACTIVE -> "Active";
    case PENDING -> "Pending";
    case INACTIVE -> "Inactive";
};

// Pattern matching in switch (Java 21+)
String describe(Object obj) {
    return switch (obj) {
        case Integer i -> "Integer: " + i;
        case String s -> "String: " + s;
        case List<?> l -> "List of size: " + l.size();
        case null -> "null";
        default -> "Unknown";
    };
}
```

#### Optional
```java
// Use Optional for return types that can be absent
public Optional<User> findById(String id) {
    return Optional.ofNullable(userMap.get(id));
}

// Never use Optional for fields or parameters
// BAD
private Optional<String> middleName;

// GOOD
private String middleName; // null means absent

// Chain Optional operations
String email = findUser(id)
    .map(User::email)
    .filter(e -> !e.isBlank())
    .orElse("unknown@example.com");

// Throw on missing
User user = findUser(id)
    .orElseThrow(() -> new UserNotFoundException(id));
```

---

## SOLID in Java

### Single Responsibility
```java
// BAD - Multiple responsibilities
public class User {
    public void save() { /* DB logic */ }
    public void sendEmail() { /* Email logic */ }
    public String toJson() { /* Serialization */ }
}

// GOOD - Separated responsibilities
public record User(String id, String name, String email) {}

public class UserRepository {
    public void save(User user) { /* DB logic */ }
}

public class EmailService {
    public void sendWelcome(User user) { /* Email logic */ }
}
```

### Dependency Injection
```java
// BAD - Hard-coded dependency
public class UserService {
    private UserRepository repo = new PostgresUserRepository();
}

// GOOD - Injected dependency
public class UserService {
    private final UserRepository repo;

    public UserService(UserRepository repo) {
        this.repo = repo;
    }
}

// With Spring
@Service
public class UserService {
    private final UserRepository repo;

    @Autowired
    public UserService(UserRepository repo) {
        this.repo = repo;
    }
}
```

---

## Security Patterns

### SQL Injection Prevention
```java
// BAD - SQL Injection vulnerable
String query = "SELECT * FROM users WHERE id = '" + userId + "'";
Statement stmt = conn.createStatement();
ResultSet rs = stmt.executeQuery(query);

// GOOD - PreparedStatement (parameterized)
String query = "SELECT * FROM users WHERE id = ?";
try (PreparedStatement pstmt = conn.prepareStatement(query)) {
    pstmt.setString(1, userId);
    ResultSet rs = pstmt.executeQuery();
}

// JPA/Hibernate - Safe by default
@Query("SELECT u FROM User u WHERE u.id = :id")
Optional<User> findById(@Param("id") String id);
```

### XSS Prevention
```java
// BAD - Direct output
response.getWriter().write(userInput);

// GOOD - Encode HTML
import org.owasp.encoder.Encode;

response.getWriter().write(Encode.forHtml(userInput));

// For different contexts
Encode.forHtmlAttribute(value);
Encode.forJavaScript(value);
Encode.forCssString(value);
Encode.forUriComponent(value);
```

### Path Traversal Prevention
```java
import java.nio.file.Path;
import java.nio.file.Paths;

private static final Path UPLOAD_DIR = Paths.get("/app/uploads").toAbsolutePath();

public byte[] readFile(String filename) throws IOException {
    Path requested = UPLOAD_DIR.resolve(filename).normalize().toAbsolutePath();

    // Verify path is within allowed directory
    if (!requested.startsWith(UPLOAD_DIR)) {
        throw new SecurityException("Path traversal detected");
    }

    return Files.readAllBytes(requested);
}
```

### Deserialization Security
```java
// NEVER deserialize untrusted data directly
// BAD - Remote code execution risk
ObjectInputStream ois = new ObjectInputStream(untrustedInput);
Object obj = ois.readObject();

// GOOD - Use allow-list filter (Java 9+)
ObjectInputFilter filter = ObjectInputFilter.Config.createFilter(
    "com.myapp.model.*;!*"  // Only allow specific classes
);
ois.setObjectInputFilter(filter);

// BETTER - Use safe formats for untrusted data
ObjectMapper mapper = new ObjectMapper();
User user = mapper.readValue(jsonInput, User.class);
```

### Secrets Management
```java
// NEVER hardcode secrets
// BAD
private static final String API_KEY = "sk-1234567890";

// GOOD - Environment variables
private final String apiKey = System.getenv("API_KEY");

// Validate at startup
@PostConstruct
public void validateConfig() {
    Objects.requireNonNull(apiKey, "API_KEY environment variable required");
}

// For passwords, use char[] instead of String
// String is immutable and stays in memory
public void authenticate(char[] password) {
    try {
        // Use password...
    } finally {
        Arrays.fill(password, '\0');  // Clear from memory
    }
}
```

### Password Hashing
```java
import org.springframework.security.crypto.bcrypt.BCryptPasswordEncoder;

public class PasswordService {
    private final BCryptPasswordEncoder encoder = new BCryptPasswordEncoder(12);

    public String hash(String password) {
        return encoder.encode(password);
    }

    public boolean verify(String password, String hash) {
        return encoder.matches(password, hash);
    }
}
```

### Input Validation
```java
import jakarta.validation.constraints.*;

public record CreateUserRequest(
    @NotBlank
    @Size(min = 1, max = 100)
    String name,

    @NotBlank
    @Email
    String email,

    @Min(0)
    @Max(150)
    Integer age,

    @Pattern(regexp = "^\\+?[1-9]\\d{1,14}$")
    String phone
) {}

// In controller
@PostMapping("/users")
public User createUser(@Valid @RequestBody CreateUserRequest request) {
    // Request is already validated
    return userService.create(request);
}
```

---

## Error Handling

### Custom Exceptions
```java
public class AppException extends RuntimeException {
    private final String code;
    private final int statusCode;

    public AppException(String message, String code, int statusCode) {
        super(message);
        this.code = code;
        this.statusCode = statusCode;
    }

    public String getCode() { return code; }
    public int getStatusCode() { return statusCode; }
}

public class NotFoundException extends AppException {
    public NotFoundException(String resource, String id) {
        super(
            String.format("%s with id %s not found", resource, id),
            "NOT_FOUND",
            404
        );
    }
}

public class ValidationException extends AppException {
    private final Map<String, String> errors;

    public ValidationException(Map<String, String> errors) {
        super("Validation failed", "VALIDATION_ERROR", 400);
        this.errors = errors;
    }
}
```

### Try-with-Resources
```java
// Always use try-with-resources for AutoCloseable
// BAD
Connection conn = dataSource.getConnection();
try {
    // Use connection
} finally {
    conn.close();
}

// GOOD
try (Connection conn = dataSource.getConnection();
     PreparedStatement pstmt = conn.prepareStatement(query)) {
    // Use resources
}  // Automatically closed
```

### Global Exception Handler
```java
@RestControllerAdvice
public class GlobalExceptionHandler {

    @ExceptionHandler(NotFoundException.class)
    public ResponseEntity<ErrorResponse> handleNotFound(NotFoundException ex) {
        return ResponseEntity
            .status(HttpStatus.NOT_FOUND)
            .body(new ErrorResponse(ex.getCode(), ex.getMessage()));
    }

    @ExceptionHandler(MethodArgumentNotValidException.class)
    public ResponseEntity<ErrorResponse> handleValidation(MethodArgumentNotValidException ex) {
        Map<String, String> errors = ex.getBindingResult()
            .getFieldErrors()
            .stream()
            .collect(Collectors.toMap(
                FieldError::getField,
                FieldError::getDefaultMessage
            ));
        return ResponseEntity
            .badRequest()
            .body(new ErrorResponse("VALIDATION_ERROR", "Validation failed", errors));
    }

    @ExceptionHandler(Exception.class)
    public ResponseEntity<ErrorResponse> handleGeneric(Exception ex) {
        log.error("Unexpected error", ex);
        return ResponseEntity
            .internalServerError()
            .body(new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred"));
    }
}
```

---

## Testing

### JUnit 5 Patterns
```java
import org.junit.jupiter.api.*;
import static org.junit.jupiter.api.Assertions.*;

class UserServiceTest {

    private UserService service;
    private UserRepository mockRepo;

    @BeforeEach
    void setUp() {
        mockRepo = mock(UserRepository.class);
        service = new UserService(mockRepo);
    }

    @Test
    @DisplayName("Should find user by ID")
    void shouldFindUserById() {
        // Arrange
        var user = new User("1", "John", "john@example.com");
        when(mockRepo.findById("1")).thenReturn(Optional.of(user));

        // Act
        var result = service.findById("1");

        // Assert
        assertNotNull(result);
        assertEquals("John", result.name());
    }

    @ParameterizedTest
    @ValueSource(strings = {"", " ", "   "})
    void shouldRejectBlankNames(String name) {
        assertThrows(ValidationException.class, () -> {
            service.createUser(name, "email@example.com");
        });
    }
}
```

---

## Code Smells

### Null Returns
```java
// BAD
public User findById(String id) {
    return userMap.get(id);  // Returns null if not found
}

// GOOD - Use Optional
public Optional<User> findById(String id) {
    return Optional.ofNullable(userMap.get(id));
}
```

### God Classes
```java
// BAD - Too many responsibilities
public class UserManager {
    public void createUser() {}
    public void deleteUser() {}
    public void sendEmail() {}
    public void generateReport() {}
    public void processPayment() {}
}

// GOOD - Split by responsibility
public class UserService {}
public class EmailService {}
public class ReportService {}
public class PaymentService {}
```

### Primitive Obsession
```java
// BAD
public void createUser(String email, String phone, int age) {}

// GOOD - Value objects
public void createUser(Email email, PhoneNumber phone, Age age) {}

public record Email(String value) {
    public Email {
        if (!value.contains("@")) {
            throw new IllegalArgumentException("Invalid email");
        }
    }
}
```
