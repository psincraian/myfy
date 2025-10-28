# ADR-0004: Frontend Module Integration

## Status

Accepted

## Context

The myfy framework started as a backend-focused framework with modules for HTTP routing (web), dependency injection (core), and CLI tools. However, many modern applications require server-side rendering (SSR) capabilities, and developers often face the choice between:

1. **Separate Frontend Deployment** - Deploy frontend (React/Vue/etc.) separately from the backend
2. **Integrated SSR** - Server-side rendering with templates like Jinja2, integrated with backend
3. **Hybrid Approach** - Backend serves API + some server-rendered pages

Problems with existing solutions:
- FastAPI has no built-in frontend/template support (just serves API)
- Django's template system is tightly coupled and heavyweight
- Flask requires manual setup of Jinja2, asset management, etc.
- Modern tooling (Vite, Tailwind) not integrated with Python frameworks

For applications that need:
- Admin dashboards
- Marketing pages with SEO
- Progressive enhancement patterns
- Simpler deployment (single server)

...a fully-featured SSR module makes sense as part of the framework.

## Decision

We will add an **optional FrontendModule** to myfy that provides:

### Core Features
1. **Server-Side Rendering** with Jinja2 templates
2. **Modern CSS/JS Tooling** via Vite, Tailwind CSS 4, and DaisyUI 5
3. **Development Experience** with Hot Module Replacement (HMR)
4. **Production Optimization** with asset fingerprinting and cache busting
5. **Auto-Scaffolding** to quickly initialize frontend structure

### Architecture Decisions

#### 1. Module as Separate Package
- Package name: `myfy-frontend` (follows existing pattern)
- Can be installed independently: `pip install myfy-frontend`
- Zero impact on users who don't need SSR

#### 2. Tool Choices

**Jinja2 for Templates:**
- Industry standard for Python SSR
- Fast, secure, well-documented
- Compatible with Starlette/FastAPI ecosystem

**Vite for Asset Bundling:**
- Modern, fast build tool
- Best-in-class HMR experience
- Native ES modules support
- Excellent plugin ecosystem

**Tailwind CSS 4:**
- Utility-first CSS framework
- Native CSS engine (no PostCSS dependency)
- Excellent performance
- Wide adoption

**DaisyUI 5:**
- Component library built on Tailwind
- Beautiful, accessible components out-of-the-box
- Reduces custom CSS needs

#### 3. Subprocess Management
- Vite dev server runs as managed subprocess
- Graceful startup/shutdown via ProcessManager
- Health checks ensure server readiness
- Production mode: pre-built assets only (no Vite)

#### 4. Static File Handling
- Development: Proxy to Vite dev server (HMR)
- Production: Serve from `dist/` directory
- Manifest-based asset resolution (cache busting)

#### 5. Configuration
- Module-specific settings with `MYFY_FRONTEND_` prefix (ADR-0002 compliance)
- Environment-based behavior (development vs production)
- Opt-in auto-scaffolding (default: explicit initialization)

### Integration with Existing Modules

```python
from myfy.core import Application
from myfy.web import WebModule, route
from myfy.frontend import FrontendModule
from starlette.templating import Jinja2Templates

app = Application(auto_discover=False)
app.add_module(WebModule())
app.add_module(FrontendModule(auto_init=True))

# Templates are registered in DI container
@route.get("/")
async def home(request: Request, templates: Jinja2Templates):
    return render_template("home.html", request=request, templates=templates)
```

## Consequences

### Positive
- **Complete Stack Solution** - myfy can now handle full-stack applications
- **Modern DX** - Vite + Tailwind provide excellent developer experience
- **Optional** - Users who only need API can ignore this module
- **Follows Patterns** - Adheres to ADR-0002 (modular config) and ADR-0003 (DI with scopes)
- **Production Ready** - Built-in asset optimization and caching
- **Rapid Prototyping** - Auto-scaffolding gets projects started quickly

### Neutral
- **Node.js Dependency** - Requires Node.js for development (but not for production if assets pre-built)
- **Learning Curve** - Developers need to understand Vite, Tailwind, DaisyUI
- **More Moving Parts** - Subprocess management adds complexity

### Negative
- **Maintenance Burden** - Need to keep up with Vite, Tailwind, DaisyUI updates
- **Larger Scope** - Framework now covers frontend concerns, not just backend
- **Potential Version Conflicts** - Node.js ecosystem moves fast, may have breaking changes

## Alternatives Considered

### 1. No Frontend Module (Users Bring Their Own)
**Rejected** because:
- Poor developer experience for common use case (SSR)
- Every project reinvents the wheel (Jinja2 setup, asset pipeline, etc.)
- Missed opportunity to provide integrated, tested solution
- Framework feels incomplete without SSR support

### 2. Basic Jinja2 Only (No Vite/Tailwind)
**Rejected** because:
- Modern frontend development expects HMR, module bundling, etc.
- Manually managing CSS/JS in 2024+ is painful
- Competitors (Django, Rails) offer integrated asset pipelines
- Half-measure doesn't solve the full problem

### 3. Use Webpack Instead of Vite
**Rejected** because:
- Webpack is slower and more complex to configure
- Vite's HMR is significantly faster
- Industry momentum is toward Vite for new projects
- Native ES modules are the future

### 4. Use Bootstrap Instead of Tailwind + DaisyUI
**Rejected** because:
- Tailwind's utility-first approach is more flexible
- Better tree-shaking (smaller CSS bundles)
- DaisyUI provides component layer without forcing framework choice
- Modern aesthetic and active ecosystem

### 5. Integrate Frontend into WebModule
**Rejected** because:
- Violates modularity principle (ADR-0002)
- Users who only need API would have unused dependencies
- Harder to version and maintain independently
- Separate package allows independent evolution

### 6. Use React/Vue Components Instead of Templates
**Rejected** because:
- SSR with React/Vue adds significant complexity (hydration, etc.)
- Many use cases don't need full SPA (admin dashboards, marketing pages)
- Templates are simpler for progressive enhancement
- Users who want React/Vue can still use separate frontend deployment

## References

- [PRINCIPLES.md](../../PRINCIPLES.md) - Framework design philosophy
- [ADR-0002](./0002-modular-configuration-design.md) - Modular configuration
- [ADR-0003](./0003-dependency-injection-with-scopes.md) - DI with scopes
- [Vite Documentation](https://vitejs.dev/) - Build tool and dev server
- [Tailwind CSS](https://tailwindcss.com/) - Utility-first CSS framework
- [DaisyUI](https://daisyui.com/) - Component library for Tailwind
- [Jinja2](https://jinja.palletsprojects.com/) - Template engine
