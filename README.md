# Transactional API Engine

[![API Engine Test Pipeline](https://github.com/dannyc7765/transactional-api-engine/actions/workflows/api-tests.yml/badge.svg)](https://github.com/dannyc7765/transactional-api-engine/actions/workflows/api-tests.yml)
[![Live Allure Report](https://img.shields.io/badge/Allure_Report-Live_Telemetry-brightgreen?logo=allure)](https://dannyc7765.github.io/transactional-api-engine/)

A transactional REST API (FastAPI + PostgreSQL) built to be attacked: row-level locking prevents overselling and wallet overdraw under concurrent requests, and a Docker Compose test harness proves it in CI, with results published as an Allure report.

## System Architecture

```text
+-----------------------------------------------------------------------------------+
|                                Docker Network                                     |
|                                                                                   |
|  +---------------------+        HTTP/REST          +---------------------------+  |
|  |     test-runner     | ------------------------> |            api            |  |
|  |   (pytest-asyncio)  |                           |     (FastAPI/Uvicorn)     |  |
|  +---------------------+                           +---------------------------+  |
|             |                                                    |                |
|             | Direct DB Assertions                               | Connection Pool|
|             | (psycopg2)                                         | (Row Locking)  |
|             v                                                    v                |
|  +-----------------------------------------------------------------------------+  |
|  |                                      db                                     |  |
|  |                            (PostgreSQL 15 Alpine)                           |  |
|  +-----------------------------------------------------------------------------+  |
+-----------------------------------------------------------------------------------+
```

## Test Telemetry & Quality Engineering

Every defect found and fixed during hardening is documented in [INCIDENTS.md](INCIDENTS.md).

The [live Allure report](https://dannyc7765.github.io/transactional-api-engine/) is published from `main` on every merge. The overview shows the full run, and the suites view shows what each test protects.

![Allure report: all passing tests across chaos, functional and contract suites](docs/allure-overview.png)

![Allure suites view showing the concurrency tests that guard against overselling and wallet overdraw](docs/allure-suites.png)

The suite is organized into three tagged suites (`pytest -m chaos|functional|contract`):

* **Chaos (17):** PostgreSQL row-level locking under concurrent load, covering stock (no overselling), wallets (no overdraw) and charging (exactly one buyer is charged). Also JWT boundary faults (expiry, bad signature, `alg=none`), rate limiting, malformed payloads and client timeouts.
* **Functional (13):** Transaction lifecycles verified against both the API response and the database, input validation (negative/zero amounts), and error-code mapping (404/409/422).
* **Contract (6):** Strict schema validation (unknown fields rejected, types and enums enforced) and typed-client error handling. Live API responses are validated against the same models inside the functional suite.

## Design Decisions & Known Limitations

* Money is `Decimal` end to end: validated at the model boundary, stored as `NUMERIC(12,2)`, and read back exactly by the test helpers.
* Lock order is always user -> product to avoid deadlocks.
* The rate limiter is in-process (single worker only); a shared store such as Redis is needed for horizontal scale.
* No idempotency keys: a retried order creates a second order.
* Test credentials in `docker-compose.yml` are fixtures for the hermetic harness; secret scanning runs in CI (`.gitleaks.toml`).

## Local Pipeline Execution

Spin up isolated dependencies, await health checks, run functional/contract/chaos test suites, and tear down:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from test-runner
```
