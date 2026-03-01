# Go Clean Code & Security

## Go Idioms

### Naming Conventions
```go
// Package names: lowercase, single word
package http
package user

// Exported (public): PascalCase
func GetUser() {}
type UserService struct {}

// Unexported (private): camelCase
func validateInput() {}
type userRepository struct {}

// Acronyms: consistent case
var httpClient *http.Client  // not Http
var userID string            // not UserId
var xmlParser Parser         // not XmlParser
```

### Error Handling
```go
// Always check errors - NEVER ignore
result, err := doSomething()
if err != nil {
    return fmt.Errorf("doSomething failed: %w", err)
}

// Wrap errors with context
if err != nil {
    return fmt.Errorf("processing user %s: %w", userID, err)
}

// Custom error types
type NotFoundError struct {
    Resource string
    ID       string
}

func (e *NotFoundError) Error() string {
    return fmt.Sprintf("%s with id %s not found", e.Resource, e.ID)
}

// Check error types
if errors.Is(err, sql.ErrNoRows) {
    return &NotFoundError{Resource: "user", ID: id}
}

var notFound *NotFoundError
if errors.As(err, &notFound) {
    // Handle not found
}
```

### Zero Values
```go
// Use zero values meaningfully
type Config struct {
    Timeout  time.Duration // 0 means no timeout
    MaxRetry int           // 0 means no retries
    Enabled  bool          // false means disabled
}

// Check for zero value
if cfg.Timeout == 0 {
    cfg.Timeout = 30 * time.Second // default
}
```

### Defer Patterns
```go
// Use defer for cleanup
func processFile(path string) error {
    f, err := os.Open(path)
    if err != nil {
        return err
    }
    defer f.Close()  // Always called

    // Process file...
    return nil
}

// Defer with error handling
func writeFile(path string, data []byte) (err error) {
    f, err := os.Create(path)
    if err != nil {
        return err
    }
    defer func() {
        closeErr := f.Close()
        if err == nil {
            err = closeErr
        }
    }()

    _, err = f.Write(data)
    return err
}
```

---

## Interface Design

### Small Interfaces
```go
// GOOD - Small, focused interfaces
type Reader interface {
    Read(p []byte) (n int, err error)
}

type Writer interface {
    Write(p []byte) (n int, err error)
}

// Compose when needed
type ReadWriter interface {
    Reader
    Writer
}

// BAD - God interface
type UserManager interface {
    Create(user *User) error
    Update(user *User) error
    Delete(id string) error
    Find(id string) (*User, error)
    List() ([]*User, error)
    SendEmail(user *User, subject, body string) error
    GenerateReport(user *User) ([]byte, error)
}
```

### Accept Interfaces, Return Structs
```go
// GOOD
type Storage interface {
    Save(data []byte) error
}

func NewProcessor(storage Storage) *Processor {
    return &Processor{storage: storage}
}

// Enables testing with mocks
type mockStorage struct{}
func (m *mockStorage) Save(data []byte) error { return nil }
```

---

## Security Patterns

### SQL Injection Prevention
```go
// BAD - SQL injection vulnerable
query := fmt.Sprintf("SELECT * FROM users WHERE id = '%s'", userID)
db.Query(query)

// GOOD - Parameterized queries
query := "SELECT * FROM users WHERE id = $1"
db.Query(query, userID)

// Using sqlx
type User struct {
    ID   string `db:"id"`
    Name string `db:"name"`
}

var user User
err := db.Get(&user, "SELECT * FROM users WHERE id = $1", userID)
```

### Command Injection Prevention
```go
import "os/exec"

// BAD - Shell injection
cmd := exec.Command("sh", "-c", "echo " + userInput)

// GOOD - Pass arguments separately
cmd := exec.Command("echo", userInput)

// GOOD - If shell needed, escape properly
import "github.com/alessio/shellescape"
cmd := exec.Command("sh", "-c", "echo " + shellescape.Quote(userInput))
```

### Path Traversal Prevention
```go
import (
    "path/filepath"
    "strings"
)

const uploadDir = "/app/uploads"

func readFile(filename string) ([]byte, error) {
    // Clean and resolve path
    cleanPath := filepath.Clean(filename)
    fullPath := filepath.Join(uploadDir, cleanPath)

    // Verify within allowed directory
    if !strings.HasPrefix(fullPath, uploadDir) {
        return nil, errors.New("path traversal detected")
    }

    return os.ReadFile(fullPath)
}
```

### Template Injection
```go
import "html/template"

// GOOD - Auto-escapes HTML
tmpl := template.Must(template.New("").Parse(`
    <h1>{{.Title}}</h1>
    <p>{{.Content}}</p>
`))
tmpl.Execute(w, data)

// For trusted HTML, explicitly mark safe
type Page struct {
    Title   string
    Content template.HTML // Trusted HTML
}

// NEVER do this with user input
page.Content = template.HTML(userInput) // DANGEROUS!
```

