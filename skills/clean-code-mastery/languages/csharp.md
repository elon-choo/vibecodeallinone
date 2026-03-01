# C# Clean Code & Security

## C# Idioms

### Naming Conventions
```csharp
// Classes, Structs, Interfaces: PascalCase
public class UserService {}
public struct Point {}
public interface IUserRepository {}  // Prefix with I

// Methods, Properties: PascalCase
public void CalculateTotal() {}
public string Name { get; set; }

// Local variables, parameters: camelCase
var itemCount = 0;
public void Process(string userInput) {}

// Private fields: _camelCase or camelCase
private readonly ILogger _logger;
private int count;

// Constants: PascalCase
public const int MaxConnections = 100;

// Async methods: suffix with Async
public async Task<User> GetUserAsync(string id) {}
```

### Modern C# (10/11/12)

#### Records
```csharp
// Immutable data types
public record User(string Id, string Name, string Email);

// With validation
public record User(string Id, string Name, string Email)
{
    public string Id { get; } = !string.IsNullOrWhiteSpace(Id)
        ? Id : throw new ArgumentException("Id required");
}

// Record with mutable property
public record User(string Id, string Name)
{
    public DateTime LastLogin { get; set; }
}

// Non-destructive mutation
var updated = user with { Name = "New Name" };
```

#### Pattern Matching
```csharp
// Type patterns
if (obj is string s)
{
    Console.WriteLine(s.Length);
}

// Switch expression
var result = status switch
{
    Status.Active => "Active",
    Status.Pending => "Pending",
    Status.Inactive => "Inactive",
    _ => throw new ArgumentOutOfRangeException()
};

// Property patterns
var discount = customer switch
{
    { IsPremium: true, YearsActive: > 5 } => 0.25m,
    { IsPremium: true } => 0.15m,
    { YearsActive: > 3 } => 0.10m,
    _ => 0m
};

// List patterns (C# 11)
var result = numbers switch
{
    [] => "Empty",
    [var single] => $"Single: {single}",
    [var first, .., var last] => $"First: {first}, Last: {last}"
};
```

#### Nullable Reference Types
```csharp
// Enable in .csproj: <Nullable>enable</Nullable>

public class UserService
{
    // Non-nullable (compiler warns if null assigned)
    public string GetName(User user) => user.Name;

    // Nullable (explicitly allowed to be null)
    public User? FindById(string id)
    {
        return _users.GetValueOrDefault(id);
    }

    // Null-forgiving operator (when you know better)
    public string GetNameOrDefault(User? user)
    {
        return user?.Name ?? "Unknown";
    }
}

// Required properties (C# 11)
public class User
{
    public required string Id { get; init; }
    public required string Name { get; init; }
    public string? MiddleName { get; init; }
}
```

#### Primary Constructors (C# 12)
```csharp
// Instead of boilerplate
public class UserService(IUserRepository repository, ILogger<UserService> logger)
{
    public async Task<User?> GetUserAsync(string id)
    {
        logger.LogInformation("Getting user {Id}", id);
        return await repository.FindByIdAsync(id);
    }
}
```

---

## SOLID in C#

### Dependency Injection
```csharp
// Interface
public interface IUserRepository
{
    Task<User?> FindByIdAsync(string id);
    Task SaveAsync(User user);
}

// Implementation
public class SqlUserRepository : IUserRepository
{
    private readonly DbContext _context;

    public SqlUserRepository(DbContext context)
    {
        _context = context;
    }

    public async Task<User?> FindByIdAsync(string id)
        => await _context.Users.FindAsync(id);
}

// Registration (Program.cs / Startup.cs)
services.AddScoped<IUserRepository, SqlUserRepository>();
services.AddScoped<IUserService, UserService>();
```

---

## Security Patterns

### SQL Injection Prevention
```csharp
// BAD - SQL Injection vulnerable
var query = $"SELECT * FROM Users WHERE Id = '{userId}'";
var result = await context.Database.ExecuteSqlRawAsync(query);

// GOOD - Parameterized query
var result = await context.Users
    .FromSqlInterpolated($"SELECT * FROM Users WHERE Id = {userId}")
    .ToListAsync();

// BEST - Use LINQ (EF Core)
var user = await context.Users
    .Where(u => u.Id == userId)
    .FirstOrDefaultAsync();

// Dapper with parameters
var user = await connection.QueryFirstOrDefaultAsync<User>(
    "SELECT * FROM Users WHERE Id = @Id",
    new { Id = userId }
);
```

