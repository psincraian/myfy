# Configuration

myfy uses Pydantic for type-safe, validated configuration with environment-based profiles.

---

## Basic Configuration

### Define Settings

```python
from myfy.core import BaseSettings
from pydantic import Field

class AppSettings(BaseSettings):
    # App settings
    app_name: str = Field(default="My App")
    debug: bool = Field(default=False)

    # Database
    database_url: str = Field(description="Database connection string")

    # Redis
    redis_url: str = Field(default="redis://localhost:6379")

    # API Keys
    api_key: str = Field(alias="API_KEY")
    jwt_secret: str
```

### Use Settings

```python
from myfy.core import Application

app = Application(settings_class=AppSettings, auto_discover=False)
```

Settings are automatically:
- Loaded from environment variables
- Loaded from `.env` files
- Validated by Pydantic
- Injected into providers

---

## Environment Variables

### Naming Convention

myfy uses UPPERCASE for environment variables:

```python
class Settings(BaseSettings):
    app_name: str  # Reads APP_NAME
    database_url: str  # Reads DATABASE_URL
    debug: bool  # Reads DEBUG
```

### Custom Prefix

```python
class Settings(BaseSettings):
    app_name: str  # Reads MYAPP_APP_NAME

    class Config:
        env_prefix = "MYAPP_"
```

### Aliases

```python
class Settings(BaseSettings):
    api_key: str = Field(alias="API_KEY")  # Reads API_KEY instead of api_key
```

---

## Environment Files

myfy loads `.env` files automatically:

### Default: `.env`

```bash
# .env
APP_NAME=My Application
DATABASE_URL=postgresql://localhost/mydb
DEBUG=true
API_KEY=secret-key-123
JWT_SECRET=super-secret
REDIS_URL=redis://localhost:6379
```

### Load Priority

```
1. System environment variables (highest priority)
2. .env.{profile} file (if MYFY_PROFILE is set)
3. .env file
4. Default values in code (lowest priority)
```

---

## Profiles

Profiles allow environment-specific configuration:

### Create Profile Files

```bash
# .env.dev
DEBUG=true
DATABASE_URL=postgresql://localhost/mydb_dev
API_KEY=dev-key-123

# .env.test
DEBUG=true
DATABASE_URL=postgresql://localhost/mydb_test
API_KEY=test-key-123

# .env.prod
DEBUG=false
DATABASE_URL=postgresql://prod-server/mydb
API_KEY=prod-key-xyz
```

### Use Profiles

```bash
# Development
MYFY_PROFILE=dev uv run myfy run

# Testing
MYFY_PROFILE=test pytest

# Production
MYFY_PROFILE=prod python app.py
```

---

## Validation

Pydantic validates all settings at startup:

### Type Validation

```python
class Settings(BaseSettings):
    port: int = 8000  # Must be an integer
    debug: bool = False  # Must be boolean
    timeout: float = 30.0  # Must be float
```

```bash
# Invalid:
PORT=abc  # Error: value is not a valid integer

# Valid:
PORT=8080
```

### Field Constraints

```python
from pydantic import Field

class Settings(BaseSettings):
    # String constraints
    app_name: str = Field(min_length=1, max_length=100)

    # Numeric constraints
    port: int = Field(ge=1, le=65535)  # Between 1 and 65535
    timeout: float = Field(gt=0)  # Greater than 0

    # Patterns
    email: str = Field(pattern=r'^[\w\.-]+@[\w\.-]+\.\w+$')
```

### Custom Validators

```python
from pydantic import validator

class Settings(BaseSettings):
    database_url: str

    @validator('database_url')
    def validate_database_url(cls, v):
        if not v.startswith(('postgresql://', 'mysql://')):
            raise ValueError('database_url must be postgresql:// or mysql://')
        return v
```

---

## Nested Configuration

### Group Related Settings

```python
from pydantic import BaseModel

class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = 10
    echo: bool = False

class RedisConfig(BaseModel):
    url: str
    ttl: int = 3600

class Settings(BaseSettings):
    app_name: str
    database: DatabaseConfig
    redis: RedisConfig
```

### Environment Variables for Nested Config

```bash
# Nested with double underscore
DATABASE__URL=postgresql://localhost/db
DATABASE__POOL_SIZE=20
DATABASE__ECHO=true

REDIS__URL=redis://localhost:6379
REDIS__TTL=7200
```

---

## Secrets Management

### From Environment Variables

