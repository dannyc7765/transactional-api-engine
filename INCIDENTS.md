# Incident Log

Post-mortems for failures hit while building and hardening this project: what broke, why, how it was fixed, and what now prevents it from happening again.

Each entry follows the same structure: **Trigger, Impact, Root Cause, Mitigation, Prevention**. Entries tagged **system defect** are bugs in the API itself. The rest are tooling, environment, or test-suite failures.

**Read these three first.** [INC-014](#inc-014-concurrent-purchases-oversold-inventory) is the chaos suite catching an oversell race it was built to find. [INC-019](#inc-019-order-endpoint-accepted-zero-and-negative-prices) and [INC-020](#inc-020-invalid-input-returned-http-500) are where a fully green suite was hiding a money-printing bug and unmapped 500s. Together they show what the suite catches and where it was blind. [INC-009](#inc-009-typed-client-rejected-valid-uuid-strings-from-the-api) is the root of INC-020 and is worth reading alongside it.

**Severity scale:** Low = developer inconvenience. Medium = blocked local work or repo hygiene. High = incorrect API behavior or a broken quality gate. Critical = financial or data-integrity impact.

## Summary

| ID | Title | Severity | Type | Status |
|----|-------|----------|------|--------|
| [INC-001](#inc-001-powershell-parser-crash-on-posix-brace-expansion) | PowerShell parser crash on POSIX brace expansion | Low | Tooling | Resolved |
| [INC-002](#inc-002-project-root-self-nesting-from-unverified-relative-path) | Project root self-nesting from unverified relative path | Medium | Environment | Resolved |
| [INC-003](#inc-003-contract-tests-failing-on-pydantic-v2-defaults-and-brittle-assertions) | Contract tests failing on Pydantic v2 defaults and brittle assertions | High | Test defect + model gap | Resolved |
| [INC-004](#inc-004-milestone-2-files-committed-under-milestone-1-and-default-branch-drift) | Milestone 2 files committed under Milestone 1, default branch drift | Medium | Version control | Resolved |
| [INC-005](#inc-005-integration-tests-run-before-containers-were-up) | Integration tests run before containers were up | High | Test orchestration | Resolved |
| [INC-006](#inc-006-host-port-collision-on-postgresql-ports-5432-and-5433) | Host port collision on PostgreSQL ports 5432 and 5433 | Medium | Infrastructure | Resolved |
| [INC-007](#inc-007-functional-tests-failed-because-the-api-server-was-not-running) | Functional tests failed because the API server was not running | Medium | Test orchestration | Resolved |
| [INC-008](#inc-008-powershell-prompt-text-pasted-as-a-command) | PowerShell prompt text pasted as a command | Low | Tooling | Resolved |
| [INC-009](#inc-009-typed-client-rejected-valid-uuid-strings-from-the-api) | Typed client rejected valid UUID strings from the API | Medium | Contract defect | Resolved (workaround later reversed) |
| [INC-010](#inc-010-tests-used-database-client-methods-that-did-not-exist) | Tests used database-client methods that did not exist | Medium | Test defect | Resolved |
| [INC-011](#inc-011-databaseclient-defaulted-to-port-5432-and-reached-the-hosts-postgresql) | DatabaseClient defaulted to port 5432 and reached the host's PostgreSQL | Medium | Configuration defect | Resolved |
| [INC-012](#inc-012-state-reset-helper-never-committed-and-leaked-dirty-test-state) | State-reset helper never committed and leaked dirty test state | Medium | Test defect | Resolved |
| [INC-013](#inc-013-chaos-test-hit-a-foreign-key-violation-and-the-api-returned-500) | Chaos test hit a foreign-key violation and the API returned 500 | Medium | Test defect + latent system defect | Test fixed here, API fixed in INC-020 |
| [INC-014](#inc-014-concurrent-purchases-oversold-inventory) | Concurrent purchases oversold inventory | **Critical** | System defect | Resolved |
| [INC-015](#inc-015-http-client-refused-to-send-a-malformed-authorization-header) | HTTP client refused to send a malformed Authorization header | Low | Test defect | Resolved |
| [INC-016](#inc-016-allure-report-deploy-failed-with-http-403) | Allure report deploy failed with HTTP 403 | Medium | CI/CD | Resolved |
| [INC-017](#inc-017-github-pages-served-the-readme-instead-of-the-allure-report) | GitHub Pages served the README instead of the Allure report | Low | CI/CD configuration | Resolved |
| [INC-018](#inc-018-git-line-ending-warnings-on-windows) | Git line-ending warnings on Windows | Low | Tooling | Resolved |
| [INC-019](#inc-019-order-endpoint-accepted-zero-and-negative-prices) | Order endpoint accepted zero and negative prices | **Critical** | System defect + test gap | Resolved, residual risk noted |
| [INC-020](#inc-020-invalid-input-returned-http-500) | Invalid input returned HTTP 500 | High | System defect + test gap | Resolved |
| [INC-021](#inc-021-expired-token-test-passed-for-the-wrong-reason) | Expired-token test passed for the wrong reason | Medium | Test defect (false positive) | Resolved |
| [INC-022](#inc-022-purchase-endpoint-never-charged-the-wallet) | Purchase endpoint never charged the wallet | High | System defect + test gap | Resolved |
| [INC-023](#inc-023-secret-scanner-flagged-expired-test-jwts-in-published-allure-data) | Secret scanner flagged expired test JWTs in published Allure data | Low | Security hygiene | Resolved |
| [INC-024](#inc-024-ci-metadata-steps-failed-on-root-owned-test-results) | CI metadata steps failed on root-owned test results | Low | CI/CD | Resolved |

---

## INC-001: PowerShell parser crash on POSIX brace expansion

- **Date:** 2026-10-05
- **Severity:** Low
- **Type:** Tooling
- **Status:** Resolved

**Trigger.** A scaffolding command written for Bash was run in Windows PowerShell:

```powershell
mkdir -p project-2-api-engine/{.github/workflows,src/{client,models,d ...
```

**Impact.** The command aborted with `ParserError: MissingArgument`. No directories were created on the first pass.

```text
Missing argument in parameter list.
At line:1 char:100
    + CategoryInfo          : ParserError: (:) [], ParentContainsErrorRecordException
    + FullyQualifiedErrorId : MissingArgument
```

**Root cause.** Bash expands `{a,b,c}` into separate arguments before the program runs. PowerShell treats `{}` as a script block, so the unescaped commas and braces produced an incomplete parameter list.

**Mitigation.** Replaced the brace expansion with an explicit PowerShell array:

```powershell
@('.github/workflows', 'src/client', 'src/models', 'src/database', 'src/utils',
  'tests/contract', 'tests/functional', 'tests/chaos') | ForEach-Object {
    New-Item -ItemType Directory -Path "project-2-api-engine/$_" -Force
}
```

**Prevention.** Directory bootstrapping goes through shell-agnostic tooling (`pathlib.Path.mkdir(parents=True, exist_ok=True)`), and setup instructions never assume a specific shell.

---

## INC-002: Project root self-nesting from unverified relative path

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Environment
- **Status:** Resolved

**Trigger.** A relative `Set-Location project-2-api-engine` was run while the shell was already inside a directory of that name.

**Impact.** The tree gained a duplicate `project-2-api-engine/project-2-api-engine/`. The virtual environment was created in the inner copy, so the editor's outer workspace could not see the installed packages. A follow-up `Move-Item` collided with existing folders:

```text
(venv) PS C:\Users\<user>\project-2-api-engine\project-2-api-engine>
Move-Item : Cannot create a file when that file already exists.
    + FullyQualifiedErrorId : MoveDirectoryItemIOError,Microsoft.PowerShell.Commands.MoveItemCommand
```

**Root cause.** The working directory had already advanced one level and the path was never checked. The relative `cd` then created a second level instead of staying put.

**Mitigation.**

1. Deactivated the misplaced virtual environment.
2. Removed the redundant nested directory: `Remove-Item -Path .\project-2-api-engine -Recurse -Force`.
3. Recreated the virtual environment from the true root and verified the interpreter path:

```powershell
Get-Command python | Select-Object -ExpandProperty Source
# C:\Users\<user>\project-2-api-engine\venv\Scripts\python.exe
```

**Prevention.** Print `$PWD` before any batch file operation. Open the workspace with `code -r .` from the project root so the editor and the shell agree on the project boundary.

---

## INC-003: Contract tests failing on Pydantic v2 defaults and brittle assertions

- **Date:** 2026-10-05
- **Severity:** High
- **Type:** Test defect + model gap
- **Status:** Resolved

**Trigger.** The first run of the contract suite.

**Impact.** 3 of 4 baseline contract tests failed, so the contract gate could not be trusted:

```text
FAILED tests/contract/test_contracts.py::TestContractIntegrity::test_schema_fails_on_extra_unexpected_field
FAILED tests/contract/test_contracts.py::TestContractIntegrity::test_schema_fails_on_type_mismatch
FAILED tests/contract/test_contracts.py::TestContractIntegrity::test_schema_fails_on_invalid_enum_state
Failed: DID NOT RAISE ValidationError
AssertionError: assert 'is_instance_of' == 'enum'
========== 3 failed, 1 passed in 0.36s ==========
```

**Root cause.** Three independent causes, two in the tests and one in the model:

1. **Payloads were not isolated to one failure each.** Validation at that point was strict (the same setting behind [INC-009](#inc-009-typed-client-rejected-valid-uuid-strings-from-the-api)), and strict mode does not coerce. A stringified UUID in a mock payload was rejected on `order_id`, so validation stopped before reaching the field each test was actually probing (`total_amount`, `status`).
2. **Assertions matched pydantic-core's internal error-type strings** (`'enum'` vs `'is_instance_of'`). Those strings are an implementation detail of the validation backend and differ by input shape.
3. **The model silently ignored unknown fields.** The extra-field test failed with `DID NOT RAISE` because Pydantic v2 defaults to `extra='ignore'`, so `OrderResponse` dropped unexpected keys instead of rejecting them. In a contract suite that masks upstream schema drift.

**Mitigation.** Refactored `tests/contract/test_contracts.py`:

- Valid fields use native `uuid.UUID` objects, so each test fails on exactly the field under test.
- Assertions check *which field* failed through `loc`, not the library's error-type wording:

```python
errors = exc.value.errors()
failed_fields = [e["loc"][0] for e in errors]
assert "total_amount" in failed_fields
```

For the model gap, `OrderResponse` (and `OrderCreateRequest`) now set `model_config = ConfigDict(extra="forbid")`, and the extra-field test asserts the `extra_forbidden` error type, which is the documented contract of that setting.

**Prevention.** One failure boundary per test, with every other field valid. Assert on the field that failed, not on library-internal error wording. The order models reject unknown fields; the other models do not yet (see Open items).

---

## INC-004: Milestone 2 files committed under Milestone 1 and default branch drift

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Version control
- **Status:** Resolved

**Trigger.** `git add .` was run without checking `git status` first.

**Impact.** Milestone 2 files (`docker-compose.yml`, `init.sql`, `src/database/db_client.py`, `tests/functional/test_orders.py`) landed in a commit labeled for Milestone 1. The local default branch was `master` while the project convention is `main`.

```text
[master cad19c3] feat(milestone-1): complete scaffolding, typed client, and contract verification
 5 files changed, 214 insertions(+), 4 deletions(-)
 create mode 100644 docker-compose.yml
 create mode 100644 init.sql
 create mode 100644 src/database/db_client.py
 create mode 100644 tests/functional/test_orders.py
```

**Root cause.** Git's local default branch was still `master`, and files from the next milestone were already in the working tree when the blanket `git add .` ran.

**Mitigation.**

```bash
git branch -M main
```

The contract suite was made runnable on its own with `pytest -m contract`, so the Milestone 1 gate no longer depends on Milestone 2 files.

**Prevention.**

- Run `git status` before every commit and stage by path, not by wildcard.
- `git config --global init.defaultBranch main`.
- Scope commit messages (`feat(milestone-1): ...`, `feat(milestone-2): ...`).

---

## INC-005: Integration tests run before containers were up

- **Date:** 2026-10-05
- **Severity:** High
- **Type:** Test orchestration
- **Status:** Resolved

**Trigger.** Running an unrestricted `pytest -v` across the whole workspace.

**Impact.** Integration tests started before PostgreSQL and the API were reachable, producing connection errors that look like product failures but are not:

```text
psycopg2.OperationalError: could not connect to server: Connection refused
    Is the server running on host "localhost" (127.0.0.1) and accepting
    TCP/IP connections on port 5432?
httpx.ConnectError: [Errno 111] Connection refused
```

**Root cause.** The runner executed offline contract tests and infrastructure-dependent tests in one pass, with nothing guaranteeing the services were up first.

**Mitigation.**

- Contract tests run on their own with no services: `pytest tests/contract -v`.
- Everything else runs inside Docker Compose, where `depends_on` with `condition: service_healthy` gates the test-runner on real healthchecks (`pg_isready` for PostgreSQL, an HTTP probe for the API).
- The pipeline command is `docker compose up --build --abort-on-container-exit --exit-code-from test-runner`, so the CI job's exit code is the test-runner's exit code.

**Prevention.**

- Services are never assumed to be up: readiness is a healthcheck, not a sleep.
- Tests that need a database or API are separated from tests that need nothing (see Rule 1).

---

## INC-006: Host port collision on PostgreSQL ports 5432 and 5433

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Infrastructure
- **Status:** Resolved

**Trigger.** `docker compose up` for the PostgreSQL service.

**Impact.** The container failed to start, which blocked every database-backed test. A second attempt on an alternative port failed the same way:

```text
Error response from daemon: driver failed programming external connectivity on endpoint engine_postgres:
Bind for 0.0.0.0:5432 failed: port is already allocated

Error response from daemon: Bind for 0.0.0.0:5433 failed: port is already allocated
```

**Root cause.** Other processes on the Windows host already held ports 5432 and 5433, so Docker could not publish the container's port on either.

**Mitigation.**

1. Inspected what was listening:

```powershell
Get-NetTCPConnection -LocalPort 5432, 5433 -ErrorAction SilentlyContinue
```

2. Moved the published host port to 5439 in `docker-compose.yml`:

```yaml
ports:
  - "5439:5432"
```

3. Pointed host-side tooling at the new port: `$env:DB_PORT="5439"`.

The container-side port is unchanged. Inside the Compose network the API and test-runner reach the database at `db:5432`, so the host port only matters for tools running outside Docker.

**Prevention.** The published port is a single line in `docker-compose.yml`, and nothing inside the containers depends on it. It is currently hardcoded, and making it configurable is tracked in [Open items](#open-items).

---

## INC-007: Functional tests failed because the API server was not running

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Test orchestration
- **Status:** Resolved

**Trigger.** First run of `tests/functional/test_orders.py`.

**Impact.** Every functional test failed with a socket-level refusal on `POST /users`:

```text
E   httpcore.ConnectError: [WinError 10061] No connection could be made because the target machine actively refused it
E   src.client.api_client.APIClientError: Connection failed for POST /users: [WinError 10061] ...
============================== 1 failed in 5.46s ==============================
```

**Root cause.** The functional tests are an out-of-process HTTP client. PostgreSQL was up on port 5439, but nothing was listening on port 8000: the FastAPI application had not been written or started yet. Windows returned `WSAECONNREFUSED` (10061). This is the same class of failure as [INC-005](#inc-005-integration-tests-run-before-containers-were-up), here for the API tier instead of the database.

**Mitigation.**

1. Implemented the FastAPI entrypoint in `src/main.py` with the `/users` and `/orders` endpoints.
2. Installed the runtime dependencies: `python -m pip install fastapi "uvicorn[standard]"`.
3. Started it in a dedicated terminal: `python -m uvicorn src.main:app --host 127.0.0.1 --port 8000`.

**Prevention.** The API now runs as a Compose service with a healthcheck, and the test-runner service has `depends_on: api: condition: service_healthy`, so tests cannot start against a missing server.

---

## INC-008: PowerShell prompt text pasted as a command

- **Date:** 2026-10-05
- **Severity:** Low
- **Type:** Tooling
- **Status:** Resolved

**Trigger.** Commands copied from a terminal log, including the prompt prefix, were pasted into PowerShell.

**Impact.** The pasted lines failed to parse, which delayed debugging:

```text
At line:1 char:8
+ (venv) PS C:\Users\<user>\project-2-api-engine> .\venv\Scripts\Activa ...
+        ~~
Unexpected token 'PS' in expression or statement.
    + FullyQualifiedErrorId : UnexpectedToken
```

**Root cause.** The prompt (`(venv) PS C:\...>`) was copied along with the command. PowerShell parsed `PS` as an unexpected token.

**Mitigation.** Pasted only the executable line:

```powershell
python -m uvicorn src.main:app --host 127.0.0.1 --port 8000
```

**Prevention.** Runbook and documentation command blocks contain only executable lines, never prompt text.

---

## INC-009: Typed client rejected valid UUID strings from the API

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Contract defect
- **Status:** Resolved (the workaround was later reversed, see below)

**Trigger.** First functional run against the live API.

**Impact.** The API completed the PostgreSQL transaction and returned `201`, but the typed client raised `SchemaValidationError`, so the test failed even though the server behaved correctly:

```text
FAILED tests/functional/test_orders.py::test_order_placement_transactional_integrity
  - src.client.api_client.SchemaValidationError: Payload validation failed: 1 validation error for UserResponse
user_id
  Input should be an instance of UUID [type=is_instance_of, input_value='93d8f3a8-1977-4b5c-b5ad-c67f5887011e', input_type=str]
```

**Root cause.** The response models typed ID fields as `UUID`. On the wire, UUIDs are JSON strings. The client validated the parsed JSON with strict type checking, which does not accept a `str` for a `UUID` field, so a perfectly valid ID was rejected with `is_instance_of`.

**Mitigation at the time.** Widened the ID fields on `UserResponse` and `OrderResponse` to `UUID | str`.

**Why that was the wrong fix.** It made the test green by weakening the contract. `UUID | str` accepts any string as an ID, so malformed IDs passed model validation and failed later inside the database driver. That is the direct cause of one of the five 500s in [INC-020](#inc-020-invalid-input-returned-http-500). The right fix was to keep the strict `UUID` type and validate wire payloads in a mode that accepts JSON strings (default validation mode, or validating the raw JSON string).

**Reversal.** In INC-020 the request models and `OrderResponse` went back to plain `UUID` under default validation, and the full suite passes. `UserResponse.user_id` still carries the union, which is tracked in [Open items](#open-items).

**Prevention.** Never loosen a contract type to make a test pass (Rule 6). Contract behavior is verified against real wire payloads, which the functional tests do against the live API.

---

## INC-010: Tests used database-client methods that did not exist

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Test defect
- **Status:** Resolved

**Trigger.** First run of `test_orders.py` after INC-009 was fixed.

**Impact.** Both functional tests crashed during verification and fixture teardown, and test rows were left behind in the database:

```text
FAILED test_order_placement_transactional_integrity - AttributeError: 'DatabaseClient' object has no attribute 'fetch_one'
FAILED test_insufficient_funds_state_rollback       - AttributeError: 'DatabaseClient' object has no attribute 'fetch_one'
ERROR  test_order_placement_transactional_integrity - AttributeError: 'DatabaseClient' object has no attribute 'execute'
E   AttributeError: 'dict' object has no attribute 'model_dump'
```

**Root cause.** Two interface mismatches between the tests and the code they called:

1. **Wrong argument type.** Fixtures passed `req.model_dump()` (a dict) to `api_client.post()`, which expects a Pydantic model and calls `.model_dump()` itself.
2. **Methods that never existed.** Tests called generic `db_client.fetch_one()` and `db_client.execute()`. `DatabaseClient` exposes domain-specific methods: `get_user_balance()`, `get_order_by_id()`, `delete_user()`, `delete_order()`.

**Mitigation.**

- Passed typed models straight into `api_client.post(..., payload=req)`.
- Rewrote `tests/functional/test_orders.py` to use the concrete `DatabaseClient` methods:

```python
db_balance = db_client.get_user_balance(user_uuid)
assert db_balance == 60.00

for oid in created_order_ids:
    db_client.delete_order(oid)
for uid in created_user_ids:
    db_client.delete_user(uid)
```

Teardown deletes orders before users to satisfy the foreign key.

**Prevention.** Tests only call the typed, domain-specific client methods. A static type checker would have caught both mismatches before any test ran; it is not configured yet and is tracked in [Open items](#open-items).

---

## INC-011: DatabaseClient defaulted to port 5432 and reached the host's PostgreSQL

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Configuration defect
- **Status:** Resolved

**Trigger.** Test fixtures created `DatabaseClient()` with no arguments while `DB_PORT=5439` was set for the Dockerized database.

**Impact.** The suite crashed during fixture setup:

```text
psycopg2.OperationalError: password authentication failed
```

The connection went to `localhost:5432` instead of the container on `5439`.

**Root cause.** The constructor signature carried a hardcoded `port: int = 5432`. A default in the signature wins over an environment lookup, so `DB_PORT` was never read and the client connected to whatever owned 5432 on the host. That matches [INC-006](#inc-006-host-port-collision-on-postgresql-ports-5432-and-5433): a real PostgreSQL server was already running on that port, which is why this surfaced as an authentication error (a server answered) and not a refused connection.

**Mitigation.** Signature defaults are `None`, and the value is resolved from the environment with a single project-wide fallback:

```python
self.port = int(port or os.getenv("DB_PORT", "5439"))
```

**Prevention.** No standard ports in signatures. This failure was loud only by luck: a wrong default that connects to a real server and happens to accept the credentials would have silently tested the wrong database (Rule 8).

---

## INC-012: State-reset helper never committed and leaked dirty test state

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Test defect
- **Status:** Resolved

**Trigger.** Consecutive runs of the chaos suite.

**Impact.** `reset_product_stock()` in test teardown did not persist. The next run started with `stock = 0`, so the race-condition assertions were non-deterministic.

**Root cause.** An early version ran its `UPDATE` through the `get_cursor()` helper, which borrows a pooled connection but never commits. The connection went back to the pool mid-transaction and the pool rolled it back, so the reset silently disappeared.

**Mitigation.** Mutations go through `get_connection()` with an explicit commit:

```python
def reset_product_stock(self, product_id: str, stock: int = 1) -> None:
    with self.get_connection() as conn:
        with conn.cursor() as cursor:
            cursor.execute(
                "UPDATE products SET stock = %s WHERE product_id = %s;",
                (stock, str(product_id)),
            )
        conn.commit()
```

**Prevention.** Convention: `get_cursor()` is for reads, and every mutating method (`delete_order`, `delete_user`, `reset_product_stock`) uses `get_connection()` and commits explicitly. All mutating methods were audited. This is a convention, not something the code enforces.

---

## INC-013: Chaos test hit a foreign-key violation and the API returned 500

- **Date:** 2026-10-05
- **Severity:** Medium
- **Type:** Test defect + latent system defect
- **Status:** Test fixed in this entry, API behavior fixed in [INC-020](#inc-020-invalid-input-returned-http-500)

**Trigger.** First run of the concurrency test.

**Impact.** All 10 concurrent requests failed, so no locking behavior was verified:

```text
AssertionError: Expected exactly one 201, got: [500, 500, 500, ...]
```

**Root cause.** The test sent a hardcoded `user_id` (`b1eebc99-9c0b-4ef8-bb6d-6bb9bd380a22`) that was never inserted into `users`. `orders.user_id` is a foreign key, so every insert raised `orders_user_id_fkey` and aborted its transaction. The API did not handle the exception and returned 500.

**Mitigation.** The test now owns its prerequisite data through a `chaos_user` fixture: a unique UUID per test, a matching row in `users` with a $1000 wallet, and stock reset to 1. Teardown deletes the user's orders first and the user second, then restores stock.

**What this fix missed.** Seeding the user made the test pass, but it left the product bug in place: an unknown user produced a 500 where a 404 was the correct answer. That stayed in the API until INC-020. The test was wrong, and so was the API, and fixing only the first hid the second.

**Prevention.** Fixtures create and clean up every row a test depends on. When a test fails with a 500, ask what the API *should* have returned before editing the test (Rule 7).

---

## INC-014: Concurrent purchases oversold inventory

- **Date:** 2026-10-05
- **Severity:** **Critical** (data integrity, financial exposure)
- **Type:** System defect
- **Status:** Resolved

**Trigger.** The chaos suite, written to attack exactly this. `tests/chaos/test_race_conditions.py::test_concurrent_purchases_prevent_overselling` fires 10 simultaneous purchases at a product with `stock = 1`.

**Impact.** In the original run, more than one request returned `201 Created` and stock went below zero. In a real system that is double-selling and unbacked fulfillment.

**Root cause.** The endpoint did a plain `SELECT stock` followed by an `UPDATE` under PostgreSQL's default `READ COMMITTED` isolation. Nothing locked the row between the check and the write, so concurrent transactions all read `stock = 1` and all passed the check. Because the update is relative (`stock = stock - 1`), later updates applied on top of the already-committed value and drove it negative.

**Mitigation.** The read takes a row lock inside the same transaction as the write:

```python
cur.execute(
    "SELECT stock, price FROM products WHERE product_id = %s FOR UPDATE;",
    (request.product_id,),
)
```

Competing transactions wait for the lock, then see `stock = 0` and receive a clean `409 Conflict`. The schema also enforces `CHECK (stock >= 0)` in `init.sql`. That constraint alone would only have turned silent oversell into 500 errors for the losers. The lock is what makes the losing requests fail cleanly.

**Prevention.**

- The regression test asserts exactly one `201`, nine `409`s, and a final stock of 0.
- A serialized baseline test (`test_serialized_purchases_baseline`) asserts the same 201-then-409 sequence without concurrency, so a logic failure and a concurrency failure are distinguishable.

---

## INC-015: HTTP client refused to send a malformed Authorization header

- **Date:** 2026-10-05
- **Severity:** Low
- **Type:** Test defect
- **Status:** Resolved

**Trigger.** A parametrized boundary test sent `Authorization: Bearer ` (with a trailing space) to `/api/v1/secure/data`.

**Impact.** The test crashed on the client side before any request left the machine, so the API's 401 handling was never exercised:

```text
httpx.LocalProtocolError: Illegal header value b'Bearer '
```

**Root cause.** The HTTP/1.1 implementation underneath `httpx` validates header values locally and rejects ones with leading or trailing whitespace.

**Mitigation.** Test inputs are now legal on the wire but invalid as credentials: no header at all, `Bearer`, `Bearer null`, `Bearer malformed.token.signature`, and `Basic dXNlcjpwYXNz`. The expired-token case was later split into its own test.

**Prevention.** Application-level validation tests use wire-legal inputs. Sending a literally malformed HTTP header would need a raw socket and is out of scope. One consequence: the API's `Empty token` branch (a header of exactly `Bearer ` followed by nothing) cannot be reached through `httpx`, so that branch is covered by reading the code, not by a test.

---

## INC-016: Allure report deploy failed with HTTP 403

- **Date:** 2026-10-08
- **Severity:** Medium
- **Type:** CI/CD
- **Status:** Resolved

**Trigger.** A push to `main` with all 20 tests passing.

**Impact.** The test job was green but the report deploy failed, and `gh-pages` was never created. The live report link in the README had nothing to serve.

```text
remote: Permission to dannyc7765/transactional-api-engine.git denied to github-actions[bot].
fatal: unable to access 'https://github.com/dannyc7765/transactional-api-engine.git/': The requested URL returned error: 403
```

**Root cause.** The workflow's `GITHUB_TOKEN` did not have write access to repository contents, so the push to `gh-pages` was rejected.

**Mitigation.**

1. Granted write access in `.github/workflows/api-tests.yml`:

```yaml
permissions:
  contents: write
```

2. Replaced the third-party report action with the Allure CLI installed directly in the runner (Java 17 plus the release tarball), so report generation no longer depends on an opaque action. The final push to `gh-pages` still uses `peaceiris/actions-gh-pages`.

**Prevention.** The deploy step runs with `if: always()`, so a failing test run still publishes its report. The permission is currently granted to the whole workflow rather than the deploy job alone; narrowing it is in [Open items](#open-items).

---

## INC-017: GitHub Pages served the README instead of the Allure report

- **Date:** 2026-10-08
- **Severity:** Low
- **Type:** CI/CD configuration
- **Status:** Resolved

**Trigger.** Opening `https://dannyc7765.github.io/transactional-api-engine/` after the first successful deploy.

**Impact.** The page rendered the repository README as a plain page, not the interactive Allure dashboard.

**Root cause.** The Pages source was set to the `main` branch. GitHub built `main` (rendering the README) while the report lived on `gh-pages`.

**Mitigation.** Set the Pages source to branch `gh-pages`, folder `/ (root)`, in the repository settings. A `.nojekyll` marker is also present on `gh-pages` so Pages serves the files as-is. The deploy action writes one by default, so committing it by hand is redundant.

**Prevention.** After the first deploy of any Pages site, open the published URL and confirm it shows the report before linking it from the README.

---

## INC-018: Git line-ending warnings on Windows

- **Date:** 2026-10-08
- **Severity:** Low
- **Type:** Tooling
- **Status:** Resolved

**Trigger.** Editing the workflow YAML on Windows.

**Impact.** Repeated warnings and the risk of CRLF line endings reaching Linux containers and runners:

```text
warning: in the working copy of '.github/workflows/api-tests.yml', LF will be replaced by CRLF the next time Git touches it
```

The committed files are LF, so no CRLF reached the repository.

**Root cause.** Git for Windows defaults to `core.autocrlf=true`, which converts LF to CRLF in the working tree and warns about it.

**Mitigation.** A repository-level `.gitattributes` pins line endings to LF on every platform:

```gitattributes
* text=auto eol=lf
```

Existing files were renormalized with `git add --renormalize .`.

**Prevention.** Line-ending policy lives in the repository, not in each developer's global Git config.

---

## INC-019: Order endpoint accepted zero and negative prices

- **Date:** 2026-10-10
- **Severity:** **Critical** (financial integrity)
- **Type:** System defect + test gap
- **Status:** Resolved, with residual risk (see below)

**Trigger.** Code review of `POST /orders` during a hardening pass, performed while the original 20-test suite was fully green.

**Evidence.** Regression tests were written first (commit `49b1a8d`) and run against the *unfixed* API (7 failed, 1 passed). `negative_price` and `zero_price` both returned `201 Created` where `422` was expected:

```text
FAILED test_order_rejects_invalid_amounts_and_never_changes_balance[negative_price] - assert 201 == 422
FAILED test_order_rejects_invalid_amounts_and_never_changes_balance[zero_price]     - assert 201 == 422
```

**Impact.**

- **Zero price:** free orders were accepted.
- **Negative price:** the order total becomes negative, so the `balance < total` funds check can never fail, and `balance - total` *increases* the wallet. Derived from the code path; the regression test asserts rejection and an unchanged balance.
- Orders with a negative `total_amount` were persisted, because the column had no constraint.

**Root cause.** Four layers:

1. **Trust boundary.** The price in the order came from the client.
2. **Weak input model.** `price: float` and `quantity: int` had no bounds, and IDs were typed `UUID | str` (the INC-009 workaround).
3. **Float money.** Balance arithmetic was done with Python floats in application code, while the database column is `NUMERIC(12,2)`.
4. **Test gap, and the real lesson.** The data factory only produced valid values (price 5 to 250, quantity 1 to 10), and no test sent a boundary or hostile value. 20 green tests measured the happy path and nothing else.

**Mitigation** (commit `67b5722`, "fix: validate order amounts, use Decimal money, pooled connections, map errors to proper status codes"):

- `OrderCreateRequest`: `price: Decimal = Field(gt=0, max_digits=12, decimal_places=2)`, `quantity: int = Field(gt=0, le=1000)`, `user_id: UUID`.
- Totals computed with `Decimal` and quantized to cents.
- The balance update is done in SQL (`wallet_balance = wallet_balance - %s`) under the existing `SELECT ... FOR UPDATE` row lock, not read, modified, and written back in Python.

**Regression tests** (`tests/functional/test_order_validation.py`): `test_order_rejects_invalid_amounts_and_never_changes_balance`, parametrized over negative price, zero price, zero quantity, and negative quantity. Each asserts the status code *and* that the database balance is unchanged.

**Prevention.**

- Every defect gets a failing test before the fix, and the commit history shows red then green.
- Boundary and hostile inputs are part of the standard test matrix for any money-moving endpoint.

**Residual risk.** `POST /orders` still accepts a client-supplied price, so any *positive* price is honored. The correct fix is server-side pricing from the `products` table. See [Open items](#open-items).

---

## INC-020: Invalid input returned HTTP 500

- **Date:** 2026-10-10
- **Severity:** High
- **Type:** System defect + test gap
- **Status:** Resolved

**Trigger.** Same hardening pass as INC-019, probing classes of invalid input beyond price.

**Evidence.** Against the unfixed API, five cases returned `500 Internal Server Error` where a 4xx was the correct contract:

| Input | Expected | Actual |
|-------|----------|--------|
| `quantity = 0` | 422 | 500 |
| `quantity = -1` | 422 | 500 |
| Duplicate username | 409 | 500 |
| Purchase by unknown user | 404 | 500 |
| `user_id = "not-a-uuid"` | 422 | 500 |

**Impact.**

- Expected client errors were indistinguishable from server outages, which would inflate any error-rate alert.
- The purchase endpoint returned `str(exception)` as the response body, which exposes database internals (constraint and column names) to callers.
- Connection handling was inconsistent: two endpoints opened a fresh `psycopg2.connect()` per request and used `with conn:` (which commits or rolls back but does not close), relying on garbage collection to release connections. A third closed explicitly.

**Root cause.** The database constraints were acting as the validation layer, with no exception mapping on top of them. The `UUID | str` unions introduced in INC-009 accepted arbitrary strings, so malformed IDs reached the driver and failed there.

**Mitigation** (same commit, `67b5722`):

- Strict models: plain `UUID` for IDs (reversing the INC-009 widening), bounded `quantity`, `Decimal` money (see INC-019).
- `UniqueViolation` mapped to `409`. Unknown user and product mapped to `404`.
- Raw exception text removed from responses.
- Per-request connections replaced by one `ThreadedConnectionPool` created in the app lifespan, accessed through a single `db_conn()` context manager that commits on success, rolls back on any error, and always returns the connection to the pool.

**Regression tests** (`tests/functional/test_order_validation.py`): `test_duplicate_username_returns_409`, `test_purchase_by_unknown_user_returns_404_and_keeps_stock`, `test_purchase_with_non_uuid_user_id_returns_422`, plus the zero and negative quantity cases from INC-019. The post-fix run is 28 passed.

**Prevention.**

- Negative-path tests assert the *specific* status code and that no state changed, not just "not 200".
- Error responses are part of the API contract and are tested as such.

---

## INC-021: Expired-token test passed for the wrong reason

- **Date:** 2026-10-10
- **Severity:** Medium
- **Type:** Test defect (false positive)
- **Status:** Resolved

**Trigger.** The default JWT signing secret in `src/main.py` was changed during the hardening pass, while the expired-token test still signed its token with the old hardcoded secret.

**Impact.** The test stayed green for the wrong reason. The API rejected the token because its *signature* no longer matched, not because it had *expired*, so the suite would still have passed with expiry checking removed entirely. Separately, no test anywhere proved that a valid token is accepted. Every auth test was a rejection test with no positive control.

**Root cause.**

1. The secret lived in two places (an API default and a constant in the test file), so changing one silently changed what the test measured.
2. The test had no control. "Expired token returns 401" cannot be told apart from any other reason for a 401.

**Mitigation** (commit `f2ef417`, "test: prove expiry and signature handling with a valid-token control; require JWT_SECRET from env"):

- `JWT_SECRET` is required from the environment (`os.environ["JWT_SECRET"]`, so a missing value fails at startup), and `docker-compose.yml` passes the same value to the API and the test-runner.
- A `make_token` fixture signs tokens with that shared secret.
- `test_expired_token_rejected_while_valid_one_passes` signs two tokens with the same secret and claims, and only expiry differs. Valid gets `200`, expired gets `401`, so the `401` can only come from expiry.
- Added `test_token_signed_with_wrong_secret_rejected`, `test_alg_none_token_rejected`, and `tests/functional/test_auth.py::test_valid_token_returns_data_and_subject`, which asserts the response body and the `sub` claim.

**Evidence.** The API log for the control test shows the two outcomes side by side:

```text
GET /api/v1/secure/data HTTP/1.1" 200 OK            (valid token)
GET /api/v1/secure/data HTTP/1.1" 401 Unauthorized  (expired token, same secret)
```

**Prevention.** Every negative test gets a positive control that differs in exactly one variable (Rule 9). Configuration that two components must agree on is read from one source.

---

## INC-022: Purchase endpoint never charged the wallet

- **Date:** 2026-10-11
- **Severity:** High
- **Type:** System defect + test gap
- **Status:** Resolved

**Trigger.** Auditing the README's claims against the code. The README promised protection against "negative ledger states and duplicate deductions", but `POST /api/v1/orders/purchase` never touched the wallet.

**Evidence.** Regression tests were written first (commit `4a48d9e`) and run against the unfixed API: 3 failed, 1 passed.

```text
FAILED test_concurrent_purchases_by_different_users_charge_exactly_one - assert [100.0, 100.0, ...] == [90.0, 100.0, ...]
FAILED test_purchase_charges_wallet_and_decrements_stock              - assert 100.0 == 90.0
FAILED test_purchase_with_insufficient_funds_changes_nothing          - assert 201 == 400
================ 3 failed, 1 passed ================
```

The one pass was the control: `test_concurrent_orders_never_overdraw_wallet` against `POST /orders`. That endpoint's row lock was already correct, and this was the first test to prove it.

**Impact.** Any user, including one with a $5 wallet, could "buy" a $10 item for free. Balances never changed and there was no insufficient-funds path.

**Root cause.** The handler checked and decremented stock but never read or updated `users.wallet_balance`. The existing race test used a single user and only inspected stock, so it could not notice. The README's claims were broader than the tests behind them.

**Mitigation** (commit `ccff5a4`, "fix: purchase charges wallet atomically with stock decrement and order insert"). One transaction, in this order:

1. Lock the user row with `FOR UPDATE`, or `404` if the user is missing.
2. Lock the product row with `FOR UPDATE`, then `404` if missing, `409` if out of stock, `400` if the wallet cannot cover the price.
3. Debit the wallet, decrement stock, and insert the order. If any step fails, none of them happen.

Locks are always taken in the order user, then product, so concurrent requests cannot deadlock each other.

**Regression tests.**

- `tests/functional/test_purchase_wallet.py`: a purchase charges the wallet and decrements stock, and an underfunded purchase changes nothing.
- `tests/chaos/test_wallet_concurrency.py::test_concurrent_purchases_by_different_users_charge_exactly_one`: 8 users race for 1 item, exactly one is charged, seven are not, and stock ends at 0.

Post-fix full run: 35 passed.

**Prevention.** Each documentation claim maps to a named test, and an unbacked claim gets a test or gets deleted (Rule 10). Purchase tests assert both the money and the stock.

---

## INC-023: Secret scanner flagged expired test JWTs in published Allure data

- **Date:** 2026-10-11
- **Severity:** Low
- **Type:** Security hygiene
- **Status:** Resolved

**Trigger.** The first full-history secret scan of this repository with gitleaks.

**Impact.** 12 findings, all from the `jwt` rule, across two commits (`7018a15` and `0a37af5`, six each). Every one was in Allure report data and none in application code: four in `data/test-cases/*.json`, and two each in `data/behaviors.json`, `data/suites.json`, `data/packages.json`, and `data/timeline.json`.

**Root cause.** An early version of the expired-token test passed the generated token as a parametrize value, so the token became part of the test ID. Allure writes test names and parameters into its report JSON, and the CI deploy commits that report to `gh-pages`, so each deploy put tokens into git history.

**Triage.** The claims of every flagged token were decoded without printing the token itself:

```text
Commit  Sub  Expires (UTC)
7018a15 test 2026-10-08 19:40:49   (x6)
0a37af5 test 2026-10-08 19:25:42   (x6)
```

All 12 were the deliberately expired test tokens (`sub=test`, expiry in the past), signed with a throwaway default secret that no longer exists in the code ([INC-021](#inc-021-expired-token-test-passed-for-the-wrong-reason)). An expired token is rejected whatever its signature, and the API now requires `JWT_SECRET` from the environment, so none of these can authenticate.

**Mitigation.**

- History was not rewritten. There was no live credential, and rewriting would change the commit hashes this log cites.
- The token was already out of the test ID: INC-021 moved the expired-token case into its own test that builds the token inside the test body, so new reports no longer carry it.
- Added `.gitleaks.toml`, which keeps the default rules and allowlists exactly one case: the `jwt` rule on those five Allure report data paths. A first version covering only `data/test-cases` still left 8 findings. Grouping the scan output by file found the other four paths, and the allowlist was widened to match.
- Added a CI job that scans the full history with gitleaks and `--redact`, so a new real secret fails the build.

**Prevention.** Anything a test framework derives from its inputs (test IDs, parameters, report data) is a published artifact. Never build those from credentials or tokens (Rule 11).

---

## INC-024: CI metadata steps failed on root-owned test results

- **Date:** 2026-10-11
- **Severity:** Low
- **Type:** CI/CD
- **Status:** Resolved

**Trigger.** Adding Allure environment metadata and trend-history steps to the workflow (PR #3).

**Impact.** The `test` job went red even though all 35 tests passed, and the Pages deploy was skipped:

```text
allure-results/environment.properties: Permission denied
cp: cannot create directory 'allure-results/history': Permission denied
```

**Root cause.** The `allure-results` directory is written by the test-runner container as root through a bind mount, so the runner's own user could not write into it. An existing `chmod -R 777` workaround sat inside the later report-generation step, after the two new steps had already run.

**Triage.** The first suspicion was a flaky test. The step log ruled that out: "Run Test Suite via Docker Compose" was green, and only the two new steps failed.

**Mitigation.** Added a step directly after the test run, before any step that writes into the folder:

```yaml
- name: Take ownership of test results
  if: always()
  run: sudo chown -R "$(id -u):$(id -g)" allure-results
```

**Prevention.** File ownership is not assumed across a container boundary (Rule 12). The older `chmod -R 777` is now redundant and tracked in [Open items](#open-items).

---

## Design notes

The reasoning behind the fixes, in the form it usually comes up in review.

- **Pessimistic vs optimistic locking.** `SELECT ... FOR UPDATE` serializes writers on the contested row. For a scarce item with many simultaneous buyers ([INC-014](#inc-014-concurrent-purchases-oversold-inventory)), optimistic version checks would mostly fail and retry, so the lock is cheaper and gives losing requests a deterministic `409`.
- **Isolation level.** Under the default `READ COMMITTED`, two transactions can read the same row state unless one takes a lock, which is exactly the INC-014 race. A targeted row lock fixes it without moving the whole system to `SERIALIZABLE`.
- **Lock ordering.** The purchase endpoint always takes the user row lock before the product row lock ([INC-022](#inc-022-purchase-endpoint-never-charged-the-wallet)). Requests from the same user serialize on the user row, requests from different users contend only on the product row, and no code path takes the locks in the opposite order, so there is no lock cycle.
- **Contract strictness.** Unknown fields fail validation on the order models ([INC-003](#inc-003-contract-tests-failing-on-pydantic-v2-defaults-and-brittle-assertions)) so schema drift is caught at the boundary. Extending that to the remaining models is an open item.

## Operational rules

These rules came out of the incidents above.

1. **Deterministic test isolation.** A unit or contract test must not require a running service (database, API, queue). If it fails when the services are down, it is an integration test and is tagged accordingly. A connection attempt to a deliberately closed local port, used to test client error handling, is deterministic and does not break this rule.
2. **Dual verification.** A state-changing operation is never verified by its HTTP status alone. The test also queries the database directly, and a rejection test asserts the database is unchanged.
3. **Schema drift: zero tolerance.** Unexpected fields, changed casing, or type conversions must fail at the schema boundary, before application logic runs.
4. **Red before green.** Every defect gets a failing regression test first, so the test is proven capable of failing before the fix makes it pass. The commit history shows the failing test, then the fix.
5. **Hostile data belongs in the matrix.** Test data generators and parametrized cases must include invalid and boundary values, not only valid ones. A suite that only sends valid input measures the happy path (INC-019).
6. **Fix the cause, not the symptom.** Do not loosen a contract to turn a test green. Widening `UUID` to `UUID | str` in INC-009 hid a client-validation problem and created INC-020.
7. **A test fix must not hide a product defect.** When a test fails with a 500, decide what the API *should* have returned before editing the test. Seeding the missing user in INC-013 fixed the test and left the API's 500 for an unknown user until INC-020.
8. **Defaults must fail loudly.** A wrong default that connects to a real server is worse than one that errors. Configuration comes from one place (INC-011).
9. **Every negative test needs a positive control.** Pair a rejection test with an acceptance test that differs in exactly one variable. Otherwise a 401 or 400 could come from any cause (INC-021).
10. **Documentation claims are test-backed.** Every behavior the README promises maps to a named test. An unbacked claim gets a test or gets deleted (INC-022).
11. **Published artifacts must not contain credentials.** Test IDs, parameters, and report data are committed and served publicly, so they are never derived from tokens or secrets (INC-023).
12. **Never assume file ownership across a container boundary.** Fix ownership explicitly before any host-side step writes into a directory a container created (INC-024).
13. **Log incidents when they happen.** Every blocking issue, environment collision, or test defect gets an entry here with root cause and permanent remediation.

## Open items

Known gaps, listed so they are decisions and not surprises.

- **Client-supplied price on `POST /orders`.** Validated to be positive but not verified against `products`. Fix: look the price up server-side.
- **No database CHECK on `orders.total_amount`.** The application now rejects negative totals, but the schema would still accept one. Fix: `CHECK (total_amount >= 0)`.
- **No idempotency keys.** A retried order request creates a second order.
- **In-process rate limiter.** State lives in one process, so it is only correct with a single worker. A shared store (for example Redis) is required to scale out.
- **`UserResponse.user_id` is still `UUID | str`.** Tighten it to `UUID` now that the INC-009 workaround is no longer needed.
- **Host database port is hardcoded** as `5439:5432` in `docker-compose.yml`. Parameterize it as `${DB_PORT:-5439}:5432`.
- **No static analysis.** No `mypy`/`pyright` or `ruff` is configured, so interface mismatches like INC-010 are caught at test runtime instead of before it.
- **No fault-injection check on dual verification.** The database assertions have not been proven to fail when the database misbehaves (for example a trigger that silently suppresses an update).
- **Test-only secrets are committed in `docker-compose.yml`.** The database password and `JWT_SECRET` are acceptable for a hermetic test harness. A deployed service would inject them from a secret store.
- **`extra="forbid"` is only on the order models.** `UserCreateRequest`, `UserResponse`, `PurchaseRequest`, and `ProductResponse` still ignore unknown fields.
- **`contents: write` is granted to the whole workflow.** It should be scoped to the deploy job only.
- **Old Allure report data on `gh-pages` still contains the expired test tokens.** They are allowlisted in `.gitleaks.toml`, not removed from history.
- **Redundant `chmod -R 777` in the workflow.** The `chown` step from INC-024 supersedes it, so the older step can be removed.
