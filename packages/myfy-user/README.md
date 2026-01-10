# myfy-user

User management module for the myfy framework.

## Features

- **Email/Password Authentication** - Secure password hashing with argon2/bcrypt
- **OAuth Authentication** - Built-in support for Google and GitHub
- **Session Management** - Cookie-based sessions for web applications
- **JWT Tokens** - API authentication with access/refresh tokens
- **Email Verification** - Token-based email verification flow
- **Password Reset** - Secure password reset via email
- **User Profiles** - Customizable user profiles
- **CLI Tools** - Admin commands for user management
- **Bundled Templates** - DaisyUI-styled Jinja2 templates

## Installation

```bash
pip install myfy-user
```

Or with all myfy modules:

```bash
pip install myfy[all]
```

## Quick Start

```python
from myfy.core import Application
from myfy.data import DataModule
from myfy.web import WebModule
from myfy.auth import AuthModule
from myfy.user import UserModule

# Create application
app = Application()

# Add required modules
app.add_module(DataModule())
app.add_module(WebModule())

# Add user module
user_module = UserModule(
    oauth_providers=["google", "github"],
    auto_create_tables=True,
)

# Integrate with AuthModule
app.add_module(AuthModule(
    authenticated_provider=user_module.get_authenticated_provider(),
))
app.add_module(user_module)
```

## Custom User Model

Extend the `BaseUser` model to add custom fields:

```python
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column
from myfy.user import BaseUser, UserModule

class User(BaseUser):
    __tablename__ = "users"

    # Custom fields
    full_name: Mapped[str | None] = mapped_column(String(255))
    phone: Mapped[str | None] = mapped_column(String(20))
    organization: Mapped[str | None] = mapped_column(String(100))

# Use custom model
user_module = UserModule(user_model=User)
```

## Configuration

Configure via environment variables:

```bash
# Required
MYFY_USER_SECRET_KEY=your-secret-key

# OAuth (optional)
MYFY_USER_OAUTH_GOOGLE_CLIENT_ID=...
MYFY_USER_OAUTH_GOOGLE_CLIENT_SECRET=...
MYFY_USER_OAUTH_GITHUB_CLIENT_ID=...
MYFY_USER_OAUTH_GITHUB_CLIENT_SECRET=...

# Sessions
MYFY_USER_SESSION_LIFETIME=604800  # 7 days
MYFY_USER_SESSION_SECURE=true

# Password requirements
MYFY_USER_PASSWORD_MIN_LENGTH=8
MYFY_USER_PASSWORD_ALGORITHM=argon2  # or bcrypt
```

## CLI Commands

```bash
# Initialize user templates for customization
myfy user init

# Create an admin user
myfy user create-admin -e admin@example.com

# List users
myfy user list
myfy user list --admins-only

# Reset a user's password
myfy user reset-password -e user@example.com

# Deactivate/activate users
myfy user deactivate -e user@example.com
myfy user activate -e user@example.com

# Verify email manually
myfy user verify-email -e user@example.com
```

## Routes

The module provides the following routes:

| Method | Path | Description |
|--------|------|-------------|
| GET | `/login` | Login page |
| POST | `/login` | Login submission |
| POST | `/logout` | Logout |
| GET | `/register` | Registration page |
| POST | `/register` | Registration submission |
| GET | `/oauth/{provider}` | OAuth redirect |
| GET | `/oauth/{provider}/callback` | OAuth callback |
| GET | `/forgot-password` | Password reset request |
| POST | `/forgot-password` | Send reset email |
| GET | `/reset-password/{token}` | Password reset page |
| POST | `/reset-password/{token}` | Set new password |
| GET | `/verify-email/{token}` | Verify email |
| GET | `/profile` | User profile (protected) |
| POST | `/profile` | Update profile |

## Background Tasks

When used with `myfy-tasks`, the module provides background tasks:

```python
from myfy.user import (
    send_verification_email,
    send_password_reset_email,
    send_welcome_email,
    cleanup_expired_tokens,
)

# Send verification email asynchronously
await send_verification_email.send(
    user_id=user.id,
    token=token.token,
    base_url="https://myapp.com",
)

# Cleanup old tokens (run daily via scheduler)
await cleanup_expired_tokens.send(days_old=7)
```

## License

MIT
