"""DDD Bounded Contexts 根包。

每个 Context 子包内包含：
- domain/     — Aggregate / Entity / Value Object / Events
- application/ — Application Service
- infrastructure/ — Repository / ORM / External Adapters
- interfaces/  — FastAPI Router / Controllers
"""

__all__ = ["user"]
