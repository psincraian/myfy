---
name: user-module
description: myfy UserModule for authentication with email/password, OAuth, sessions, and JWT. Use when working with UserModule, BaseUser, OAuth providers, login, registration, password reset, email verification, or user authentication.
---

# UserModule - User Authentication

UserModule provides complete user authentication with email/password, OAuth, sessions, and JWT tokens.

## Quick Start

```python
from myfy.core import Application
from myfy.data import DataModule
from myfy.web import WebModule
from myfy.web.auth import AuthModule
from myfy.user import UserModule, BaseUser
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String

# Extend BaseUser with custom fields
class User(BaseUser):
    __tablename__ = "users"
    phone: Mapped[str | None] = mapped_column(String(20))

# Create module
user_module = UserModule(
    user_model=User,
    oauth_providers=["google", "github"],
    auto_create_tables=True,
)

# Set up application
app = Application()
app.add_module(DataModule())
app.add_module(WebModule())
app.add_module(AuthModule(
    authenticated_provider=user_module.get_authenticated_provider(),
))
app.add_module(user_module)
```

## Configuration

Environment variables use the `MYFY_USER_` prefix:

| Variable | Default | Description |
|----------|---------|-------------|
| `MYFY_USER_SECRET_KEY` | (auto-generated) | Secret for JWT/sessions |
| `MYFY_USER_SESSION_LIFETIME` | `604800` | Session duration (7 days, in seconds) |
| `MYFY_USER_JWT_ALGORITHM` | `HS256` | JWT signing algorithm |
| `MYFY_USER_JWT_ACCESS_TOKEN_LIFETIME` | `3600` | JWT access token lifetime |
| `MYFY_USER_PASSWORD_MIN_LENGTH` | `8` | Minimum password length |
| `MYFY_USER_REQUIRE_EMAIL_VERIFICATION` | `True` | Require email verification |

### OAuth Configuration

```bash
# Google OAuth
MYFY_USER_OAUTH_GOOGLE_CLIENT_ID=your-client-id
MYFY_USER_OAUTH_GOOGLE_CLIENT_SECRET=your-secret

# GitHub OAuth
MYFY_USER_OAUTH_GITHUB_CLIENT_ID=your-client-id
MYFY_USER_OAUTH_GITHUB_CLIENT_SECRET=your-secret
```

## Module Options

```python
UserModule(
    user_model=User,              # Custom user model (must extend BaseUser)
    oauth_providers=["google"],   # OAuth providers to enable
    auto_create_tables=True,      # Create tables on start
    enable_routes=True,           # Register auth routes
    enable_templates=True,        # Provide Jinja2 templates
)
```

## Custom User Model

```python
from myfy.user import BaseUser
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import String, Boolean

class User(BaseUser):
    __tablename__ = "users"

    # Custom fields
    phone: Mapped[str | None] = mapped_column(String(20))
    is_admin: Mapped[bool] = mapped_column(Boolean, default=False)
    company_id: Mapped[int | None] = mapped_column(ForeignKey("companies.id"))

    # Relationships
    company: Mapped["Company"] = relationship(back_populates="users")
```

BaseUser provides:
- `id`: Primary key
- `email`: Unique email address
- `password_hash`: Hashed password
- `is_active`: Account active status
- `is_verified`: Email verified status
- `created_at`, `updated_at`: Timestamps

## Protected Routes

```python
from myfy.web import route, Authenticated

@route.get("/profile")
async def profile(user: User) -> dict:
    # user is injected if authenticated
    # Returns 401 if not authenticated
    return {"email": user.email, "name": user.name}

@route.get("/admin")
async def admin_dashboard(user: User) -> dict:
    if not user.is_admin:
        abort(403, "Admin access required")
    return {"message": "Welcome, admin"}
```

## Auth Routes

UserModule registers these routes by default:

| Route | Method | Description |
|-------|--------|-------------|
| `/auth/login` | GET/POST | Login page and handler |
| `/auth/logout` | POST | Logout (clear session) |
| `/auth/register` | GET/POST | Registration page and handler |
| `/auth/forgot-password` | GET/POST | Password reset request |
| `/auth/reset-password` | GET/POST | Password reset form |
| `/auth/verify-email` | GET | Email verification link |
| `/auth/google` | GET | Google OAuth start |
| `/auth/google/callback` | GET | Google OAuth callback |
| `/auth/github` | GET | GitHub OAuth start |
| `/auth/github/callback` | GET | GitHub OAuth callback |

## Using UserService

```python
from myfy.user import UserService

@route.post("/users")
async def create_user(body: CreateUserRequest, user_service: UserService) -> dict:
    user = await user_service.create(
        email=body.email,
        password=body.password,
    )
    return {"id": user.id}

@route.get("/users/{user_id}")
async def get_user(user_id: int, user_service: UserService) -> dict:
    user = await user_service.get_by_id(user_id)
    if not user:
        abort(404, "User not found")
    return {"email": user.email}
```

## Session vs JWT

### Session-Based (Web)

Default for web routes. Session ID stored in cookie.

```python
@route.get("/dashboard")
async def dashboard(user: User) -> str:
    # Session cookie auto-validated
    return render_template("dashboard.html", user=user)
```

### JWT-Based (API)

For API clients, use JWT tokens.

```python
from myfy.user import JWTService

@route.post("/api/login")
async def api_login(body: LoginRequest, jwt_service: JWTService, user_service: UserService) -> dict:
    user = await user_service.authenticate(body.email, body.password)
    if not user:
        abort(401, "Invalid credentials")
    token = jwt_service.create_token(user)
    return {"token": token}
```

Client sends token in header:

```
Authorization: Bearer <token>
```

## OAuth Integration

### Google OAuth

```python
user_module = UserModule(
    user_model=User,
    oauth_providers=["google"],
)
```

Login link:

```html
<a href="/auth/google" class="btn">Login with Google</a>
```

### GitHub OAuth

```python
user_module = UserModule(
    user_model=User,
    oauth_providers=["github"],
)
```

Login link:

```html
<a href="/auth/github" class="btn">Login with GitHub</a>
```

## Email Verification

Enable verification:

```bash
MYFY_USER_REQUIRE_EMAIL_VERIFICATION=true
```

Users must verify email before full access. Verification link sent on registration.

## Password Reset

1. User requests reset at `/auth/forgot-password`
2. Reset email sent with secure token
3. User clicks link to `/auth/reset-password?token=...`
4. User enters new password

## Custom Templates

Override default templates by placing files in your templates directory:

```
frontend/templates/auth/
  login.html
  register.html
  forgot-password.html
  reset-password.html
  verify-email.html
```

## Best Practices

1. **Set a strong SECRET_KEY** - Use a long random string
2. **Enable email verification** - For production apps
3. **Use OAuth where possible** - Reduces password management burden
4. **Extend BaseUser** - Don't modify it directly
5. **Use sessions for web, JWT for API** - Different use cases
6. **Hash passwords** - UserService handles this automatically
7. **Rate limit auth routes** - Prevent brute force attacks
