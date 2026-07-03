---
name: c-coding-standards
description: "C coding standards based on ISO C (C11/C17/C23), CERT C, and MISRA-style safety practices. Use when writing, reviewing, or refactoring C code to enforce memory safety, defined behavior, portable interfaces, resource cleanup, and maintainable low-level design."
---

# C Coding Standards

Comprehensive coding standards for modern C (C11/C17/C23) derived from ISO C, CERT C, and MISRA-style defensive programming practices. Enforce explicit ownership, bounds-aware interfaces, predictable error handling, portability, and clarity.

## When to Use

- Writing new C code in libraries, services, CLI tools, embedded systems, or low-level components
- Reviewing or refactoring existing C code
- Designing C APIs, headers, ownership contracts, and error-handling conventions
- Hardening code against memory leaks, buffer overflows, integer overflow, undefined behavior, and portability bugs
- Choosing between C language mechanisms such as macros vs `static inline`, `enum` vs `#define`, pointer ownership vs borrowed access, or return codes vs output parameters

### When NOT to Use

- C++ projects where C++ Core Guidelines are the correct baseline
- Projects with a stricter mandatory standard such as MISRA C, AUTOSAR C, or a vendor/kernel style guide that overrides these rules
- Hardware-specific bare-metal code where deliberate implementation-defined behavior is documented and required

## Cross-Cutting Principles

These themes recur across the entire guideline set:

1. **Make ownership explicit**: Every allocated resource has one clear owner and one clear release path.
2. **Pass sizes with buffers**: A pointer to an array is incomplete without its element count or byte length.
3. **Initialize everything**: Objects start in a known valid state and are destroyed through a matching cleanup function.
4. **Prefer immutability**: Use `const` for input data and unchanged objects; mutability is a visible choice.
5. **Avoid undefined behavior**: Treat signed overflow, invalid pointers, out-of-bounds access, strict-aliasing violations, and uninitialized reads as design bugs.
6. **Keep interfaces boring and explicit**: C lacks overloads, constructors, destructors, and exceptions; encode intent in names, types, return values, and documentation.
7. **Use the compiler and tools**: Enable warnings, static analysis, sanitizers, and formatters in normal development.

## Philosophy & Interfaces (P.*, I.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **P.1** | Express intent directly in names, types, and contracts |
| **P.2** | Avoid hidden ownership and hidden mutation |
| **P.3** | Prefer simple control flow and explicit cleanup |
| **P.4** | Make invalid states hard to create and easy to detect |
| **I.1** | Make APIs self-contained and explicit |
| **I.2** | Document ownership, nullability, sizes, and lifetime |
| **I.3** | Return status consistently; do not mix unrelated error conventions |
| **I.4** | Use project-prefixed public symbols |
| **I.5** | Keep argument lists short; group related data in structs |
| **I.6** | Avoid non-const global state |

### DO

```c
/* I.2: Pointer, size, ownership, and status are explicit. */
enum parse_status {
    parse_ok = 0,
    parse_invalid_input,
    parse_no_memory
};

struct parse_result {
    const char *token;  /* borrowed from input */
    size_t token_len;
};

enum parse_status parse_token(const char *input,
                              size_t input_len,
                              struct parse_result *out);
```

### DON'T

```c
/* Weak interface: no length, unclear ownership, unclear errors. */
char *parse(char *input);

/* Hidden mutable global state. */
int g_parse_mode;
```

## Functions (F.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **F.1** | Package one logical operation per function |
| **F.2** | Keep functions short enough to audit manually |
| **F.3** | Name functions by effect: `load_config`, `buffer_free`, `parse_u32` |
| **F.4** | Mark internal functions `static` |
| **F.5** | Use `const` pointer parameters for read-only input |
| **F.6** | Put output parameters last and document when they are written |
| **F.7** | Avoid function-like macros; prefer functions or `static inline` |
| **F.8** | Do not return pointers to local objects or invalidated storage |
| **F.9** | Avoid C variadics unless implementing a printf-like API with format checking |

### Parameter Passing

```c
/* Input by value for small scalars. */
void sensor_set_rate(unsigned hz);

/* Read-only input by const pointer plus length. */
bool digest_update(struct digest *ctx, const uint8_t *data, size_t len);

/* Output parameter last; written only on success. */
bool parse_u32(const char *text, uint32_t *out_value);
```

