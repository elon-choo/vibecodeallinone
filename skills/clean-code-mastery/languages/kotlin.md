# Kotlin Clean Code & Security

## Kotlin Idioms

### Naming Conventions
```kotlin
// Classes, Objects, Interfaces: PascalCase
class UserService
object DatabaseConfig
interface UserRepository

// Functions, Properties, Variables: camelCase
fun calculateTotal() {}
val itemCount = 0
var isActive = true

// Constants: SCREAMING_SNAKE_CASE or PascalCase
const val MAX_CONNECTIONS = 100
val DefaultTimeout = 30.seconds  // Non-primitive constants

// Packages: lowercase
package com.example.userservice

// Backing properties
private val _items = mutableListOf<Item>()
val items: List<Item> get() = _items
```

### Null Safety
```kotlin
// Non-nullable by default
var name: String = "John"
// name = null  // Compile error!

// Nullable with ?
var middleName: String? = null

// Safe call operator
val length = middleName?.length  // Returns Int?

// Elvis operator
val length = middleName?.length ?: 0  // Returns Int

// Not-null assertion (use sparingly!)
val length = middleName!!.length  // Throws if null

// Smart cast
fun process(value: String?) {
    if (value != null) {
        // value is automatically String here
        println(value.length)
    }
}

// Let for scoped null checks
user?.let {
    println(it.name)
    sendEmail(it.email)
}
```

### Data Classes
```kotlin
// Automatic equals, hashCode, toString, copy
data class User(
    val id: String,
    val name: String,
    val email: String,
    val createdAt: Instant = Instant.now()
) {
    init {
        require(id.isNotBlank()) { "id cannot be blank" }
        require(email.contains("@")) { "invalid email" }
    }
}

// Destructuring
val (id, name, email) = user

// Non-destructive copy
val updated = user.copy(name = "New Name")
```

### Sealed Classes/Interfaces
```kotlin
sealed interface Result<out T> {
    data class Success<T>(val value: T) : Result<T>
    data class Failure(val error: Throwable) : Result<Nothing>
}

fun <T> Result<T>.getOrNull(): T? = when (this) {
    is Result.Success -> value
    is Result.Failure -> null
}

fun <T> Result<T>.getOrThrow(): T = when (this) {
    is Result.Success -> value
    is Result.Failure -> throw error
}

// Exhaustive when
fun handle(result: Result<User>) = when (result) {
    is Result.Success -> println(result.value.name)
    is Result.Failure -> println(result.error.message)
    // No else needed - compiler enforces exhaustiveness
}
```

### Extension Functions
```kotlin
// Add functionality without inheritance
fun String.isValidEmail(): Boolean {
    return this.contains("@") && this.contains(".")
}

// Usage
if (email.isValidEmail()) { }

// Scoping functions
inline fun <T, R> T.let(block: (T) -> R): R
inline fun <T> T.also(block: (T) -> Unit): T
inline fun <T, R> T.run(block: T.() -> R): R
inline fun <T> T.apply(block: T.() -> Unit): T
inline fun <R> run(block: () -> R): R

// Example usage
val user = User("1", "John", "john@example.com")
    .also { logger.info("Created user: ${it.id}") }
    .apply { validate() }

val result = dbConnection.use { conn ->
    conn.query("SELECT * FROM users")
}
```

---

## Coroutines

### Structured Concurrency
```kotlin
import kotlinx.coroutines.*

// Always use structured concurrency
suspend fun fetchAllData(): CompleteData = coroutineScope {
    val user = async { fetchUser() }
    val orders = async { fetchOrders() }
    val payments = async { fetchPayments() }

    CompleteData(
        user = user.await(),
        orders = orders.await(),
        payments = payments.await()
    )
}

// Cancel-safe operations
suspend fun processItems(items: List<Item>) = coroutineScope {
    items.forEach { item ->
        ensureActive()  // Check for cancellation
        process(item)
    }
}

// Timeout handling
suspend fun fetchWithTimeout(): Data? {
    return withTimeoutOrNull(5000) {
        fetchData()
    }
}
```