### Secrets Management
```go
import "os"

// Read from environment
apiKey := os.Getenv("API_KEY")
if apiKey == "" {
    log.Fatal("API_KEY environment variable required")
}

// Constant-time comparison
import "crypto/subtle"

func verifyToken(provided, expected string) bool {
    return subtle.ConstantTimeCompare(
        []byte(provided),
        []byte(expected),
    ) == 1
}

// Secure random generation
import "crypto/rand"

func generateToken(length int) (string, error) {
    bytes := make([]byte, length)
    if _, err := rand.Read(bytes); err != nil {
        return "", err
    }
    return base64.URLEncoding.EncodeToString(bytes), nil
}
```

### HTTP Security
```go
import (
    "net/http"
    "time"
)

// Secure HTTP client
client := &http.Client{
    Timeout: 30 * time.Second,
    Transport: &http.Transport{
        TLSClientConfig: &tls.Config{
            MinVersion: tls.VersionTLS12,
        },
    },
}

// Secure server
server := &http.Server{
    Addr:         ":8080",
    ReadTimeout:  5 * time.Second,
    WriteTimeout: 10 * time.Second,
    IdleTimeout:  120 * time.Second,
}

// Security headers middleware
func securityHeaders(next http.Handler) http.Handler {
    return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
        w.Header().Set("X-Content-Type-Options", "nosniff")
        w.Header().Set("X-Frame-Options", "DENY")
        w.Header().Set("Content-Security-Policy", "default-src 'self'")
        next.ServeHTTP(w, r)
    })
}
```

---

## Concurrency

### Goroutine Management
```go
import (
    "context"
    "sync"
)

// Always use context for cancellation
func worker(ctx context.Context) error {
    for {
        select {
        case <-ctx.Done():
            return ctx.Err()
        default:
            // Do work
        }
    }
}

// Use WaitGroup for multiple goroutines
func processAll(items []Item) {
    var wg sync.WaitGroup
    for _, item := range items {
        wg.Add(1)
        go func(item Item) {
            defer wg.Done()
            process(item)
        }(item)  // Pass item to avoid closure issue
    }
    wg.Wait()
}

// Limit concurrency with semaphore
func processWithLimit(items []Item, limit int) {
    sem := make(chan struct{}, limit)
    var wg sync.WaitGroup

    for _, item := range items {
        wg.Add(1)
        sem <- struct{}{}  // Acquire

        go func(item Item) {
            defer wg.Done()
            defer func() { <-sem }()  // Release
            process(item)
        }(item)
    }
    wg.Wait()
}
```

### Channel Patterns
```go
// Always close channels from sender side
func generate(nums ...int) <-chan int {
    out := make(chan int)
    go func() {
        defer close(out)  // Close when done
        for _, n := range nums {
            out <- n
        }
    }()
    return out
}

// Fan-out, fan-in
func fanOut(in <-chan int, workers int) []<-chan int {
    outs := make([]<-chan int, workers)
    for i := 0; i < workers; i++ {
        outs[i] = worker(in)
    }
    return outs
}

func fanIn(ins ...<-chan int) <-chan int {
    var wg sync.WaitGroup
    out := make(chan int)

    for _, in := range ins {
        wg.Add(1)
        go func(c <-chan int) {
            defer wg.Done()
            for n := range c {
                out <- n
            }
        }(in)
    }

    go func() {
        wg.Wait()
        close(out)
    }()

    return out
}
```

---

## Testing

### Table-Driven Tests
```go
func TestAdd(t *testing.T) {
    tests := []struct {
        name     string
        a, b     int
        expected int
    }{
        {"positive", 2, 3, 5},
        {"negative", -1, -1, -2},
        {"zero", 0, 0, 0},
    }

    for _, tt := range tests {
        t.Run(tt.name, func(t *testing.T) {
            result := Add(tt.a, tt.b)
            if result != tt.expected {
                t.Errorf("Add(%d, %d) = %d; want %d",
                    tt.a, tt.b, result, tt.expected)
            }
        })
    }
}
```

### Mocking with Interfaces
```go
// Production code
type UserRepository interface {
    FindByID(id string) (*User, error)
}

type UserService struct {
    repo UserRepository
}

// Test mock
type mockUserRepo struct {
    users map[string]*User
}

func (m *mockUserRepo) FindByID(id string) (*User, error) {
    if user, ok := m.users[id]; ok {
        return user, nil
    }
    return nil, ErrNotFound
}

func TestUserService(t *testing.T) {
    mock := &mockUserRepo{
        users: map[string]*User{
            "1": {ID: "1", Name: "Test"},
        },
    }
    service := &UserService{repo: mock}
    // Test with mock...
}
```

---

## Code Smells

### Init Abuse
```go
// BAD - Hidden initialization
func init() {
    db = connectToDatabase()  // Side effect, hard to test
}

// GOOD - Explicit initialization
func NewApp(config Config) (*App, error) {
    db, err := connectToDatabase(config.DatabaseURL)
    if err != nil {
        return nil, err
    }
    return &App{db: db}, nil
}
```

### Naked Returns
```go
// BAD - Confusing
func calculate(a, b int) (result int, err error) {
    result = a + b
    return  // Naked return
}

// GOOD - Explicit
func calculate(a, b int) (int, error) {
    result := a + b
    return result, nil
}
```

### Package-Level State
```go
// BAD - Global mutable state
var globalDB *sql.DB

// GOOD - Dependency injection
type Server struct {
    db *sql.DB
}

func NewServer(db *sql.DB) *Server {
    return &Server{db: db}
}
```