### Internal Helpers

```c
/* F.4: Internal linkage keeps helper names out of the global symbol table. */
static bool is_ascii_digit(unsigned char ch)
{
    return ch >= '0' && ch <= '9';
}
```

### Anti-Patterns

- Returning pointers to stack variables or freed storage
- Hiding mutation behind `const` casts
- Mutating input buffers unless the function name and contract make it explicit
- Long functions with mixed parsing, allocation, I/O, and logging
- Public helper functions that should be `static`
- Varargs without format attributes or strict validation

## Types, Structs & Enums (T.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **T.1** | Use domain-specific structs instead of primitive clusters |
| **T.2** | Prefer `enum` for named states and results |
| **T.3** | Use fixed-width integer types only when width matters |
| **T.4** | Use `size_t` for object sizes and element counts |
| **T.5** | Keep struct invariants behind functions when invariants exist |
| **T.6** | Use opaque structs for public types with private representation |
| **T.7** | Do not use reserved identifiers |
| **T.8** | Avoid bit-fields in portable interfaces |

### Opaque Types

```c
/* widget.h */
#ifndef ACME_WIDGET_H
#define ACME_WIDGET_H

#include <stddef.h>
#include <stdbool.h>

struct acme_widget;

struct acme_widget *acme_widget_create(size_t capacity);
void acme_widget_destroy(struct acme_widget *widget);
bool acme_widget_push(struct acme_widget *widget, int value);

#endif
```

```c
/* widget.c */
#include "widget.h"

#include <stdlib.h>

struct acme_widget {
    int *items;
    size_t len;
    size_t cap;
};
```

### Enums

```c
enum log_level {
    log_level_debug = 0,
    log_level_info,
    log_level_warning,
    log_level_error
};
```

### Anti-Patterns

- Public structs whose fields must satisfy hidden invariants
- `typedef` names that obscure pointer ownership, such as `typedef char *string;`
- Project-defined identifiers beginning with `_` or containing `__`
- Project-defined `_t` suffixes in POSIX-facing code
- Assuming enum size, struct padding, bit-field layout, or endianness

## Pointers, Arrays & Strings (PA.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **PA.1** | Treat every pointer as nullable unless the contract says otherwise |
| **PA.2** | Pass array lengths with array pointers |
| **PA.3** | Use `sizeof *ptr` in allocations and copies |
| **PA.4** | Check allocation-size multiplication for overflow |
| **PA.5** | Do pointer arithmetic only within one array object |
| **PA.6** | Use `memmove` for overlapping ranges |
| **PA.7** | Prefer length-aware string handling |
| **PA.8** | Do not use obsolete unsafe functions |

### Bounds-Aware Buffers

```c
bool bytes_copy(uint8_t *dst, size_t dst_len,
                const uint8_t *src, size_t src_len)
{
    if (dst == NULL || src == NULL) {
        return false;
    }
    if (src_len > dst_len) {
        return false;
    }

    memcpy(dst, src, src_len);
    return true;
}
```

### Overflow-Safe Allocation

```c
int *int_array_create(size_t count)
{
    if (count > SIZE_MAX / sizeof(int)) {
        return NULL;
    }

    int *items = calloc(count, sizeof *items);
    return items;
}
```

### Strings

```c
bool make_label(char *dst, size_t dst_len, const char *name)
{
    if (dst == NULL || name == NULL || dst_len == 0) {
        return false;
    }

    int written = snprintf(dst, dst_len, "sensor:%s", name);
    return written >= 0 && (size_t)written < dst_len;
}
```

### Anti-Patterns

- `gets`, `strcpy`, `strcat`, `sprintf`, and unbounded `scanf("%s", ...)`
- `strncpy` as a general safe string-copy primitive; it may omit the terminator
- Allocation written as `malloc(count * sizeof(type))` without overflow checking
- `sizeof(pointer)` when the intent is the pointed-to object size
- Pointer arithmetic across unrelated objects
- Treating text strings and binary buffers as interchangeable

## Resource Management (R.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **R.1** | Every resource acquisition has a matching release function |
| **R.2** | Use one cleanup path for functions that acquire multiple resources |
| **R.3** | Initialize handles and pointers before the first possible cleanup |
| **R.4** | Destruction functions accept `NULL` unless there is a strong reason not to |
| **R.5** | Ownership transfer is explicit in function names or comments |
| **R.6** | Do not leak resources on partial failure |
| **R.7** | Pair allocation families correctly: `malloc/free`, `fopen/fclose`, `open/close` |