### Flow
```kotlin
import kotlinx.coroutines.flow.*

// Cold stream
fun fetchUsers(): Flow<User> = flow {
    val users = api.getUsers()
    users.forEach { emit(it) }
}

// Operators
fetchUsers()
    .filter { it.isActive }
    .map { it.toDto() }
    .catch { e -> emit(ErrorDto(e.message)) }
    .collect { dto -> display(dto) }

// StateFlow for state management
class UserViewModel : ViewModel() {
    private val _state = MutableStateFlow<UiState>(UiState.Loading)
    val state: StateFlow<UiState> = _state.asStateFlow()

    fun loadUser(id: String) {
        viewModelScope.launch {
            _state.value = UiState.Loading
            try {
                val user = repository.getUser(id)
                _state.value = UiState.Success(user)
            } catch (e: Exception) {
                _state.value = UiState.Error(e.message)
            }
        }
    }
}
```

---

## Security Patterns

### SQL Injection Prevention
```kotlin
// BAD - SQL Injection vulnerable
val query = "SELECT * FROM users WHERE id = '$userId'"
connection.prepareStatement(query).executeQuery()

// GOOD - Parameterized query
val query = "SELECT * FROM users WHERE id = ?"
connection.prepareStatement(query).use { stmt ->
    stmt.setString(1, userId)
    stmt.executeQuery()
}

// Exposed ORM (type-safe queries)
object Users : Table() {
    val id = varchar("id", 36)
    val name = varchar("name", 100)
}

fun findUser(id: String): User? {
    return Users.select { Users.id eq id }
        .map { User(it[Users.id], it[Users.name]) }
        .singleOrNull()
}

// JOOQ (type-safe SQL)
dsl.selectFrom(USERS)
    .where(USERS.ID.eq(userId))
    .fetchOne()
```

### Input Validation
```kotlin
// Validation with require/check
class User(val name: String, val email: String, val age: Int) {
    init {
        require(name.isNotBlank()) { "Name cannot be blank" }
        require(email.contains("@")) { "Invalid email format" }
        require(age in 0..150) { "Age must be between 0 and 150" }
    }
}

// Jakarta Validation
data class CreateUserRequest(
    @field:NotBlank
    @field:Size(min = 1, max = 100)
    val name: String,

    @field:NotBlank
    @field:Email
    val email: String,

    @field:Min(0)
    @field:Max(150)
    val age: Int?
)

// Custom validation DSL
class Validator<T>(private val value: T) {
    private val errors = mutableListOf<String>()

    fun validate(predicate: (T) -> Boolean, message: String): Validator<T> {
        if (!predicate(value)) errors.add(message)
        return this
    }

    fun getResult(): Result<T> =
        if (errors.isEmpty()) Result.Success(value)
        else Result.Failure(ValidationException(errors))
}

fun validateUser(user: User) = Validator(user)
    .validate({ it.name.isNotBlank() }, "Name required")
    .validate({ it.email.isValidEmail() }, "Invalid email")
    .getResult()
```

### Path Traversal Prevention
```kotlin
import java.nio.file.Path
import java.nio.file.Paths

class FileService(private val uploadDir: String) {
    fun readFile(filename: String): ByteArray {
        val basePath = Paths.get(uploadDir).toAbsolutePath().normalize()
        val filePath = basePath.resolve(filename).normalize()

        // Verify path is within allowed directory
        require(filePath.startsWith(basePath)) {
            "Path traversal detected"
        }

        return filePath.toFile().readBytes()
    }
}
```

### Secrets Management
```kotlin
// NEVER hardcode secrets
// BAD
private const val API_KEY = "sk-1234567890"

// GOOD - Environment variables
val apiKey = System.getenv("API_KEY")
    ?: throw IllegalStateException("API_KEY not configured")

// GOOD - Config with validation
data class AppConfig(
    val apiKey: String,
    val dbPassword: String
) {
    companion object {
        fun fromEnvironment() = AppConfig(
            apiKey = requireEnv("API_KEY"),
            dbPassword = requireEnv("DB_PASSWORD")
        )

        private fun requireEnv(name: String): String =
            System.getenv(name)
                ?: throw IllegalStateException("$name environment variable required")
    }
}
```

### Cryptography
```kotlin
import java.security.SecureRandom
import javax.crypto.SecretKeyFactory
import javax.crypto.spec.PBEKeySpec

object PasswordHasher {
    private const val ITERATIONS = 120_000
    private const val KEY_LENGTH = 256
    private const val SALT_LENGTH = 16

    fun hash(password: String): String {
        val salt = ByteArray(SALT_LENGTH).also {
            SecureRandom().nextBytes(it)
        }

        val hash = pbkdf2(password, salt)
        return "${salt.toBase64()}:${hash.toBase64()}"
    }

    fun verify(password: String, stored: String): Boolean {
        val (saltBase64, hashBase64) = stored.split(":")
        val salt = saltBase64.fromBase64()
        val expectedHash = hashBase64.fromBase64()
        val actualHash = pbkdf2(password, salt)

        return actualHash.contentEquals(expectedHash)
    }

    private fun pbkdf2(password: String, salt: ByteArray): ByteArray {
        val spec = PBEKeySpec(password.toCharArray(), salt, ITERATIONS, KEY_LENGTH)
        return SecretKeyFactory.getInstance("PBKDF2WithHmacSHA256")
            .generateSecret(spec)
            .encoded
    }
}
```

