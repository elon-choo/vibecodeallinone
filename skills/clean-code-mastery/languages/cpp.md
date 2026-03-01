# C++ Clean Code & Security

## Modern C++ (C++17/20/23)

### Naming Conventions
```cpp
// Classes/Structs: PascalCase
class UserAccount {};
struct Point {};

// Functions/Methods: camelCase or snake_case (be consistent)
void calculateTotal();
void calculate_total();

// Variables: camelCase or snake_case
int itemCount;
int item_count;

// Constants: kPascalCase or SCREAMING_SNAKE_CASE
constexpr int kMaxConnections = 100;
constexpr int MAX_CONNECTIONS = 100;

// Namespaces: lowercase
namespace my_project {}

// Template parameters: PascalCase
template<typename T, typename Allocator>
```

### RAII (Resource Acquisition Is Initialization)
```cpp
// ALWAYS use RAII for resource management
// BAD - Manual memory management
void processFile(const std::string& path) {
    FILE* f = fopen(path.c_str(), "r");
    // ... if exception thrown, file leaks
    fclose(f);
}

// GOOD - RAII wrapper
void processFile(const std::string& path) {
    std::ifstream file(path);  // Opens on construction
    // ... exception safe
}  // Closes automatically on destruction

// Custom RAII wrapper
class DatabaseConnection {
public:
    explicit DatabaseConnection(const std::string& connStr)
        : conn_(db_connect(connStr)) {}

    ~DatabaseConnection() {
        if (conn_) db_disconnect(conn_);
    }

    // Non-copyable
    DatabaseConnection(const DatabaseConnection&) = delete;
    DatabaseConnection& operator=(const DatabaseConnection&) = delete;

    // Movable
    DatabaseConnection(DatabaseConnection&& other) noexcept
        : conn_(std::exchange(other.conn_, nullptr)) {}

private:
    DB_HANDLE conn_;
};
```

### Smart Pointers
```cpp
// NEVER use raw new/delete
// BAD
Widget* w = new Widget();
delete w;

// GOOD - std::unique_ptr for single ownership
auto widget = std::make_unique<Widget>();

// GOOD - std::shared_ptr for shared ownership
auto shared = std::make_shared<Widget>();

// Use std::weak_ptr to break cycles
class Node {
    std::shared_ptr<Node> next;
    std::weak_ptr<Node> parent;  // Prevents cycle
};

// Pass by reference when not transferring ownership
void process(const Widget& widget);  // Read-only
void modify(Widget& widget);         // Modifiable

// Transfer ownership explicitly
void takeOwnership(std::unique_ptr<Widget> widget);
```

### Move Semantics
```cpp
class Buffer {
public:
    explicit Buffer(size_t size) : data_(new char[size]), size_(size) {}

    // Move constructor
    Buffer(Buffer&& other) noexcept
        : data_(std::exchange(other.data_, nullptr))
        , size_(std::exchange(other.size_, 0)) {}

    // Move assignment
    Buffer& operator=(Buffer&& other) noexcept {
        if (this != &other) {
            delete[] data_;
            data_ = std::exchange(other.data_, nullptr);
            size_ = std::exchange(other.size_, 0);
        }
        return *this;
    }

    ~Buffer() { delete[] data_; }

private:
    char* data_;
    size_t size_;
};

// Use std::move to transfer ownership
auto buf1 = Buffer(1024);
auto buf2 = std::move(buf1);  // buf1 is now empty
```

---

## Error Handling

### Exceptions (Modern Approach)
```cpp
// Define exception hierarchy
class AppError : public std::runtime_error {
public:
    explicit AppError(const std::string& msg) : std::runtime_error(msg) {}
};

class NotFoundError : public AppError {
public:
    explicit NotFoundError(const std::string& resource)
        : AppError("Not found: " + resource) {}
};

class ValidationError : public AppError {
public:
    explicit ValidationError(const std::string& msg)
        : AppError("Validation failed: " + msg) {}
};

// noexcept for functions that don't throw
void swap(int& a, int& b) noexcept {
    int temp = a;
    a = b;
    b = temp;
}
```

