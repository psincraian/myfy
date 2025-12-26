# Myfy Documentation Review Findings

**Documentation Reviewed:** https://docs.myfy.dev/reference/ (via local `docs/reference.md`)
**Version Tested:** myfy 0.1.2a77 (latest alpha)
**Date:** 2025-12-26

---

## Executive Summary

| Section | Clarity | Code Works | Issues Found |
|---------|---------|------------|--------------|
| Quick Start | ✅ Clear | ✅ Works | None |
| Dependency Injection | ✅ Clear | ✅ Works | None |
| Web Routes | ⚠️ Mostly Clear | ❌ Partial | `status_code` parameter incorrect |
| Error Handling | ⚠️ Mostly Clear | ✅ Works | Attribute access differs |
| Configuration | ✅ Clear | ✅ Works | None |
| Modules | ✅ Clear | ✅ Works | None |
| Database | ✅ Clear | ✅ Works | None |
| Frontend | ✅ Clear | ✅ Works | None |
| CLI Commands | ✅ Clear | ✅ Works | None |
| Middleware | ❌ Incorrect | ❌ Fails | Major API mismatch |
| Testing | ⚠️ Mostly Clear | ⚠️ Partial | API reference incorrect |
| Common Patterns | ✅ Clear | ✅ Works | None |

---

## Detailed Findings

### 1. Quick Start

**Clarity:** ✅ Clear and concise
**Code Works:** ✅ Yes

The minimal application example works correctly:

```python
from myfy.core import Application
from myfy.web import route, WebModule

@route.get("/")
async def home() -> dict:
    return {"message": "Hello World"}

app = Application(auto_discover=False)
app.add_module(WebModule())
```

Running `myfy run` starts the server successfully.

**No issues found.**

---

### 2. Dependency Injection

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

All scopes work correctly:
- `SINGLETON` - ✅
- `REQUEST` - ✅
- `TASK` - ✅

The `@provider` decorator and scope imports work as documented.

**No issues found.**

---

### 3. Web Routes

**Clarity:** ⚠️ Mostly clear
**Code Works:** ❌ Partial - `status_code` parameter fails

#### Issue 1: `status_code` Parameter Does Not Exist

**Documentation shows:**
```python
@route.post("/users", status_code=201)
async def create_user(body: CreateUserDTO) -> User:
    return await service.create_user(body)

@route.delete("/users/{id}", status_code=204)
async def delete_user(id: int) -> None:
    await service.delete_user(id)
```

**Error:**
```
TypeError: Router.post() got an unexpected keyword argument 'status_code'
```

**Actual API:**
```python
# Route decorator signature:
(path: str, name: str | None = None) -> Callable
```

**Solution Options:**
1. Remove `status_code` from docs OR
2. Implement `status_code` in route decorators OR
3. Document that returning `None` automatically returns 204, and for other codes use `Response(status_code=XXX)`

**Note:** The framework automatically returns 204 when a route returns `None`, which covers the DELETE case. For POST with 201, users need to use a custom Response.

#### Other Features Work
- HTTP methods (GET, POST, PUT, PATCH, DELETE) ✅
- Path parameters ✅
- Query parameters with defaults ✅
- Query validation with `Query()` ✅
- Request body with Pydantic ✅

---

### 4. Error Handling

**Clarity:** ⚠️ Mostly clear
**Code Works:** ✅ Yes (with different API)

#### Issue: Documentation Shows Non-Existent Attribute

**Documentation implies accessing `.detail`:**
The JSON response shows `"detail": "User not found"` but this is from `to_problem_detail()`, not a direct attribute.

**Actual API:**
```python
from myfy.web import errors

try:
    raise errors.NotFound("User not found", user_id=123)
except errors.NotFound as e:
    print(str(e))              # "User not found"
    print(e.status_code)       # 404
    print(e.extra)             # {'user_id': 123}
    print(e.to_problem_detail()) # Full RFC 7807 dict
```

**Available attributes:**
- `str(e)` or `e.args[0]` - The message
- `e.status_code` - HTTP status code
- `e.error_type` - Error type string
- `e.extra` - Additional kwargs passed to constructor
- `e.to_problem_detail()` - Full RFC 7807 dictionary

All error classes work correctly:
- `errors.BadRequest` (400) ✅
- `errors.Unauthorized` (401) ✅
- `errors.Forbidden` (403) ✅
- `errors.NotFound` (404) ✅
- `errors.Conflict` (409) ✅
- `errors.UnprocessableEntity` (422) ✅
- `errors.RateLimit` (429) ✅
- `errors.ServiceUnavailable` (503) ✅

Custom errors work as documented.

---

### 5. Configuration

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

`BaseSettings` class and environment file loading work correctly.

**No issues found.**

---

### 6. Modules

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

Custom module creation with `BaseModule` works as documented:
- `__init__` with name
- `configure(container)` method
- `start()` / `stop()` lifecycle methods

**No issues found.**

---

### 7. Database (myfy-data)

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

