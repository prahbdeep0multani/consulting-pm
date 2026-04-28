# Consulting PM

> Production-grade, multi-tenant project management platform for consulting companies.
> Built with Python 3.12 + FastAPI, deployed on Kubernetes.

---

## Table of Contents

- [Overview](#overview)
- [Architecture](#architecture)
- [Services](#services)
- [Shared Library](#shared-library)
- [Data Models](#data-models)
- [API Reference](#api-reference)
- [Inter-Service Events](#inter-service-events)
- [Security Design](#security-design)
- [Multi-Tenancy](#multi-tenancy)
- [Getting Started (Local Dev)](#getting-started-local-dev)
- [Running Tests](#running-tests)
- [Database Migrations](#database-migrations)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Helm Chart](#helm-chart)
- [CI/CD](#cicd)
- [Project Structure](#project-structure)
- [Environment Variables](#environment-variables)
- [Design Decisions](#design-decisions)

---

## Overview

Consulting PM is a backend-only API platform that covers the four core operational domains of a consulting firm:

| Domain | Features |
|---|---|
| **Projects & Tasks** | Clients, projects, milestones, tasks (with subtasks), comments, file attachments |
| **Time Tracking & Billing** | Time entries with approval workflow, invoice generation, billing rate resolution |
| **Resource Planning** | Team allocations with over-allocation detection, leave requests, capacity calendar |
| **Notifications** | In-app and email notifications, per-user quiet hours, preference management |

Every entity in the system is **tenant-scoped**: a single deployment serves multiple independent consulting firms, with strict row-level data isolation enforced at the database query layer — not in application code.

---

## Architecture

```
Internet
    │
    ▼
┌─────────────┐
│   Gateway   │  :8000  JWT validation · rate limiting · reverse proxy
└──────┬──────┘
       │  (internal HTTP + X-Tenant-ID / X-User-ID headers)
       ├──── Auth          :8001  Identity, RBAC, JWT issuance
       ├──── Projects      :8002  Clients, projects, tasks, attachments
       ├──── Timelog       :8003  Time entries, approval workflow
       ├──── Billing       :8004  Rates, invoices, PDF generation
       ├──── Resources     :8005  Allocations, leave requests, capacity
       └──── Notifications :8006  In-app + email notifications

Each service owns its own PostgreSQL database.
All services share a Redis instance (cache + Redis Streams event bus).
File storage (attachments, invoice PDFs) lives in MinIO (S3-compatible).
Async background work runs via Celery workers + beat scheduler.
```

### Technology Stack

| Layer | Choice |
|---|---|
| Language | Python 3.12 |
| Web framework | FastAPI 0.115 |
| Data validation | Pydantic v2 |
| ORM | SQLAlchemy 2.0 async |
| DB driver | asyncpg |
| Migrations | Alembic |
| Database | PostgreSQL 16 (one per service) |
| Cache / sessions | Redis 7 |
| Event bus | Redis Streams |
| Object storage | MinIO (S3-compatible) |
| Async workers | Celery + Redis broker |
| Containerisation | Docker (multi-stage builds) |
| Orchestration | Kubernetes + Kustomize overlays |
| Package manager | Helm (Bitnami chart dependencies) |
| CI/CD | GitHub Actions |
| Linting | Ruff |
| Type checking | mypy (strict) |

---

## Services

### Gateway `:8000`

The single ingress point for all external traffic. It never touches a database.

**Responsibilities:**
- **JWT validation** — verifies RS256 signature using the public key loaded from disk at startup. No call to the auth service per request.
- **Tenant resolution** — maps the `tenant_id` claim from the JWT to the `X-Tenant-ID` header and injects it into every upstream request.
- **Rate limiting** — sliding window counter per IP and per tenant stored in Redis (`ZADD` + `ZREMRANGEBYSCORE`). Configurable limits per environment.
- **Correlation IDs** — generates a `X-Correlation-ID` UUID on every request and propagates it to all upstreams and the response.
- **Reverse proxy** — forwards the stripped, enriched request to the correct service via `httpx.AsyncClient`.

### Auth `:8001`

Handles identity, credentials, and access control.

**Key features:**
- **RS256 JWT** — access tokens (15 min TTL), refresh tokens (30 day TTL, hashed with SHA-256, stored in DB).
- **Refresh token rotation** — every refresh issues a new token and revokes the old one. Each token belongs to a *family* (UUID). If a revoked token is reused (replay attack), the entire family is invalidated immediately.
- **TOTP/MFA** — optional TOTP second factor per user.
- **RBAC** — permissions stored as `"resource:action"` strings in a JSONB column on roles. Four system roles seeded on tenant creation: `tenant_admin`, `project_manager`, `consultant`, `client_viewer`.
- **Password reset** — token-based flow with time-limited, single-use tokens.
- **Email verification** — optional email verification on registration.
- **Tenant registration** — creates tenant + first admin user atomically; seeds system roles.

### Projects `:8002`

Core project management data.

**Key features:**
- Full CRUD for clients, projects, milestones, tasks, subtasks (self-referential FK), comments, and attachments.
- **Presigned MinIO upload** — two-step file upload: client requests a presigned PUT URL (5 min TTL), uploads directly to MinIO, then confirms via POST. The API performs a HEAD request to MinIO to verify the object exists before writing the attachment record. The API never proxies file bytes.
- **Task position ordering** — integer `position` field with a `move` endpoint for Kanban-style reordering.
- **Actual hours sync** — `actual_hours` on tasks is updated by consuming `time_entry.approved` events from Redis Streams.
- Publishes events on: `project.created`, `project.status_changed`, `task.created`, `task.assigned`, `task.status_changed`, `milestone.completed`.

### Timelog `:8003`

Time tracking with structured approval workflow.

**Key features:**
- **State machine** — `draft → submitted → approved | rejected`. Each state transition is validated; skipping states returns `409 Conflict`.
- **Timer support** — `start-timer` / `stop-timer` endpoints calculate `duration_minutes` from `started_at` / `ended_at`.
- **Bulk submission** — `POST /time-entries/bulk` accepts multiple entries in a single request.
- **Approval audit trail** — every `submit / approve / reject` action creates a `TimeEntryApproval` record with actor, timestamp, and notes.
- **Reports** — aggregated summaries by project, user, date range, and billable status (requires `project_manager` role).
- Publishes events on: `time_entry.submitted`, `time_entry.approved`, `time_entry.rejected`.

### Billing `:8004`

Financial layer for invoicing and rate management.

**Key features:**
- **Rate resolution** — finds the most specific applicable billing rate for a `(user, project, date)` tuple. Specificity order: `user > role > project > global`. Rates have `effective_from` / `effective_to` date ranges.
- **Invoice generation from timelog** — calls the timelog service for all approved, un-billed time entries in a date range and creates line items automatically.
- **Invoice lifecycle** — `draft → sent → partially_paid | paid | overdue | void`.
- **Overdue detection** — a Celery beat task runs daily at 08:00 UTC and marks `sent` invoices past their `due_date` as `overdue`.
- **PDF generation** — WeasyPrint renders invoices to PDF; the file is stored in MinIO and served via a presigned GET URL.
- **Auto-numbering** — invoice numbers are generated in format `INV-{YEAR}-{NNNN}`, scoped per tenant per year.
- Publishes events on: `invoice.created`, `invoice.sent`, `invoice.paid`, `invoice.overdue`.

### Resources `:8005`

Team capacity and availability management.

**Key features:**
- **Allocation CRUD** — assigns users to projects with a percentage of their working capacity (`allocation_pct`, 0–100).
- **Over-allocation guard** — before creating or updating an allocation, the service sums existing `allocation_pct` for the user in the overlapping date range. If the total would exceed 100%, returns `409 Conflict`.
- **Leave requests** — `pending → approved | rejected | cancelled`. Approved leave is factored into capacity queries.
- **Capacity calendar** — `GET /calendar` returns a per-user, per-day availability breakdown.
- Publishes events on: `allocation.created`, `leave_request.approved`.

### Notifications `:8006`

In-app and email notification delivery.

**Key features:**
- **In-app notifications** — stored in the database and served via REST (list, mark read, mark all read, delete, unread count).
- **Email delivery** — Celery worker sends transactional email via SMTP. Uses MailHog in local dev.
- **Event-driven** — consumes events from all other service streams and maps event types to notification templates.
- **Per-user preferences** — `email_enabled`, `in_app_enabled`, per-notification-type granular toggles in a JSONB column, quiet hours (`quiet_hours_start`, `quiet_hours_end`, `timezone`).
- **Preference auto-creation** — preferences record is created with defaults on first access.

---

## Shared Library

The `shared/` package is installed as an editable dependency in every service. It contains the primitives that must behave identically across all services.

```
shared/
├── core/
│   ├── models/
│   │   └── base.py          SQLAlchemy declarative base + PrimaryKeyMixin (UUID PK)
│   │                        + TenantMixin + TimestampMixin + SoftDeleteMixin
│   ├── middleware/
│   │   ├── tenant.py        TenantMiddleware — reads X-Tenant-ID, sets ContextVar
│   │   ├── jwt_middleware.py JWTAuthMiddleware — validates RS256, sets request.state
│   │   └── correlation.py   CorrelationIdMiddleware — ensures X-Correlation-ID
│   ├── security/
│   │   └── jwt.py           JWTHandler — RS256 encode/decode, token hashing
│   ├── exceptions/
│   │   ├── base.py          AppError, NotFoundError, ForbiddenError, ConflictError, ...
│   │   └── handlers.py      FastAPI exception handlers → structured JSON responses
│   ├── health/
│   │   └── factory.py       create_health_router(name, checks) → /health + /ready
│   ├── cache/
│   │   └── redis.py         Async Redis wrapper with get/set/delete/incr/expire
│   └── schemas/
│       ├── base.py          BaseSchema (Pydantic model_config from_attributes=True)
│       └── pagination.py    Cursor-based pagination schema
└── events/
    ├── schemas/
    │   ├── base.py          BaseEvent envelope (event_id, event_type, tenant_id, ...)
    │   ├── auth_events.py   TenantCreated, UserRegistered, UserDeactivated
    │   ├── project_events.py ProjectCreated, TaskAssigned, MilestoneCompleted, ...
    │   ├── timelog_events.py TimeEntrySubmitted, TimeEntryApproved, ...
    │   ├── billing_events.py InvoiceCreated, InvoiceSent, InvoicePaid, ...
    │   └── resource_events.py AllocationCreated, LeaveRequestApproved
    ├── publisher.py         XADD to named Redis Streams
    └── consumer.py          XREADGROUP consumer groups + XAUTOCLAIM (60s stale threshold)
```

### Base Model Mixins

```python
class PrimaryKeyMixin:
    id: Mapped[uuid.UUID] = mapped_column(default=uuid.uuid4, primary_key=True)

class TenantMixin:
    tenant_id: Mapped[uuid.UUID]  # enforced by TenantMiddleware on every query

class TimestampMixin:
    created_at: Mapped[datetime]  # server default now()
    updated_at: Mapped[datetime]  # updated on every write

class SoftDeleteMixin:
    deleted_at: Mapped[datetime | None]  # None = visible, set = logically deleted
```

All list queries in repositories automatically append `.where(Model.deleted_at.is_(None))`. Admin endpoints can explicitly pass `include_deleted=True`.

---

## Data Models

### Auth service DB

| Table | Key columns |
|---|---|
| `tenants` | `id`, `slug` (unique), `name`, `plan`, `is_active`, `settings` (JSONB), `max_users` |
| `users` | `id`, `tenant_id`, `email` (unique per tenant), `password_hash`, `full_name`, `is_active`, `is_verified`, `mfa_secret` |
| `roles` | `id`, `tenant_id`, `name` (unique per tenant), `is_system`, `permissions` (JSONB `["resource:action"]`) |
| `user_roles` | `user_id`, `role_id` (composite PK), `assigned_by` |
| `refresh_tokens` | `id`, `user_id`, `token_hash` (SHA-256), `family` (UUID), `expires_at`, `revoked_at`, `ip_address`, `user_agent` |
| `password_reset_tokens` | `id`, `user_id`, `token_hash`, `expires_at`, `used_at` |

### Projects service DB

| Table | Key columns |
|---|---|
| `clients` | `id`, `tenant_id`, `name`, `industry`, `contact_*`, `billing_address`, `currency` |
| `projects` | `id`, `tenant_id`, `client_id`, `name`, `type` (fixed_price / time_and_materials), `status`, `budget_amount`, `manager_user_id` |
| `milestones` | `id`, `tenant_id`, `project_id`, `name`, `due_date`, `status`, `completion_pct` |
| `tasks` | `id`, `tenant_id`, `project_id`, `milestone_id`, `parent_task_id`, `title`, `status`, `priority`, `assignee_user_id`, `estimated_hours`, `actual_hours`, `labels` (TEXT[]) |
| `comments` | `id`, `tenant_id`, `task_id`, `author_user_id`, `body`, `edited_at` |
| `attachments` | `id`, `tenant_id`, `task_id`, `project_id`, `storage_key` (unique), `storage_bucket`, `checksum_sha256`, `is_confirmed` |

### Timelog service DB

| Table | Key columns |
|---|---|
| `time_entries` | `id`, `tenant_id`, `user_id`, `project_id`, `task_id`, `date`, `started_at`, `ended_at`, `duration_minutes` (authoritative), `is_billable`, `status` (draft/submitted/approved/rejected), `invoice_id` |
| `time_entry_approvals` | `id`, `tenant_id`, `time_entry_id`, `approver_user_id`, `action`, `notes` |

### Billing service DB

| Table | Key columns |
|---|---|
| `billing_rates` | `id`, `tenant_id`, `type` (user/role/project/global), `target_id`, `hourly_rate`, `effective_from`, `effective_to` |
| `invoices` | `id`, `tenant_id`, `client_id`, `project_id`, `invoice_number` (unique per tenant+year), `status`, `subtotal`, `tax_rate`, `tax_amount`, `total_amount` |
| `invoice_line_items` | `id`, `invoice_id`, `time_entry_id`, `description`, `quantity` (hours), `unit_price`, `amount` |

### Resources service DB

| Table | Key columns |
|---|---|
| `allocations` | `id`, `tenant_id`, `user_id`, `project_id`, `allocation_pct` (0–100 CHECK), `start_date`, `end_date` |
| `leave_requests` | `id`, `tenant_id`, `user_id`, `type` (annual/sick/unpaid/…), `start_date`, `end_date`, `total_days`, `status`, `approver_user_id` |

### Notifications service DB

| Table | Key columns |
|---|---|
| `notifications` | `id`, `tenant_id`, `recipient_user_id`, `type` (e.g. `task.assigned`), `title`, `body`, `payload` (JSONB), `channel`, `is_read`, `read_at` |
| `notification_preferences` | `id`, `tenant_id`, `user_id` (unique per tenant), `email_enabled`, `in_app_enabled`, `preferences` (JSONB), `quiet_hours_start`, `quiet_hours_end`, `timezone` |

---

## API Reference

All requests (except auth login/register/refresh) require:

```
Authorization: Bearer <access_token>
```

Tenant context is derived from the `tenant_id` claim inside the JWT — clients never send a separate tenant header.

### Gateway `:8000`

```
GET  /health
GET  /ready
ANY  /api/{service}/{path:path}    → proxied to the target service
```

### Auth `:8001`

```
POST   /tenants                         Register new tenant + first admin
GET    /tenants/me                      Get current tenant info
PATCH  /tenants/me                      Update tenant settings
DELETE /tenants/me                      Deactivate tenant

POST   /auth/login                      → { access_token, refresh_token }
POST   /auth/refresh                    Rotate refresh token
POST   /auth/logout                     Revoke current refresh token
POST   /auth/logout-all                 Revoke all sessions
POST   /auth/forgot-password
POST   /auth/reset-password
POST   /auth/verify-email
POST   /auth/mfa/enable
POST   /auth/mfa/verify
POST   /auth/mfa/disable

GET    /users                           List users [tenant_admin]
POST   /users/invite                    Invite user [tenant_admin]
GET    /users/me                        Current user profile
PATCH  /users/me
POST   /users/me/change-password
GET    /users/{id}
PATCH  /users/{id}                      [tenant_admin]
DELETE /users/{id}                      [tenant_admin]

GET    /roles                           List roles
POST   /roles                           Create role [tenant_admin]
GET    /roles/{id}
PATCH  /roles/{id}                      [tenant_admin]
DELETE /roles/{id}                      [tenant_admin]
POST   /users/{id}/roles/{role_id}      Assign role [tenant_admin]
DELETE /users/{id}/roles/{role_id}      Remove role [tenant_admin]
```

### Projects `:8002`

```
GET    /clients
POST   /clients
GET    /clients/{id}
PATCH  /clients/{id}
DELETE /clients/{id}
GET    /clients/{id}/projects

GET    /projects
POST   /projects
GET    /projects/{id}
PATCH  /projects/{id}
DELETE /projects/{id}
GET    /projects/{id}/budget            Budget burn: planned vs. actual
GET    /projects/{id}/members

GET    /projects/{id}/milestones
POST   /projects/{id}/milestones
GET    /projects/{id}/milestones/{id}
PATCH  /projects/{id}/milestones/{id}
DELETE /projects/{id}/milestones/{id}

GET    /projects/{id}/tasks
POST   /projects/{id}/tasks
GET    /tasks/{id}
PATCH  /tasks/{id}
DELETE /tasks/{id}
POST   /tasks/{id}/move                 Reorder (position)
GET    /tasks/{id}/subtasks
POST   /tasks/{id}/subtasks

GET    /tasks/{id}/comments
POST   /tasks/{id}/comments
PATCH  /comments/{id}
DELETE /comments/{id}

POST   /attachments/upload              Returns presigned MinIO PUT URL
POST   /attachments                     Confirm upload (HEAD verify)
GET    /attachments/{id}
DELETE /attachments/{id}
GET    /tasks/{id}/attachments
GET    /projects/{id}/attachments
```

### Timelog `:8003`

```
GET    /time-entries
POST   /time-entries
GET    /time-entries/{id}
PATCH  /time-entries/{id}
DELETE /time-entries/{id}
POST   /time-entries/{id}/start-timer
POST   /time-entries/{id}/stop-timer
POST   /time-entries/bulk
GET    /time-entries/summary

POST   /time-entries/{id}/submit
POST   /time-entries/{id}/approve       [project_manager]
POST   /time-entries/{id}/reject        [project_manager]

GET    /approvals/pending               [project_manager]
GET    /approvals/history

GET    /reports/by-project             [project_manager]
GET    /reports/by-user                [project_manager]
GET    /reports/by-date                [project_manager]
GET    /reports/billable-summary       [project_manager]
```

### Billing `:8004`

```
GET    /billing-rates
POST   /billing-rates
GET    /billing-rates/{id}
PATCH  /billing-rates/{id}
DELETE /billing-rates/{id}
GET    /billing-rates/resolve?user_id=&project_id=&date=

GET    /invoices
POST   /invoices
GET    /invoices/{id}
PATCH  /invoices/{id}
DELETE /invoices/{id}
POST   /invoices/{id}/generate-from-timelog
POST   /invoices/{id}/send
POST   /invoices/{id}/record-payment
POST   /invoices/{id}/void
GET    /invoices/{id}/pdf               → presigned MinIO GET URL

POST   /invoices/{id}/line-items
PATCH  /invoices/{id}/line-items/{item_id}
DELETE /invoices/{id}/line-items/{item_id}

GET    /projects/{id}/burn-rate
GET    /projects/{id}/budget-forecast
GET    /dashboard/revenue-summary      [tenant_admin]
```

### Resources `:8005`

```
GET    /allocations
POST   /allocations
GET    /allocations/{id}
PATCH  /allocations/{id}
DELETE /allocations/{id}
GET    /allocations/conflicts

GET    /users/{id}/capacity
GET    /projects/{id}/team
GET    /calendar
GET    /users/{id}/availability

GET    /leave-requests
POST   /leave-requests
GET    /leave-requests/{id}
PATCH  /leave-requests/{id}
DELETE /leave-requests/{id}
POST   /leave-requests/{id}/approve    [project_manager]
POST   /leave-requests/{id}/reject     [project_manager]
GET    /leave-requests/pending         [project_manager]
```

### Notifications `:8006`

```
GET    /notifications
GET    /notifications/{id}
POST   /notifications/{id}/read
POST   /notifications/read-all
DELETE /notifications/{id}
GET    /notifications/unread-count

GET    /preferences
PUT    /preferences
PATCH  /preferences
```

---

## Inter-Service Events

Services communicate asynchronously via **Redis Streams**. Each service publishes to its own stream and subscribes to streams from other services using consumer groups.

Every event carries a standard envelope:

```json
{
  "event_id": "uuid",
  "event_type": "task.assigned",
  "tenant_id": "uuid",
  "occurred_at": "2024-01-01T12:00:00Z",
  "source_service": "projects",
  "correlation_id": "uuid",
  "schema_version": "1.0",
  "payload": { ... }
}
```

| Stream | Published by | Consumed by | Events |
|---|---|---|---|
| `events:auth` | auth | notifications, resources | `tenant.created`, `user.registered`, `user.deactivated` |
| `events:projects` | projects | billing, resources, notifications | `project.created`, `project.status_changed`, `task.created`, `task.assigned`, `task.status_changed`, `milestone.completed` |
| `events:timelog` | timelog | billing, projects, notifications | `time_entry.submitted`, `time_entry.approved`, `time_entry.rejected` |
| `events:billing` | billing | notifications, timelog | `invoice.created`, `invoice.sent`, `invoice.paid`, `invoice.overdue` |
| `events:resources` | resources | notifications | `allocation.created`, `leave_request.approved` |

Stale messages (unacknowledged for > 60 seconds) are reclaimed via `XAUTOCLAIM` in a background task.

---

## Security Design

### JWT Architecture

```
Client → Gateway → (JWT verified with RS256 public key, no auth service call)
                 → (X-User-ID, X-Tenant-ID, X-User-Roles headers injected)
                 → Upstream service (trusts headers, sets ContextVar)
```

- **Access token** (15 min): signed with RS256 private key. Contains `user_id`, `tenant_id`, `roles`, `permissions[]`.
- **Refresh token** (30 day): raw token returned to client, SHA-256 hash stored in DB alongside a `family` UUID.
- **Rotation**: each use of a refresh token revokes the old record and issues a new one in the same `family`.
- **Reuse detection**: if a revoked token is presented again, the entire `family` is immediately revoked, terminating all active sessions for that user.

### Rate Limiting

The gateway implements a **sliding window** rate limiter per IP and per tenant using Redis sorted sets:

1. `ZADD stream:{ip} {now_ms} {uuid}` — add current request
2. `ZREMRANGEBYSCORE stream:{ip} 0 {window_start_ms}` — remove old entries
3. `ZCARD stream:{ip}` — count requests in window

Requests exceeding the limit receive `429 Too Many Requests`.

### RBAC

Permissions are stored as `"resource:action"` strings (e.g. `"task:write"`, `"invoice:read"`). The wildcard `"*:*"` grants full access (tenant_admin). Permission checks happen in router dependencies.

### File Upload Security

The API never handles file bytes directly. The presigned URL flow ensures:

1. The gateway never becomes a bandwidth bottleneck.
2. File content is verified at rest (SHA-256 checksum) before the attachment record is confirmed.
3. Presigned URLs expire after 5 minutes.

---

## Multi-Tenancy

Tenant isolation is enforced at the **database query layer** using a Python `contextvars.ContextVar`:

```python
# shared/core/models/base.py
_tenant_id_var: ContextVar[uuid.UUID | None] = ContextVar("tenant_id", default=None)

def get_current_tenant_id() -> uuid.UUID:
    tid = _tenant_id_var.get()
    if tid is None:
        raise RuntimeError("Tenant context not set")
    return tid
```

`TenantMiddleware` sets this var from the `X-Tenant-ID` header (injected by the gateway) at the start of every request and clears it afterwards.

Every repository method that queries tenant-scoped data calls `get_current_tenant_id()` in its WHERE clause:

```python
stmt = select(Task).where(
    Task.tenant_id == get_current_tenant_id(),
    Task.id == task_id,
    Task.deleted_at.is_(None),
)
```

This means a bug in a router that forgets to filter by tenant will still be blocked by the repository layer. **No cross-service foreign keys exist** — services store foreign UUIDs as plain columns, ensuring independent schema evolution.

The test suite for every service includes a mandatory tenant isolation test:

```python
async def test_tenant_isolation(client_a, client_b):
    # Create resource in tenant A
    # Authenticate as tenant B
    # Assert 0 results returned — not a 403, just empty
```

---

## Getting Started (Local Dev)

### Prerequisites

- Docker >= 24
- Docker Compose >= 2.20
- `make`
- OpenSSL (for generating JWT keys)

### 1. Clone and configure

```bash
git clone https://github.com/your-org/consulting-pm.git
cd consulting-pm
cp .env.example .env
```

### 2. Generate RSA keys for JWT

```bash
mkdir -p keys
openssl genrsa -out keys/private.pem 2048
openssl rsa -in keys/private.pem -pubout -out keys/public.pem
```

Update `.env` to point `JWT_PRIVATE_KEY_PATH` and `JWT_PUBLIC_KEY_PATH` at these files, or mount them as Docker secrets.

### 3. Start the stack

```bash
make dev-up
```

This builds all service images and starts:

- 6 × PostgreSQL instances (ports 5432–5437)
- Redis (port 6379)
- MinIO (port 9000, console 9001)
- All 7 application services
- Billing worker + Celery beat
- Notifications worker
- MailHog (port 8025) — catches all outbound email
- pgAdmin (port 5050) — database browser
- redis-commander (port 8081) — Redis key browser

### 4. Run migrations

```bash
make migrate
```

### 5. Verify the stack

```bash
# Gateway health
curl http://localhost:8000/health

# Register a tenant
curl -s -X POST http://localhost:8000/api/auth/tenants \
  -H "Content-Type: application/json" \
  -d '{"slug":"acme","name":"ACME Consulting","admin_email":"admin@acme.com","admin_password":"secret123"}'

# Login
curl -s -X POST http://localhost:8000/api/auth/auth/login \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@acme.com","password":"secret123","tenant_slug":"acme"}'
```

### Available Make targets

| Target | Description |
|---|---|
| `make dev-up` | Start all services with hot reload |
| `make dev-down` | Stop all services |
| `make dev-logs` | Tail logs for all services |
| `make migrate` | Run `alembic upgrade head` for all services |
| `make test` | Run full test suite via Docker Compose |
| `make test-local` | Run tests locally (requires local DB/Redis) |
| `make lint` | `ruff check` across all services |
| `make fmt` | `ruff format` across all services |
| `make typecheck` | `mypy` (strict) across all services |
| `make build` | Build all production Docker images |
| `make clean` | Destroy containers, volumes, images |

### Developer Tools

| Tool | URL | Purpose |
|---|---|---|
| OpenAPI (gateway) | http://localhost:8000/docs | Interactive API explorer |
| OpenAPI (auth) | http://localhost:8001/docs | Auth service docs |
| OpenAPI (projects) | http://localhost:8002/docs | Projects service docs |
| OpenAPI (timelog) | http://localhost:8003/docs | Timelog service docs |
| OpenAPI (billing) | http://localhost:8004/docs | Billing service docs |
| OpenAPI (resources) | http://localhost:8005/docs | Resources service docs |
| OpenAPI (notifications) | http://localhost:8006/docs | Notifications service docs |
| MailHog | http://localhost:8025 | Catch-all SMTP inbox |
| pgAdmin | http://localhost:5050 | Database browser |
| redis-commander | http://localhost:8081 | Redis key browser |
| MinIO console | http://localhost:9001 | Object storage browser |

---

## Running Tests

### Full suite (Docker, recommended)

```bash
make test
```

Spins up `docker-compose.test.yml` — an isolated stack with real PostgreSQL, Redis, and MinIO. Runs migrations then pytest across all services with `--cov-fail-under=80`.

### Single service

```bash
cd services/auth
DATABASE_URL=postgresql+asyncpg://auth:auth_pass@localhost:5432/auth_db \
REDIS_URL=redis://localhost:6379/0 \
python -m pytest app/tests/ -v
```

### Coverage report

```bash
pytest services/auth/app/tests/ --cov=services/auth/app --cov-report=html
open htmlcov/index.html
```

---

## Database Migrations

Each service manages its own Alembic migrations independently.

```bash
# Apply all pending migrations (via Docker)
make migrate

# Create a new migration for a specific service
cd services/projects
alembic revision --autogenerate -m "add project tags"

# Apply migrations for a specific service
cd services/projects
DATABASE_URL=postgresql+asyncpg://... alembic upgrade head

# Rollback one step
alembic downgrade -1
```

Migration files are at `services/{name}/alembic/versions/`.

---

## Kubernetes Deployment

### Base manifests

```
k8s/base/
├── namespace.yaml
├── kustomization.yaml
├── infra/
│   ├── redis.yaml            StatefulSet + headless Service
│   ├── minio.yaml            StatefulSet + Service
│   └── resource-quotas.yaml
├── ingress/
│   └── ingress.yaml          nginx-ingress + cert-manager TLS
└── {gateway,auth,projects,timelog,billing,resources,notifications}/
    ├── deployment.yaml
    ├── service.yaml           ClusterIP
    ├── hpa.yaml               CPU 70% / Memory 80% triggers
    ├── configmap.yaml
    ├── pdb.yaml               minAvailable: 1
    └── networkpolicy.yaml     Ingress/Egress rules per service
```

### Deploy with Kustomize

```bash
# Development
kubectl apply -k k8s/overlays/dev/

# Staging
kubectl apply -k k8s/overlays/staging/

# Production
kubectl apply -k k8s/overlays/prod/
```

| Overlay | Replicas | HPA max | PDB minAvailable |
|---|---|---|---|
| dev | 1 | 2 | 0 |
| staging | 2 | 5 | 1 |
| prod | 3 | 15 | 2 |

### Secrets

Secrets are not committed to this repository. Create them before deploying:

```bash
kubectl create secret generic auth-secret \
  --from-literal=database-url="postgresql+asyncpg://..." \
  --from-file=jwt-private-key=keys/private.pem \
  --from-file=jwt-public-key=keys/public.pem \
  -n consulting-pm
```

For production, use [External Secrets Operator](https://external-secrets.io) or Sealed Secrets to pull secrets from a vault.

---

## Helm Chart

The chart at `helm/consulting-pm/` wraps all seven services plus Bitnami dependencies (postgresql × 6, redis, minio).

```bash
# Add Bitnami repo
helm repo add bitnami https://charts.bitnami.com/bitnami
helm dependency update helm/consulting-pm/

# Staging deploy
helm upgrade --install consulting-pm helm/consulting-pm/ \
  --namespace consulting-pm-staging \
  --create-namespace \
  --values helm/consulting-pm/values-staging.yaml \
  --set global.imageRegistry=123456789.dkr.ecr.eu-west-1.amazonaws.com \
  --set auth.image.tag=abc1234 \
  --wait

# Production deploy (auto-rollback on failure)
helm upgrade --install consulting-pm helm/consulting-pm/ \
  --namespace consulting-pm \
  --values helm/consulting-pm/values-prod.yaml \
  --set global.imageRegistry=123456789.dkr.ecr.eu-west-1.amazonaws.com \
  --set auth.image.tag=v1.2.3 \
  --atomic \
  --timeout 15m
```

Key values (see [`values.yaml`](helm/consulting-pm/values.yaml) for the full reference):

```yaml
global:
  imageRegistry: ""        # ECR/GCR registry prefix

auth:
  replicaCount: 2
  image:
    repository: consulting-pm/auth
    tag: latest
  autoscaling:
    enabled: true
    minReplicas: 2
    maxReplicas: 8
    targetCPUUtilizationPercentage: 70

notifications:
  smtp:
    host: smtp.sendgrid.net
    port: 587
    from: noreply@yourcompany.com
```

---

## CI/CD

### CI (`ci.yml`) — triggers on every push and PR

```
detect-changes          Identifies which services changed (dorny/paths-filter)
        │
        ├── lint-and-type-check   Matrix: all services + shared
        │       ruff check · ruff format --check · mypy --strict
        │
        ├── test                  Matrix: auth, projects, timelog, billing, resources, notifications
        │       Real Postgres + Redis + MinIO as job services
        │       alembic upgrade head → pytest --cov --cov-fail-under=80
        │       Coverage uploaded to Codecov
        │
        ├── build-docker          Matrix: all 7 services
        │       docker buildx build --target production (verify only, no push)
        │       GitHub Actions cache scoped per service
        │
        └── security-scan         Matrix: all 7 services
                Trivy scan for CRITICAL + HIGH CVEs
                Results uploaded as SARIF to GitHub Security tab
                Fails CI on any CRITICAL finding
```

### CD (`cd.yml`) — triggers on push to `main` or semver tag

```
push-images             Multi-arch build (linux/amd64 + linux/arm64)
                        OIDC authentication to AWS — no long-lived credentials
                        Push to Amazon ECR: :sha · :latest · :semver tags
        │
        ├── deploy-staging        (on push to main)
        │       helm upgrade --install with values-staging.yaml
        │       Smoke tests: /health + /ready endpoints
        │
        └── deploy-prod           (on tag v*.*.*)
                Requires manual approval (GitHub Environment: production)
                helm upgrade --atomic (auto-rollback on failure, 15 min timeout)
                Smoke tests
                Creates GitHub Release with auto-generated release notes
```

### Required GitHub Secrets

| Secret | Description |
|---|---|
| `AWS_ECR_REGISTRY` | ECR registry URL |
| `AWS_REGION` | AWS region |
| `AWS_DEPLOY_ROLE_ARN` | IAM role ARN for OIDC federation |
| `EKS_CLUSTER_STAGING` | EKS cluster name for staging |
| `EKS_CLUSTER_PROD` | EKS cluster name for production |
| `STAGING_HOST` | Staging API hostname for smoke tests |
| `PROD_HOST` | Production API hostname for smoke tests |

---

## Project Structure

```
consulting-pm/
├── .github/
│   └── workflows/
│       ├── ci.yml                 Lint · test · build · scan
│       ├── cd.yml                 Push images · deploy staging/prod
│       └── dependency-review.yml  Block high-severity dependency additions
├── services/
│   ├── gateway/
│   ├── auth/
│   ├── projects/
│   ├── timelog/
│   ├── billing/
│   ├── resources/
│   └── notifications/
│       ├── Dockerfile             Multi-stage: builder → production → development
│       ├── alembic.ini
│       ├── alembic/
│       │   ├── env.py
│       │   └── versions/
│       └── app/
│           ├── main.py            App factory, lifespan, middleware registration
│           ├── config.py          Pydantic Settings (reads env vars)
│           ├── database.py        Async SQLAlchemy engine + session factory
│           ├── dependencies.py    FastAPI Depends() factories
│           ├── models/            SQLAlchemy ORM models
│           ├── schemas/           Pydantic v2 request/response schemas
│           ├── routers/           APIRouter per resource
│           ├── services/          Business logic (no HTTP, no SQL)
│           ├── repositories/      Data access layer (all SQL lives here)
│           ├── events/            Redis Streams publishers + consumers
│           └── tests/             pytest + conftest
├── shared/                        Installed as editable dep in all services
│   ├── core/
│   └── events/
├── k8s/
│   ├── base/                      Kustomize base manifests
│   └── overlays/
│       ├── dev/
│       ├── staging/
│       └── prod/
├── helm/consulting-pm/            Helm chart with Bitnami dependencies
├── docker-compose.yml             Full local dev stack
├── docker-compose.override.yml    Dev tools (MailHog, pgAdmin, redis-commander)
├── docker-compose.test.yml        CI integration test stack
├── Makefile
├── pyproject.toml                 Root ruff + mypy + pytest config
└── .env.example
```

---

## Environment Variables

Copy `.env.example` to `.env` before running `make dev-up`.

| Variable | Service | Description |
|---|---|---|
| `JWT_PRIVATE_KEY_PATH` | auth, gateway | Path to RS256 private key PEM |
| `JWT_PUBLIC_KEY_PATH` | auth, gateway | Path to RS256 public key PEM |
| `ACCESS_TOKEN_EXPIRE_MINUTES` | auth | Access token TTL (default: 15) |
| `REFRESH_TOKEN_EXPIRE_DAYS` | auth | Refresh token TTL (default: 30) |
| `AUTH_DATABASE_URL` | auth | asyncpg connection string |
| `PROJECTS_DATABASE_URL` | projects | asyncpg connection string |
| `TIMELOG_DATABASE_URL` | timelog | asyncpg connection string |
| `BILLING_DATABASE_URL` | billing | asyncpg connection string |
| `RESOURCES_DATABASE_URL` | resources | asyncpg connection string |
| `NOTIFICATIONS_DATABASE_URL` | notifications | asyncpg connection string |
| `REDIS_URL` | all | Redis connection string |
| `MINIO_ENDPOINT` | projects, billing | MinIO host:port |
| `MINIO_ACCESS_KEY` | projects, billing | MinIO access key |
| `MINIO_SECRET_KEY` | projects, billing | MinIO secret key |
| `MINIO_BUCKET_ATTACHMENTS` | projects | Bucket for file attachments |
| `MINIO_BUCKET_INVOICES` | billing | Bucket for invoice PDFs |
| `MINIO_USE_SSL` | projects, billing | `true` / `false` |
| `SMTP_HOST` | notifications | SMTP server host |
| `SMTP_PORT` | notifications | SMTP server port |
| `SMTP_FROM` | notifications | Sender address |
| `TIMELOG_SERVICE_URL` | billing | Internal URL to timelog service |
| `CORS_ORIGINS` | all | Comma-separated allowed origins |
| `LOG_LEVEL` | all | `DEBUG` / `INFO` / `WARNING` |
| `ENVIRONMENT` | all | `development` / `staging` / `production` |

---

## Design Decisions

**No cross-service foreign keys.**
Each service stores UUIDs from other services as plain columns with no FK constraint. This allows each service to evolve its schema independently, be deployed and migrated separately, and be extracted to its own database without coordination. Referential integrity is maintained via events and lightweight HTTP validation at write time.

**Tenant isolation via ContextVar, not function parameters.**
Passing `tenant_id` as a parameter to every repository method would be easy to forget. Storing it in a `contextvars.ContextVar` means the repository layer always has access to the current tenant without any explicit plumbing — and it's automatically cleared at the end of every request, preventing cross-request leakage even in async contexts.

**Gateway validates JWT without calling auth.**
The gateway loads the RS256 public key once at startup and validates every token locally. This eliminates the auth service as a latency bottleneck and single point of failure for every API call. Token revocation (logout) is handled via the refresh token; the short access token TTL (15 min) keeps the revocation window small.

**Refresh token families for reuse detection.**
A simple `is_revoked` flag detects that a token has been used. Token families detect *replay attacks*: if a rotated (already-used) token is presented again, an attacker has obtained an old token. Revoking the entire family immediately terminates all active sessions for that user, not just the compromised one.

**Presigned URL file upload.**
The API never proxies file bytes. API pod memory usage stays flat regardless of file size. The confirmation step (HEAD request to MinIO) prevents orphaned records for uploads that never completed. Presigned URLs expire after 5 minutes.

**Soft delete on all entities.**
Rather than hard-deleting records, a `deleted_at` timestamp is set. All list queries filter `deleted_at IS NULL` automatically. This preserves audit history, allows recovery from accidental deletes, and keeps financial data (invoices, time entries) consistent with the state at the time of creation.

**Celery beat for scheduled tasks, not cron jobs.**
Running overdue invoice detection as a Celery beat task means it is observable (task results in Redis), restartable on failure, horizontally scalable, and deployable as a standard Kubernetes Deployment — without needing host-level cron configuration or a separate scheduling service.

---

## License

MIT — see [LICENSE](LICENSE).
