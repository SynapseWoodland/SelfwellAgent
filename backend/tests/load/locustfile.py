"""Selfwell Backend Load Tests - Locust test scenarios.

This module defines load test scenarios for the Selfwell Agent Backend API.
Run with: locust -f backend/tests/load/locustfile.py --host=http://localhost:8000

Scenarios cover:
- Health check endpoints (liveness/readiness probes)
- Root endpoint and docs
- Concurrent user simulation with weighted task distribution
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from locust import task
from locust.contrib.fasthttp import RestUser as HttpUser

if TYPE_CHECKING:
    from locust import events


class SelfwellHealthUser(HttpUser):
    """Simulates a client hitting health check endpoints frequently.

    These endpoints are lightweight but critical for orchestration systems
    (Kubernetes liveness/readiness probes, load balancers).
    """

    host = "http://localhost:8000"

    @task(50)
    def healthz(self) -> None:
        """Primary health check - highest weight (50)."""
        self.client.get("/healthz", name="/healthz")

    @task(10)
    def root(self) -> None:
        """Root endpoint - medium weight (10)."""
        self.client.get("/", name="/")

    @task(5)
    def docs(self) -> None:
        """Swagger UI docs - lower weight (5)."""
        self.client.get("/docs", name="/docs")

    @task(3)
    def openapi_schema(self) -> None:
        """OpenAPI schema endpoint - low weight (3)."""
        self.client.get("/openapi.json", name="/openapi.json")


class SelfwellAPISmokeUser(HttpUser):
    """Simulates a client performing API discovery and metadata checks.

    Useful for testing the overhead of OpenAPI schema generation and
    ensuring docs are accessible under load.
    """

    host = "http://localhost:8000"

    @task(2)
    def openapi(self) -> None:
        """Fetch OpenAPI schema."""
        self.client.get("/openapi.json", name="/openapi.json")

    @task(1)
    def docs_oauth2_redirect(self) -> None:
        """Test OAuth2 redirect from docs page."""
        self.client.get("/docs/oauth2-redirect.html", name="/docs/oauth2-redirect")

    @task(1)
    def redoc(self) -> None:
        """Alternative API documentation (ReDoc)."""
        self.client.get("/redoc", name="/redoc")


@events.init_command_line_parser.add_listener
def _(parser: events.CommandLineParser) -> None:
    """Register custom command line arguments for Locust."""
    parser.add_argument("--test-duration", type=int, default=60, help="Run duration in seconds")
    parser.add_argument(
        "--peak-users",
        type=int,
        default=100,
        help="Peak concurrent users to simulate",
    )