---

## Error Handling

### Sealed Result Types
```kotlin
sealed class Result<out T, out E> {
    data class Success<T>(val value: T) : Result<T, Nothing>()
    data class Failure<E>(val error: E) : Result<Nothing, E>()

    inline fun <R> map(transform: (T) -> R): Result<R, E> = when (this) {
        is Success -> Success(transform(value))
        is Failure -> this
    }

    inline fun <R> flatMap(transform: (T) -> Result<R, E>): Result<R, E> = when (this) {
        is Success -> transform(value)
        is Failure -> this
    }

    inline fun onSuccess(action: (T) -> Unit): Result<T, E> {
        if (this is Success) action(value)
        return this
    }

    inline fun onFailure(action: (E) -> Unit): Result<T, E> {
        if (this is Failure) action(error)
        return this
    }
}

// Usage
suspend fun getUser(id: String): Result<User, AppError> {
    return try {
        val user = repository.findById(id)
            ?: return Result.Failure(AppError.NotFound("User", id))
        Result.Success(user)
    } catch (e: Exception) {
        Result.Failure(AppError.Database(e.message))
    }
}

getUser("123")
    .map { it.toDto() }
    .onSuccess { render(it) }
    .onFailure { showError(it.message) }
```

### runCatching
```kotlin
// Built-in Result type
val result: Result<User> = runCatching {
    repository.getUser(id)
}

result
    .onSuccess { user -> display(user) }
    .onFailure { error -> showError(error) }

val user = result.getOrNull()
val user = result.getOrDefault(defaultUser)
val user = result.getOrElse { error -> handleError(error) }
```

---

## Testing

### Kotest
```kotlin
class UserServiceTest : FunSpec({
    val mockRepo = mockk<UserRepository>()
    val service = UserService(mockRepo)

    test("should find user by id") {
        // Arrange
        val expected = User("1", "John", "john@example.com")
        coEvery { mockRepo.findById("1") } returns expected

        // Act
        val result = service.getUser("1")

        // Assert
        result shouldBe expected
    }

    test("should throw for blank id") {
        shouldThrow<IllegalArgumentException> {
            service.getUser("")
        }
    }
})

// Property-based testing
class MathTest : StringSpec({
    "addition is commutative" {
        checkAll<Int, Int> { a, b ->
            a + b shouldBe b + a
        }
    }
})
```

### MockK
```kotlin
// Mocking
val mockRepo = mockk<UserRepository>()

// Stubbing
every { mockRepo.findById("1") } returns user
coEvery { mockRepo.findByIdAsync("1") } returns user

// Verification
verify { mockRepo.findById("1") }
coVerify { mockRepo.findByIdAsync("1") }

// Argument capture
val slot = slot<User>()
every { mockRepo.save(capture(slot)) } returns Unit
// slot.captured contains the argument
```

---

## Code Smells

### Platform Types
```kotlin
// BAD - Java interop without null safety
val javaList = JavaClass.getList()  // List<String!>
val first = javaList[0]  // Might NPE!

// GOOD - Explicit null handling
val javaList: List<String>? = JavaClass.getList()
val first = javaList?.firstOrNull()
```

### Overusing !!
```kotlin
// BAD
val name = user!!.name!!.trim()

// GOOD
val name = user?.name?.trim() ?: "Unknown"

// Or handle the null case explicitly
val name = requireNotNull(user?.name) { "User name required" }
```

### God Classes
```kotlin
// BAD
class UserManager {
    fun createUser() { }
    fun sendEmail() { }
    fun generateReport() { }
    fun processPayment() { }
}

// GOOD
class UserService { }
class EmailService { }
class ReportService { }
class PaymentService { }
```

### Mutable Data Classes
```kotlin
// BAD - Mutable data class
data class User(var name: String, var email: String)

// GOOD - Immutable with copy
data class User(val name: String, val email: String)
val updated = user.copy(name = "New Name")
```
