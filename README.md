# Transactional API Engine

[![API Engine Test Pipeline](https://github.com/dannyc7765/transactional-api-engine/actions/workflows/api-tests.yml/badge.svg)](https://github.com/dannyc7765/transactional-api-engine/actions/workflows/api-tests.yml)

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