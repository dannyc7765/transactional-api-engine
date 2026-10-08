# Transactional API Engine

[![API Engine Test Pipeline](https://github.com/dannyc7765/transactional-api-engine/actions/workflows/api-tests.yml/badge.svg)](https://github.com/dannyc7765/transactional-api-engine/actions/workflows/api-tests.yml)
[![Live Allure Report](https://img.shields.io/badge/Allure_Report-Live_Telemetry-brightgreen?logo=allure)](https://dannyc7765.github.io/transactional-api-engine/)

High-concurrency transactional API built with FastAPI, PostgreSQL row-level locking (`SELECT ... FOR UPDATE`), and token sliding-window middleware.

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

Interactive execution timelines, test suites, and chaos run logs are deployed on every push:
👉 **[View Live Allure Telemetry Report](https://dannyc7765.github.io/transactional-api-engine/)**

The test harness evaluates database consistency across three isolated suites:
* **Chaos Tests (12):** Validates PostgreSQL row-level locks (`SELECT ... FOR UPDATE`) under concurrent race conditions to prevent negative ledger states and duplicate deductions.
* **Contract Tests (6):** Asserts strict schema compliance, HTTP status contracts, and payload validations via Pydantic models.
* **Functional Tests (2):** Validates standard end-to-end transaction lifecycles and idempotency guarantees.

## Local Pipeline Execution

Spin up isolated dependencies, await health checks, run functional/contract/chaos test suites, and tear down:

```bash
docker compose up --build --abort-on-container-exit --exit-code-from test-runner
```
