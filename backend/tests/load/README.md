# Load Tests

This directory contains Locust-based load testing scenarios for the Selfwell Agent Backend.

## Overview

The load tests simulate realistic traffic patterns against the FastAPI application:

| Scenario | User Class | Weight | Endpoint |
|----------|------------|--------|----------|
| Health checks | `SelfwellHealthUser` | 50 | `GET /healthz` |
| Root | `SelfwellHealthUser` | 10 | `GET /` |
| Swagger docs | `SelfwellHealthUser` | 5 | `GET /docs` |
| OpenAPI schema | `SelfwellHealthUser` | 3 | `GET /openapi.json` |
| ReDoc docs | `SelfwellAPISmokeUser` | 1 | `GET /redoc` |

## Running Load Tests

### Quick Start (Web UI)

```bash
# From project root
locust -f backend/tests/load/locustfile.py --host=http://localhost:8000

# Then open http://localhost:8089 in your browser
```

### Headless Mode

```bash
# Run for 60s with 100 concurrent users, spawning 10 users/sec
locust -f backend/tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 100 \
  --spawn-rate 10 \
  --run-time 60s \
  --html=backend/tests/load/report.html
```

### With Custom Args

```bash
# Extended run with peak users
locust -f backend/tests/load/locustfile.py \
  --host=http://localhost:8000 \
  --headless \
  --users 500 \
  --spawn-rate 20 \
  --run-time 5m \
  --test-duration 300 \
  --peak-users 500 \
  --html=backend/tests/load/report.html \
  --csv=backend/tests/load/results
```

## Interpreting Results

### Key Metrics

| Metric | Description | Target |
|--------|-------------|--------|
| **RPS** | Requests per second | Depends on hardware |
| **Avg Latency** | Mean response time | < 100ms for healthz |
| **95th %ile** | 95th percentile latency | < 200ms |
| **Failure Rate** | % of non-2xx responses | < 1% |

### Success Criteria

- `/healthz` p99 latency < 200ms
- No HTTP 5xx errors
- System remains responsive under peak load

### Locust Web UI Tabs

1. **Statistics** - RPS, latency, failure rate per endpoint
2. **Charts** - Real-time graphs of RPS and response times
3. **Failures** - Error details and stack traces
4. **Exceptions** - Uncaught exceptions in the locustfile
5. **Reports** - Download HTML report after run

## CI Integration

### GitHub Actions Example

```yaml
# .github/workflows/load-test.yml
name: Load Tests

on:
  push:
    branches: [main]
  schedule:
    - cron: '0 2 * * *'  # Daily at 2 AM

jobs:
  load-test:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4

      - name: Setup Python
        uses: actions/setup-python@v5
        with:
          python-version: '3.12'

      - name: Install dependencies
        run: |
          pip install uv
          uv sync --dev

      - name: Start backend
        run: uvicorn backend.app.main:app --host 0.0.0.0 --port 8000 &
        env:
          LOG_LEVEL: WARNING

      - name: Wait for backend
        run: sleep 5

      - name: Run load test
        run: |
          locust -f backend/tests/load/locustfile.py \
            --host=http://localhost:8000 \
            --headless \
            --users 50 \
            --spawn-rate 5 \
            --run-time 30s \
            --html=backend/tests/load/report.html \
            --csv=backend/tests/load/results

      - name: Upload report
        uses: actions/upload-artifact@v4
        if: always()
        with:
          name: load-test-report
          path: backend/tests/load/report.html
```

### Locustfile CLI Args

The following custom arguments are supported:

| Argument | Default | Description |
|----------|---------|-------------|
| `--test-duration` | 60 | Test duration in seconds |
| `--peak-users` | 100 | Peak concurrent users |

## Writing New Scenarios

Add new task classes inheriting from `HttpUser`:

```python
from locust.contrib.fasthttp import RestUser as HttpUser

class MyNewUser(HttpUser):
    host = "http://localhost:8000"

    @task(10)
    def my_endpoint(self) -> None:
        self.client.get("/my-endpoint")
```

Weight determines relative frequency. Higher weight = more requests.

## Dependencies

- `locust>=2.32.0` (dev dependency in `pyproject.toml`)
- FastAPI backend running at `--host`

## Notes

- Load tests run against the actual running application (not TestClient)
- Ensure PostgreSQL and Redis are accessible before running
- For sustained load, monitor system resources (CPU, memory, DB connections)
