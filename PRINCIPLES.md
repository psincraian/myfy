# Principles
⸻

🧭 Core philosophy
	1.	Opinionated, not rigid.
**myfy** comes with strong defaults so you can start fast — but everything can be replaced or extended.
	2.	Defaults by default.
The fastest path is the golden path. Convention wins, but configuration is always possible.
	3.	Sugar with substance.
The framework provides ergonomic decorators and helpers — they’re sugar over explicit, well-defined mechanics.
	4.	Pythonic over ceremonial.
Clean, readable code — no XML, no annotations, no hidden globals. Simplicity beats abstraction.
	5.	Predictable lifecycle.
Clear startup/shutdown order, explicit hooks, graceful recovery. Apps are deterministic and introspectable.
	6.	Modular by design.
Every feature (web, data, telemetry, tasks) is just a module. The kernel stays tiny; modules wire themselves in.
	7.	Replace anything.
Defaults are composable — swap routers, ORMs, or DI providers without breaking the core.
	8.	Typed, validated, safe.
All configs and interfaces are typed; validation mirrors your types at runtime.
	9.	Async-native, context-aware.
Built on ASGI + AnyIO; request and task scopes handled via contextvars.
	10.	Observability built-in.
Logging, tracing, and metrics are first-class citizens — zero setup needed to see what your app is doing.

⸻

⚙️ Configuration & runtime
	11.	Profiles over env chaos.
dev, test, prod — layered, predictable configuration.
	12.	Runtime reconfig is deliberate.
Only safe settings (like log levels) can hot-reload. Everything else requires a restart.
	13.	Dependency injection with scopes.
singleton, request, task — no hidden globals, no surprises.
	14.	Zero heavy reflection on the hot path.
All introspection happens once at startup. Requests stay fast and predictable.
	15.	Safe by default.
Security headers, JSON-only APIs, and sensible timeouts are baked in.

⸻

❤️ Developer experience
	16.	One-command DX.
myfy new, myfy run, myfy routes, myfy doctor — batteries included, no boilerplate.
	17.	Instant productivity, gradual control.
Start simple, dig deeper as your app grows. Defaults scale with you.
	18.	Friendly errors and docs.
Misconfigurations fail fast with clear, actionable messages.
	19.	Testable by nature.
Override dependencies easily, spin up fake apps in tests, and verify modules in isolation.

⸻

✨ TL;DR — your “Zen”

Start fast, stay flexible.
Have strong defaults, but never lose control.
Pythonic, async, typed, and open.