### std::optional (C++17)
```cpp
#include <optional>

// Return optional instead of nullptr/sentinel
std::optional<User> findUser(const std::string& id) {
    auto it = users.find(id);
    if (it == users.end()) {
        return std::nullopt;
    }
    return it->second;
}

// Usage
if (auto user = findUser("123"); user) {
    std::cout << user->name << '\n';
}

// Or with value_or
auto user = findUser("123").value_or(defaultUser);
```

### std::expected (C++23)
```cpp
#include <expected>

enum class Error {
    NotFound,
    InvalidInput,
    DatabaseError
};

std::expected<User, Error> findUser(const std::string& id) {
    if (id.empty()) {
        return std::unexpected(Error::InvalidInput);
    }
    auto it = users.find(id);
    if (it == users.end()) {
        return std::unexpected(Error::NotFound);
    }
    return it->second;
}

// Usage
auto result = findUser("123");
if (result) {
    process(*result);
} else {
    handleError(result.error());
}
```

---

## Security Patterns

### Buffer Overflow Prevention
```cpp
// BAD - Buffer overflow risk
char buffer[64];
strcpy(buffer, userInput);  // No bounds checking

// GOOD - Use safe alternatives
std::string buffer(userInput);  // std::string manages memory

// For C-style APIs, use strncpy with null termination
char buffer[64];
strncpy(buffer, userInput, sizeof(buffer) - 1);
buffer[sizeof(buffer) - 1] = '\0';

// BETTER - Use std::array with bounds checking
std::array<char, 64> buffer;
auto len = std::min(strlen(userInput), buffer.size() - 1);
std::copy_n(userInput, len, buffer.begin());
buffer[len] = '\0';
```

### Integer Overflow
```cpp
#include <limits>
#include <stdexcept>

// BAD - Potential overflow
int add(int a, int b) {
    return a + b;  // Can overflow silently
}

// GOOD - Check for overflow
int safeAdd(int a, int b) {
    if (b > 0 && a > std::numeric_limits<int>::max() - b) {
        throw std::overflow_error("Integer overflow");
    }
    if (b < 0 && a < std::numeric_limits<int>::min() - b) {
        throw std::underflow_error("Integer underflow");
    }
    return a + b;
}

// Or use SafeInt library / compiler builtins
#if defined(__GNUC__)
int safeAdd(int a, int b) {
    int result;
    if (__builtin_add_overflow(a, b, &result)) {
        throw std::overflow_error("Integer overflow");
    }
    return result;
}
#endif
```

### Format String Vulnerabilities
```cpp
// BAD - Format string attack
printf(userInput);  // User can inject %s, %n, etc.

// GOOD - Always use format specifier
printf("%s", userInput);

// BETTER - Use C++ streams or fmt library
std::cout << userInput;

#include <fmt/format.h>
fmt::print("{}", userInput);
```

### Memory Safety
```cpp
// Use containers instead of raw arrays
// BAD
int* arr = new int[100];
// ... might forget to delete[]

// GOOD
std::vector<int> arr(100);

// Use string_view for non-owning strings (C++17)
void process(std::string_view input) {
    // No allocation, just view
}

// Use span for non-owning array views (C++20)
void process(std::span<const int> data) {
    for (int val : data) {
        // Safe iteration with bounds
    }
}
```

### Secure Random
```cpp
#include <random>

// BAD - Predictable
srand(time(nullptr));
int value = rand();

// GOOD - Cryptographically secure
std::random_device rd;  // Hardware entropy
std::mt19937 gen(rd());
std::uniform_int_distribution<> dis(1, 100);
int value = dis(gen);

// For security-critical: use platform-specific CSPRNG
#ifdef _WIN32
    #include <bcrypt.h>
    std::vector<uint8_t> secureRandom(size_t size) {
        std::vector<uint8_t> buffer(size);
        BCryptGenRandom(nullptr, buffer.data(), size,
                        BCRYPT_USE_SYSTEM_PREFERRED_RNG);
        return buffer;
    }
#else
    #include <sys/random.h>
    std::vector<uint8_t> secureRandom(size_t size) {
        std::vector<uint8_t> buffer(size);
        getrandom(buffer.data(), size, 0);
        return buffer;
    }
#endif
```