### Cleanup Pattern

```c
enum load_status load_file(const char *path, struct buffer *out)
{
    enum load_status status = load_ok;
    FILE *file = NULL;
    uint8_t *data = NULL;

    if (path == NULL || out == NULL) {
        return load_invalid_argument;
    }

    file = fopen(path, "rb");
    if (file == NULL) {
        return load_io_error;
    }

    data = malloc(4096);
    if (data == NULL) {
        status = load_no_memory;
        goto cleanup;
    }

    out->data = data;
    out->len = 0;
    data = NULL;  /* ownership moved to out */

cleanup:
    free(data);
    if (file != NULL) {
        fclose(file);
    }
    return status;
}
```

### Destruction Functions

```c
void buffer_destroy(struct buffer *buffer)
{
    if (buffer == NULL) {
        return;
    }

    free(buffer->data);
    buffer->data = NULL;
    buffer->len = 0;
}
```

### Anti-Patterns

- Multiple early returns after acquiring resources
- Cleanup labels that assume uninitialized pointers are valid
- Freeing through aliases after ownership has moved
- Double-free by not nulling or invalidating moved resources when appropriate
- Library code calling `exit` instead of returning an error

## Expressions & Statements (ES.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **ES.1** | Keep scopes small |
| **ES.2** | Always initialize variables |
| **ES.3** | Use braces for every control statement body |
| **ES.4** | Avoid assignments inside conditions unless the idiom is local and obvious |
| **ES.5** | Avoid magic numbers; use named constants |
| **ES.6** | Avoid signed integer overflow and lossy conversions |
| **ES.7** | Avoid undefined and implementation-defined behavior unless documented |
| **ES.8** | Do not cast away `const` |
| **ES.9** | Use casts sparingly and locally |
| **ES.10** | Prefer readable control flow over clever expressions |

### Initialization

```c
enum { max_retries = 3 };

struct config {
    unsigned timeout_ms;
    unsigned retries;
    bool verbose;
};

struct config cfg = {
    .timeout_ms = 30000,
    .retries = max_retries,
    .verbose = false
};
```

### Integer Conversion

```c
bool size_to_u32(size_t value, uint32_t *out)
{
    if (out == NULL || value > UINT32_MAX) {
        return false;
    }

    *out = (uint32_t)value;
    return true;
}
```

### Anti-Patterns

- Uninitialized reads
- Signed overflow
- Mixing signed and unsigned arithmetic casually
- Fallthrough in `switch` without an explicit marker comment
- Deeply nested conditionals that hide the main success path
- Type punning through incompatible pointer types
- Assuming `char` is signed or unsigned

## Error Handling (E.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **E.1** | Define the module error strategy before implementing APIs |
| **E.2** | Return errors; do not terminate from library code |
| **E.3** | Keep return-value conventions consistent in a module |
| **E.4** | Preserve diagnostic detail at module boundaries |
| **E.5** | Set output parameters only on success unless documented otherwise |
| **E.6** | Check every fallible call |
| **E.7** | Use `errno` only when the API contract says so |
| **E.8** | Cleanup must not hide the original failure |

### Typed Return Codes

```c
enum config_error {
    config_ok = 0,
    config_invalid_argument,
    config_io_error,
    config_parse_error,
    config_no_memory
};

enum config_error config_load(const char *path, struct config *out);
const char *config_error_string(enum config_error error);
```

### Parsing

```c
bool parse_port(const char *text, uint16_t *out_port)
{
    char *end = NULL;
    unsigned long value;

    if (text == NULL || out_port == NULL || text[0] == '\0') {
        return false;
    }

    errno = 0;
    value = strtoul(text, &end, 10);
    if (errno != 0 || *end != '\0' || value > UINT16_MAX) {
        return false;
    }

    *out_port = (uint16_t)value;
    return true;
}
```

### Anti-Patterns

- Ignoring return values from allocation, I/O, locks, and parsing
- `atoi`, `atol`, and `atof` for validated input
- APIs that sometimes return `NULL`, sometimes set `errno`, and sometimes log and continue
- Swallowing cleanup failures that matter to the caller
- Writing partially valid output structures after failure

