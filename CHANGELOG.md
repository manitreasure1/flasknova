# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [0.2.0] Latest
### Configs
- ANSI_COLOR_JSON_LOG: bool
    - this change the behaviour of flask internal logger from text to RFC 7807 problem detail colorful json log

## Error handling
- `HTTPException` implement `traceparent` header and `trace_id` by default

## Serailizer
- Custom classes and dataclass can be used as serializer not only binders
    - this will `raise ValueError` if cls field is not in the return type
    - no field typed check

## Binder
- File binder added for file request `args`: `name: str`  file name and `multiple: bool` to get list of files

## Router
### Native Return Type Dispatcher
used in place of response model

## Openapi
- `servers: list`, `deprecated: bool` and `responses: dict` params added to route param

## Task
- `to_thread`:
    - Run a callable in a worker thread from an async context.
- `to_process`:
    - Execute a sync callable in a worker process or thread pool and runs CPU-intensive or I/O-bound code in a separate pool.

### Deprecated
route method `OPTIONS` and `HEAD` has no behavior

## [0.1.1] - 2025-09-06
### Added
- `Form()` helper for request form-data binding.
- `guard()` decorator for grouping multiple route guards (e.g. `@guard(jwt_required, ...)`).

### Improved
- Error responses now fully aligned with Problem Details format (RFC 7807).
- Documentation updates to reflect new features (`Form`, `guard`).

---

## [0.1.0] - 2025-07-23
### Added
- Initial stable release of **Flask Nova**
- Automatic request binding for query, JSON, and path parameters.
- Built-in Swagger UI & OpenAPI schema generation.
- Async support (`Flask[async]`).
- Problem Details–style error responses.

---
## Releases
[0.1.3](https://pypi.org/project/flask-nova/0.1.3/)

[0.1.2](https://pypi.org/project/flask-nova/0.1.2/)

[0.1.1](https://pypi.org/project/flask-nova/0.1.1/)

[0.1.0](https://pypi.org/project/flask-nova/0.1.0/)