### Input Validation
```cpp
#include <regex>
#include <string_view>

class Validator {
public:
    static bool isEmail(std::string_view input) {
        static const std::regex emailRegex(
            R"([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,})");
        return std::regex_match(input.begin(), input.end(), emailRegex);
    }

    static bool isAlphanumeric(std::string_view input) {
        return std::all_of(input.begin(), input.end(), [](char c) {
            return std::isalnum(static_cast<unsigned char>(c));
        });
    }

    static std::string sanitize(std::string_view input, size_t maxLen) {
        std::string result;
        result.reserve(std::min(input.size(), maxLen));

        for (char c : input) {
            if (result.size() >= maxLen) break;
            if (std::isprint(static_cast<unsigned char>(c))) {
                result += c;
            }
        }
        return result;
    }
};
```

---

## Modern C++ Features

### Structured Bindings (C++17)
```cpp
// Tuple unpacking
auto [name, age, score] = std::make_tuple("John", 30, 95.5);

// Map iteration
std::map<std::string, int> scores;
for (const auto& [name, score] : scores) {
    std::cout << name << ": " << score << '\n';
}

// Struct unpacking
struct Point { int x, y; };
Point p{10, 20};
auto [x, y] = p;
```

### constexpr and consteval
```cpp
// Compile-time computation
constexpr int factorial(int n) {
    return n <= 1 ? 1 : n * factorial(n - 1);
}

constexpr int fact5 = factorial(5);  // Computed at compile time

// C++20: consteval (must be evaluated at compile time)
consteval int mustBeCompileTime(int n) {
    return n * n;
}

// C++20: constinit (initialized at compile time, not const)
constinit int globalValue = factorial(10);
```

### Concepts (C++20)
```cpp
#include <concepts>

// Define constraint
template<typename T>
concept Numeric = std::is_arithmetic_v<T>;

template<typename T>
concept Printable = requires(T t) {
    { std::cout << t } -> std::same_as<std::ostream&>;
};

// Use concepts
template<Numeric T>
T add(T a, T b) {
    return a + b;
}

// Multiple constraints
template<typename T>
    requires Numeric<T> && std::totally_ordered<T>
T max(T a, T b) {
    return a > b ? a : b;
}
```

---

## Testing

### Google Test Patterns
```cpp
#include <gtest/gtest.h>

class UserServiceTest : public ::testing::Test {
protected:
    void SetUp() override {
        repo_ = std::make_unique<MockUserRepository>();
        service_ = std::make_unique<UserService>(repo_.get());
    }

    std::unique_ptr<MockUserRepository> repo_;
    std::unique_ptr<UserService> service_;
};

TEST_F(UserServiceTest, FindsExistingUser) {
    // Arrange
    User expected{"1", "John"};
    EXPECT_CALL(*repo_, findById("1"))
        .WillOnce(Return(expected));

    // Act
    auto result = service_->findById("1");

    // Assert
    ASSERT_TRUE(result.has_value());
    EXPECT_EQ(result->name, "John");
}

// Parameterized test
class ValidationTest : public ::testing::TestWithParam<std::string> {};

TEST_P(ValidationTest, RejectsInvalidInput) {
    EXPECT_FALSE(Validator::isEmail(GetParam()));
}

INSTANTIATE_TEST_SUITE_P(
    InvalidEmails,
    ValidationTest,
    ::testing::Values("", "invalid", "@example.com", "test@")
);
```

---

## Code Smells

### Raw Pointers for Ownership
```cpp
// BAD
class Container {
    Widget* widget;  // Who owns this?
public:
    ~Container() { delete widget; }  // Maybe double-free?
};

// GOOD
class Container {
    std::unique_ptr<Widget> widget;  // Clear ownership
};
```

### Manual Resource Management
```cpp
// BAD
void process() {
    auto* conn = new Connection();
    // ... code that might throw ...
    delete conn;  // Might leak
}

// GOOD
void process() {
    auto conn = std::make_unique<Connection>();
    // ... exception safe ...
}
```

### Magic Numbers
```cpp
// BAD
if (status == 1) { }
buffer.resize(1024);

// GOOD
enum class Status { Active = 1, Inactive = 0 };
constexpr size_t BUFFER_SIZE = 1024;

if (status == Status::Active) { }
buffer.resize(BUFFER_SIZE);
```
