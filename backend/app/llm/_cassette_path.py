"""Default cassette dir resolver for mock_doubles.

包装在独立模块避免 ``mock_doubles.py`` import 期强制读 .env。
"""

from pathlib import Path


def default_cassettes_path() -> Path:
    """Return ``backend/tests/cassettes`` absolute path (no I/O)."""
    return Path(__file__).resolve().parents[3] / "tests" / "cassettes"


__all__ = ["default_cassettes_path"]