```python
class Settings(BaseSettings):
    # Sensitive values
    jwt_secret: str
    api_key: str
    database_password: str
```

```bash
# Never commit these to git!
JWT_SECRET=your-secret-here
API_KEY=your-api-key
DATABASE_PASSWORD=your-password
```

### From Files

```python
from pydantic import Field

class Settings(BaseSettings):
    # Read from file
    jwt_secret: str = Field(env="JWT_SECRET_FILE")

    class Config:
        @classmethod
        def parse_env_var(cls, field_name: str, raw_val: str) -> Any:
            if field_name.endswith('_FILE'):
                # Read from file path
                return Path(raw_val).read_text().strip()
            return raw_val
```

```bash
# Point to secret file
JWT_SECRET_FILE=/run/secrets/jwt_secret
```

### With Docker Secrets

```yaml
# docker-compose.yml
services:
  app:
    image: myapp
    secrets:
      - jwt_secret
      - api_key
    environment:
      JWT_SECRET_FILE: /run/secrets/jwt_secret
      API_KEY_FILE: /run/secrets/api_key

secrets:
  jwt_secret:
    file: ./secrets/jwt_secret.txt
  api_key:
    file: ./secrets/api_key.txt
```

---

## Computed Properties

```python
class Settings(BaseSettings):
    host: str = "localhost"
    port: int = 8000

    @property
    def base_url(self) -> str:
        return f"http://{self.host}:{self.port}"

    @property
    def is_production(self) -> bool:
        return self.environment == "production"
```

---

## Using Settings

### In Providers

```python
from myfy.core import provider, SINGLETON

@provider(scope=SINGLETON)
def database(settings: Settings) -> Database:
    return Database(settings.database_url, pool_size=settings.database.pool_size)
```

### In Routes

```python
from myfy.web import route

@route.get("/config")
async def get_config(settings: Settings) -> dict:
    return {
        "app_name": settings.app_name,
        "debug": settings.debug,
        "version": settings.version
    }
```

### In Modules

```python
class DataModule(BaseModule):
    def configure(self, container: Container) -> None:
        settings = container.get(Settings)

        @provider(scope=SINGLETON)
        def database() -> Database:
            return Database(settings.database_url)
```

---

## Best Practices

### ✅ DO

- Use environment variables for all config
- Validate config with Pydantic constraints
- Use profiles for different environments
- Keep secrets out of version control
- Provide sensible defaults
- Document all settings

### ❌ DON'T

- Don't hardcode config values
- Don't commit secrets to git
- Don't use different config systems
- Don't skip validation
- Don't mix runtime and startup config

---

## Complete Example

```python
from myfy.core import BaseSettings
from pydantic import Field, validator
from typing import Literal

class DatabaseConfig(BaseModel):
    url: str
    pool_size: int = Field(default=10, ge=1, le=100)
    echo: bool = False

class Settings(BaseSettings):
    # App
    app_name: str = Field(default="My API")
    environment: Literal["dev", "test", "prod"] = "dev"
    debug: bool = False

    # Server
    host: str = "0.0.0.0"
    port: int = Field(default=8000, ge=1, le=65535)

    # Database
    database: DatabaseConfig

    # Redis
    redis_url: str = "redis://localhost:6379"

    # Secrets
    jwt_secret: str
    api_key: str

    @property
    def is_production(self) -> bool:
        return self.environment == "prod"

    @validator('debug')
    def debug_only_in_dev(cls, v, values):
        if v and values.get('environment') == 'prod':
            raise ValueError('debug cannot be true in production')
        return v

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
```

```bash
# .env.dev
APP_NAME=My Development API
ENVIRONMENT=dev
DEBUG=true
DATABASE__URL=postgresql://localhost/mydb_dev
DATABASE__POOL_SIZE=5
JWT_SECRET=dev-secret
API_KEY=dev-key

# .env.prod
APP_NAME=My Production API
ENVIRONMENT=prod
DEBUG=false
HOST=0.0.0.0
PORT=80
DATABASE__URL=postgresql://prod-db/mydb
DATABASE__POOL_SIZE=50
JWT_SECRET=${JWT_SECRET}  # From environment
API_KEY=${API_KEY}  # From environment
```

---

## Next Steps

- [Dependency Injection](dependency-injection.md) - Use settings in DI
- [Modules](modules.md) - Module-specific config
- [Deployment](../guides/deployment.md) - Production configuration