### XSS Prevention
```csharp
using System.Web;
using System.Text.Encodings.Web;

// Razor automatically encodes by default
// @Model.UserInput  // Safe

// For raw HTML (be careful!)
// @Html.Raw(Model.TrustedHtml)  // Only for trusted content

// Manual encoding
var safeHtml = HtmlEncoder.Default.Encode(userInput);
var safeJs = JavaScriptEncoder.Default.Encode(userInput);
var safeUrl = UrlEncoder.Default.Encode(userInput);

// ASP.NET Core Anti-XSS
services.AddAntiforgery(options =>
{
    options.HeaderName = "X-XSRF-TOKEN";
});
```

### CSRF Protection
```csharp
// In Razor view
<form method="post">
    @Html.AntiForgeryToken()
    ...
</form>

// In controller
[HttpPost]
[ValidateAntiForgeryToken]
public async Task<IActionResult> CreateUser(UserDto dto)
{
    // Token automatically validated
}

// For API with custom header
[HttpPost]
[AutoValidateAntiforgeryToken]
public async Task<IActionResult> ApiEndpoint([FromBody] DataDto dto)
{
    // Validates X-XSRF-TOKEN header
}
```

### Path Traversal Prevention
```csharp
public class FileService
{
    private readonly string _uploadDir = "/app/uploads";

    public async Task<byte[]> ReadFileAsync(string filename)
    {
        // Combine and normalize path
        var fullPath = Path.GetFullPath(Path.Combine(_uploadDir, filename));

        // Verify within allowed directory
        if (!fullPath.StartsWith(_uploadDir, StringComparison.OrdinalIgnoreCase))
        {
            throw new SecurityException("Path traversal detected");
        }

        return await File.ReadAllBytesAsync(fullPath);
    }
}
```

### Secrets Management
```csharp
// NEVER hardcode secrets
// BAD
private const string ApiKey = "sk-1234567890";

// GOOD - User Secrets (development)
// dotnet user-secrets set "ApiKey" "sk-1234567890"
var apiKey = configuration["ApiKey"];

// GOOD - Environment variables
var apiKey = Environment.GetEnvironmentVariable("API_KEY");

// BEST - Azure Key Vault / AWS Secrets Manager
services.AddAzureKeyVault(
    new Uri($"https://{vaultName}.vault.azure.net/"),
    new DefaultAzureCredential()
);
```

### Password Hashing
```csharp
using Microsoft.AspNetCore.Identity;

public class PasswordService
{
    private readonly IPasswordHasher<User> _hasher;

    public PasswordService(IPasswordHasher<User> hasher)
    {
        _hasher = hasher;
    }

    public string HashPassword(User user, string password)
    {
        return _hasher.HashPassword(user, password);
    }

    public bool VerifyPassword(User user, string hash, string password)
    {
        var result = _hasher.VerifyHashedPassword(user, hash, password);
        return result != PasswordVerificationResult.Failed;
    }
}

// Or use BCrypt directly
using BCrypt.Net;

var hash = BCrypt.HashPassword(password, workFactor: 12);
var isValid = BCrypt.Verify(password, hash);
```

### Input Validation
```csharp
using System.ComponentModel.DataAnnotations;

public class CreateUserDto
{
    [Required]
    [StringLength(100, MinimumLength = 1)]
    public required string Name { get; init; }

    [Required]
    [EmailAddress]
    public required string Email { get; init; }

    [Range(0, 150)]
    public int? Age { get; init; }

    [RegularExpression(@"^\+?[1-9]\d{1,14}$")]
    public string? Phone { get; init; }
}

// Controller with validation
[HttpPost]
public async Task<IActionResult> CreateUser([FromBody] CreateUserDto dto)
{
    if (!ModelState.IsValid)
    {
        return BadRequest(ModelState);
    }
    // Process validated dto
}

// Custom validation attribute
public class NoScriptTagsAttribute : ValidationAttribute
{
    protected override ValidationResult? IsValid(object? value, ValidationContext context)
    {
        if (value is string str && str.Contains("<script", StringComparison.OrdinalIgnoreCase))
        {
            return new ValidationResult("Script tags not allowed");
        }
        return ValidationResult.Success;
    }
}
```

---

## Error Handling

### Custom Exceptions
```csharp
public abstract class AppException : Exception
{
    public string Code { get; }
    public int StatusCode { get; }

    protected AppException(string message, string code, int statusCode = 500)
        : base(message)
    {
        Code = code;
        StatusCode = statusCode;
    }
}

public class NotFoundException : AppException
{
    public NotFoundException(string resource, string id)
        : base($"{resource} with id {id} not found", "NOT_FOUND", 404) { }
}

public class ValidationException : AppException
{
    public IDictionary<string, string[]> Errors { get; }

    public ValidationException(IDictionary<string, string[]> errors)
        : base("Validation failed", "VALIDATION_ERROR", 400)
    {
        Errors = errors;
    }
}
```