The `DataModule` with SQLAlchemy integration works:
- `Base` for model definitions
- `auto_create_tables=True` option
- `metadata` parameter

Environment variables work correctly:
- `MYFY_DATA_DATABASE_URL`
- `MYFY_DATA_POOL_SIZE`
- `MYFY_DATA_MAX_OVERFLOW`

**No issues found.**

---

### 8. Frontend (myfy-frontend)

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

`myfy frontend init` creates the expected structure:
- `frontend/templates/` with base.html, home.html
- `frontend/css/`
- `frontend/js/`
- `package.json`
- `vite.config.js`

`render_template` function works with correct signature:
```python
render_template(template_name: str, request: Request | None = None,
                templates: Jinja2Templates | None = None, **context)
```

**No issues found.**

---

### 9. CLI Commands

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

All CLI commands work:
- `myfy run` ✅
- `myfy routes` ✅
- `myfy modules` ✅
- `myfy doctor` ✅
- `myfy frontend init` ✅

**No issues found.**

---

### 10. Middleware

**Clarity:** ❌ Incorrect - Major API mismatch
**Code Works:** ❌ No - Code fails completely

#### Critical Issue: `middleware` Parameter Does Not Exist

**Documentation shows:**
```python
from myfy.web import WebModule
from starlette.middleware import Middleware
from starlette.middleware.cors import CORSMiddleware

app.add_module(WebModule(
    middleware=[
        Middleware(
            CORSMiddleware,
            allow_origins=["*"],
            allow_methods=["*"],
            allow_headers=["*"]
        )
    ]
))
```

**Error:**
```
TypeError: WebModule.__init__() got an unexpected keyword argument 'middleware'
```

**Actual API:**
```python
# WebModule.__init__ signature:
(self, router: Router | None = None)
```

**Actual CORS Configuration:**
CORS is configured via `WebSettings` environment variables:

```bash
# .env
MYFY_WEB_CORS_ENABLED=true
MYFY_WEB_CORS_ALLOWED_ORIGINS=["https://example.com", "http://localhost:3000"]
MYFY_WEB_CORS_ALLOW_CREDENTIALS=true
MYFY_WEB_CORS_ALLOWED_METHODS=["GET", "POST", "PUT", "DELETE", "PATCH"]
MYFY_WEB_CORS_ALLOWED_HEADERS=["Content-Type", "Authorization"]
```

**Solution:**
The entire Middleware section needs to be rewritten to show the correct approach using environment variables.

---

### 11. Testing

**Clarity:** ⚠️ Mostly clear
**Code Works:** ⚠️ Partial - needs corrections

#### Issue 1: `app.web_module` Does Not Exist

**Documentation shows:**
```python
from starlette.testclient import TestClient

def test_get_users(app):
    client = TestClient(app.web_module.get_asgi_app(app.container))
    response = client.get("/users")
    assert response.status_code == 200
```

**Error:** `app.web_module` attribute does not exist.

**Correct approach:**
```python
from starlette.testclient import TestClient
from myfy.web import WebModule

def test_get_users(app):
    app.initialize()  # Must call initialize first!
    web_mod = app.get_module(WebModule)
    client = TestClient(web_mod.get_asgi_app(app.container))
    response = client.get("/users")
    assert response.status_code == 200
```

#### Issue 2: Missing `app.initialize()`

The test example doesn't show that `app.initialize()` must be called before getting the ASGI app. Without it, the container won't be properly set up.

#### Additional Note

Need to install `httpx` package for `starlette.testclient`:
```bash
pip install httpx
```

---

### 12. Common Patterns

**Clarity:** ✅ Clear
**Code Works:** ✅ Yes

All patterns work correctly:
- Repository Pattern ✅
- Service Layer ✅
- Background Tasks ✅

**No issues found.**

---

## Summary of Required Documentation Fixes

### Critical Fixes (Code Does Not Work)

1. **Middleware Section (Line 529-545)**: Complete rewrite needed
   - Remove `middleware` parameter from `WebModule()`
   - Document CORS configuration via environment variables

2. **Web Routes - Status Codes (Lines 162-169)**: Remove or fix
   - `status_code` parameter doesn't exist in route decorators
   - Either implement the feature or document the actual approach

3. **Testing Section - HTTP Tests (Lines 569-577)**: Fix API reference
   - Change `app.web_module` to `app.get_module(WebModule)`
   - Add `app.initialize()` call before getting ASGI app

### Minor Fixes (Clarity Improvements)

4. **Error Handling Section**: Clarify attribute access
   - Document that message is accessed via `str(e)`, not `.detail`
   - Document `to_problem_detail()` for RFC 7807 response

---

## Tested Environment

- Python: 3.12
- myfy: 0.1.2a77
- myfy-core: 0.1.2a77
- myfy-web: 0.1.2a77
- myfy-data: 0.1.2a77
- myfy-frontend: 0.1.2a77
- myfy-cli: 0.1.2a77
