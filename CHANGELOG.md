# Changelog

All notable changes to this project will be documented in this file.
The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

---
## [1.0.3] - 2026-03-XX
### Added
- `render_spa_template` for adding jsx/tsx template (e.g. `render_spa_template("index.jsx")`)
- `File()` recieving file request
- `server`, `responses` and `mermaid.js syntax` added to route param
---
## [1.0.2]
### Added
`GET`, `POST`, `PATCH`, `PUT`, `DELETE`, `HEAD`, `OPTIONS` route **Decorator**

## [1.0.1] - 2025-09-06
### Added
- `Form()` helper for request form-data binding.
- `guard()` decorator for grouping multiple route guards (e.g. `@guard(jwt_required, ...)`).

### Improved
- Error responses now fully aligned with Problem Details format (RFC 7807).
- Documentation updates to reflect new features (`Form`, `guard`).

---

## [1.0.0] - 2025-08-XX
### Added
- Initial stable release of **Flask Nova** 🎉
- FastAPI-style dependency injection with `Depend()`.
- Automatic request binding for query, JSON, and path parameters.
- Built-in Swagger UI & OpenAPI schema generation.
- Async support (`Flask[async]`).
- Problem Details–style error responses.

---

[1.0.3]: https://pypi.org/project/flask-nova/1.0.1/
[1.0.2]: https://pypi.org/project/flask-nova/1.0.1/
[1.0.1]: https://pypi.org/project/flask-nova/1.0.1/
[1.0.0]: https://pypi.org/project/flask-nova/1.0.0/