### Global Exception Handler
```csharp
public class GlobalExceptionHandler : IExceptionHandler
{
    private readonly ILogger<GlobalExceptionHandler> _logger;

    public GlobalExceptionHandler(ILogger<GlobalExceptionHandler> logger)
    {
        _logger = logger;
    }

    public async ValueTask<bool> TryHandleAsync(
        HttpContext httpContext,
        Exception exception,
        CancellationToken cancellationToken)
    {
        var response = exception switch
        {
            NotFoundException ex => new ErrorResponse(ex.Code, ex.Message),
            ValidationException ex => new ErrorResponse(ex.Code, ex.Message, ex.Errors),
            _ => new ErrorResponse("INTERNAL_ERROR", "An unexpected error occurred")
        };

        var statusCode = exception switch
        {
            AppException ex => ex.StatusCode,
            _ => 500
        };

        if (statusCode == 500)
        {
            _logger.LogError(exception, "Unhandled exception");
        }

        httpContext.Response.StatusCode = statusCode;
        await httpContext.Response.WriteAsJsonAsync(response, cancellationToken);

        return true;
    }
}

// Registration
services.AddExceptionHandler<GlobalExceptionHandler>();
app.UseExceptionHandler();
```

### Result Pattern
```csharp
public readonly struct Result<T>
{
    public T? Value { get; }
    public string? Error { get; }
    public bool IsSuccess { get; }

    private Result(T value)
    {
        Value = value;
        Error = null;
        IsSuccess = true;
    }

    private Result(string error)
    {
        Value = default;
        Error = error;
        IsSuccess = false;
    }

    public static Result<T> Success(T value) => new(value);
    public static Result<T> Failure(string error) => new(error);

    public TResult Match<TResult>(
        Func<T, TResult> onSuccess,
        Func<string, TResult> onFailure)
        => IsSuccess ? onSuccess(Value!) : onFailure(Error!);
}

// Usage
public async Task<Result<User>> GetUserAsync(string id)
{
    var user = await _repository.FindByIdAsync(id);
    return user is null
        ? Result<User>.Failure("User not found")
        : Result<User>.Success(user);
}

var result = await GetUserAsync(id);
return result.Match(
    user => Ok(user),
    error => NotFound(error)
);
```

---

## Testing

### xUnit Patterns
```csharp
public class UserServiceTests
{
    private readonly Mock<IUserRepository> _mockRepo;
    private readonly UserService _service;

    public UserServiceTests()
    {
        _mockRepo = new Mock<IUserRepository>();
        _service = new UserService(_mockRepo.Object);
    }

    [Fact]
    public async Task GetUserAsync_WhenExists_ReturnsUser()
    {
        // Arrange
        var expected = new User { Id = "1", Name = "John" };
        _mockRepo.Setup(r => r.FindByIdAsync("1"))
                 .ReturnsAsync(expected);

        // Act
        var result = await _service.GetUserAsync("1");

        // Assert
        Assert.NotNull(result);
        Assert.Equal("John", result.Name);
    }

    [Theory]
    [InlineData("")]
    [InlineData(" ")]
    [InlineData(null)]
    public async Task GetUserAsync_WhenInvalidId_ThrowsValidation(string? id)
    {
        await Assert.ThrowsAsync<ValidationException>(
            () => _service.GetUserAsync(id!));
    }
}
```

---

## Code Smells

### Async Void
```csharp
// BAD - Can't catch exceptions
async void HandleClick()
{
    await DoSomethingAsync();
}

// GOOD
async Task HandleClickAsync()
{
    await DoSomethingAsync();
}
```

### String Concatenation in Loops
```csharp
// BAD - O(n²) complexity
var result = "";
foreach (var item in items)
{
    result += item.ToString();
}

// GOOD - O(n) complexity
var builder = new StringBuilder();
foreach (var item in items)
{
    builder.Append(item);
}
var result = builder.ToString();

// Or LINQ
var result = string.Join("", items);
```

### God Classes
```csharp
// BAD
public class UserManager
{
    public void CreateUser() { }
    public void SendEmail() { }
    public void GenerateReport() { }
    public void ProcessPayment() { }
}

// GOOD - Single Responsibility
public class UserService { }
public class EmailService { }
public class ReportService { }
public class PaymentService { }
```