## Constants & Immutability (Con.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **Con.1** | Make input data `const` by default |
| **Con.2** | Use `static const` for internal read-only objects |
| **Con.3** | Use `enum` constants for integer compile-time constants |
| **Con.4** | Do not cast away `const` |
| **Con.5** | Keep mutable global state out of interfaces |

```c
enum { max_packet_size = 1500 };

static const char default_host[] = "localhost";

void packet_dump(const struct packet *packet);
```

### Notes

- In C, `const` means read-only through that expression; it does not imply deep immutability.
- A block-scope `const int` is not a portable integer constant expression for all C uses. Use `enum` for compile-time integer constants.
- `const` does not make a global object thread-safe if other aliases can mutate it.

## Concurrency & Atomics (CP.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **CP.1** | Avoid data races |
| **CP.2** | Minimize shared writable state |
| **CP.3** | Protect data with the mutex that owns it |
| **CP.4** | Use condition variables in loops with predicates |
| **CP.5** | Do not use `volatile` for synchronization |
| **CP.6** | Use atomics only for simple, well-understood shared state |
| **CP.7** | Establish a documented lock ordering for multiple locks |
| **CP.8** | Do not call unknown callbacks while holding a lock |

### Locking Pattern

```c
bool queue_push(struct queue *queue, int value)
{
    bool ok = false;

    if (queue == NULL) {
        return false;
    }

    mtx_lock(&queue->mutex);
    ok = queue_push_locked(queue, value);
    cnd_signal(&queue->not_empty);
    mtx_unlock(&queue->mutex);

    return ok;
}
```

### Anti-Patterns

- Using `volatile` as a substitute for mutexes or atomics
- Reading shared non-atomic data without synchronization
- Holding locks while calling user-provided callbacks
- Lock order that depends on runtime accidents rather than documented rules
- Lock-free code without a clear memory-ordering argument and tests

## Standard Library & Portability (SL.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **SL.1** | Use the standard library where it is safe and appropriate |
| **SL.2** | Know which APIs are ISO C, POSIX, compiler-specific, or platform-specific |
| **SL.3** | Check return values from standard-library functions |
| **SL.4** | Prefer `snprintf`, `fgets`, `strtol`, `strtoul`, and `memcpy`/`memmove` with checked sizes |
| **SL.5** | Do not use removed, obsolete, or inherently unsafe functions |
| **SL.6** | Avoid locale-dependent behavior unless it is intentional |
| **SL.7** | Use `memcpy` for representation copies, not incompatible pointer casts |

### Safer Standard Library Choices

```c
/* Good: validated numeric conversion. */
bool parse_i32(const char *text, int32_t *out);

/* Good: bounded formatting with truncation detection. */
int n = snprintf(buffer, buffer_len, "%s:%u", host, port);
if (n < 0 || (size_t)n >= buffer_len) {
    return false;
}
```

### Anti-Patterns

- `gets`, `sprintf`, `vsprintf`, unbounded `scanf`, `atoi`
- Assuming `fread`/`fwrite` transferred everything requested
- Using POSIX functions in portable ISO C code without an abstraction or feature guard
- Assuming endianness, alignment, struct packing, or two's-complement details without a contract
- Security-sensitive randomness from `rand`

## Preprocessor (PP.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **PP.1** | Use macros mainly for include guards, feature flags, and compile-time constants that must be preprocessor-visible |
| **PP.2** | Prefer `enum`, `static const`, or `static inline` over macros |
| **PP.3** | Prefix public macros with the project or module name |
| **PP.4** | Parenthesize macro parameters and full macro expansions |
| **PP.5** | Never pass side-effect expressions to macros that may evaluate arguments more than once |
| **PP.6** | Keep conditional compilation shallow and localized |
| **PP.7** | Do not hide control flow in macros |

### Prefer Inline Functions

```c
static inline int clamp_int(int value, int low, int high)
{
    if (value < low) {
        return low;
    }
    if (value > high) {
        return high;
    }
    return value;
}
```

### Macro Hygiene

```c
#define ACME_ARRAY_LEN(a) (sizeof(a) / sizeof((a)[0]))
```

Use this only with actual arrays, not pointers.

### Anti-Patterns

- Function-like macros with hidden side effects
- Macros that expand to partial statements or unbalanced braces
- Public macros without a project prefix
- Compile-time feature matrices that make the code impossible to audit

## Source Files & Naming (SF.*, NL.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **SF.1** | Use `.c` for implementation files and `.h` for interfaces |
| **SF.2** | Headers must be self-contained |
| **SF.3** | Every header has an include guard |
| **SF.4** | Headers include what they use |
| **SF.5** | Do not define external-linkage objects in headers |
| **SF.6** | Use `static` for internal functions and objects |
| **NL.1** | Use one naming style consistently |
| **NL.2** | Use lower_snake_case for functions, variables, fields, and enum values |
| **NL.3** | Use ALL_CAPS only for macros |
| **NL.4** | Prefix public symbols with the project or module name |
| **NL.5** | Avoid Hungarian notation and type-encoding prefixes |

### Header Guard

```c
#ifndef ACME_NET_SOCKET_H
#define ACME_NET_SOCKET_H

#include <stdbool.h>
#include <stddef.h>
#include <stdint.h>

struct acme_socket;

struct acme_socket *acme_socket_open(const char *host, uint16_t port);
void acme_socket_close(struct acme_socket *socket);
bool acme_socket_send(struct acme_socket *socket,
                      const uint8_t *data,
                      size_t len);

#endif
```

### Anti-Patterns

- Headers that require another header to be included first
- Non-`static` function definitions in headers
- Defining global variables in headers
- Names beginning with `_`, names containing `__`, or names colliding with standard-library identifiers
- ALL_CAPS names for ordinary constants, enum values, or variables

## Performance (Per.*)

### Key Rules

| Rule | Summary |
|------|---------|
| **Per.1** | Do not optimize without measurement |
| **Per.2** | Preserve defined behavior while optimizing |
| **Per.3** | Design data layout intentionally |
| **Per.4** | Prefer simple contiguous storage when it matches access patterns |
| **Per.5** | Avoid needless allocation in hot paths |
| **Per.6** | Keep cache locality, alignment, and branch behavior in mind after profiling |
| **Per.7** | Do not make performance claims without benchmark evidence |

### Guidelines

```c
/* Good: contiguous storage and explicit length. */
struct point_array {
    struct point *items;
    size_t len;
    size_t cap;
};
```

### Anti-Patterns

- Clever bit tricks that rely on undefined behavior
- Pointer-heavy layouts where arrays would be simpler and faster
- Global caches with unclear invalidation or synchronization
- Manual micro-optimizations that defeat compiler optimization or readability

## Tooling Baseline

Before trusting C changes, prefer project-appropriate versions of:

- Compiler warnings: `-Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wstrict-prototypes -Wmissing-prototypes`
- Sanitizers in test builds: AddressSanitizer, UndefinedBehaviorSanitizer, LeakSanitizer, ThreadSanitizer when applicable
- Static analysis: clang-tidy, cppcheck, scan-build, CodeQL, or project-required tools
- Formatting: clang-format or the local style formatter
- Tests that exercise error paths, allocation failures where practical, boundary lengths, and invalid inputs

## Quick Reference Checklist

Before marking C work complete:

- [ ] Public APIs document ownership, nullability, sizes, lifetime, and error convention
- [ ] Array and buffer pointers are passed with explicit lengths
- [ ] All variables are initialized before use
- [ ] Read-only inputs use `const`
- [ ] Allocations use `sizeof *ptr` and check multiplication overflow
- [ ] Every resource has one clear cleanup path
- [ ] Output parameters are written only on success unless documented otherwise
- [ ] Fallible calls have checked return values
- [ ] No `gets`, `strcpy`, `strcat`, `sprintf`, unbounded `scanf`, or `atoi`
- [ ] No signed overflow, out-of-bounds access, invalid pointer use, or strict-aliasing violation
- [ ] Casts are rare, local, and justified; no casts remove `const`
- [ ] Public symbols and macros have project/module prefixes
- [ ] Headers are self-contained and guarded
- [ ] Internal functions and objects are `static`
- [ ] No mutable global state without synchronization and a clear owner
- [ ] No `volatile` used for thread synchronization
- [ ] `switch` fallthrough is explicit
- [ ] Platform-specific code is isolated behind feature checks or adapters
- [ ] Warning, sanitizer, static-analysis, formatter, and test expectations have been run or documented
