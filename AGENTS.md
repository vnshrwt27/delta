# editor-backend

FastAPI collaborative document editor backend (early stage).

## Quick start

```bash
# run dev server (hot-reload enabled)
uvicorn app.main:app --reload

# or via run.py
python run.py
```

## Structure

```
app/
  main.py           # FastAPI app instantiation (no routers wired yet)
  core/
    config.py       # pydantic-settings, reads from .env
    database.py     # SQLAlchemy engine + session + Base
    security.py     # OAuth2 stubs (incomplete)
  models/
    users.py        # User model (SQLAlchemy)
    document.py     # Document + DocumentPermission models
  schemas/
    user.py         # UserCreate, UserRead, Token (Pydantic)
  routes/
    __init__.py     # empty — no routes implemented
```

## Gotchas

- **`pyproject.toml` venv path mismatch**: `[tool.pyright]` has `venv = "venv"` but the actual virtualenv is `.venv`. Fix the config or create a symlink before running pyright.
- `.env` is gitignored. Create one with `database_url`, `secret_key`, etc. (see `app/core/config.py` for defaults).
- No routes are wired into `app/main.py` yet — any new router must be added there.
- No tests, CI, or linter config exist; no pytest config either.

## Stack

- FastAPI, SQLAlchemy 2.x, psycopg2-binary, PostgreSQL, pydantic-settings
- Python >=3.11

## Roadmap — OT-based Google Docs clone

### Architecture

```
Client A ──WebSocket──┐                ┌──WebSocket── Client B
                      │                │
                      ▼                ▼
              ┌──────────────────────────────┐
              │  FastAPI App                  │
              │  ┌────────────────────────┐   │
              │  │ ConnectionManager      │   │  per-document rooms
              │  │ (WebSocket registry)   │   │
              │  ├────────────────────────┤   │
              │  │ OTCore                 │   │  transform(op_a, op_b)
              │  │ (pure logic)           │   │  apply(doc, op)
              │  ├────────────────────────┤   │
              │  │ REST routes            │   │  CRUD docs, ops
              │  │ WS routes              │   │  real-time sync
              │  ├────────────────────────┤   │
              │  │ SQLAlchemy             │   │  PostgreSQL
              │  └────────────────────────┘   │
              └──────────────────────────────┘
```

### Phase 1 — OT Core Engine (`app/core/ot.py`)

Pure functions, no I/O. Server is authoritative.

**Operations** (JSON wire format):
```json
{"type": "insert", "pos": 5, "text": "hello", "user_id": "1", "doc_version": 1}
{"type": "delete", "pos": 3, "length": 2, "user_id": "2", "doc_version": 1}
{"type": "update", "pos": 7, "text": "X", "length": 1, "user_id": "1", "doc_version": 2}
```

**Transform rules** `T(op_a, op_b)`:

| op_a | op_b | Effect on op_a |
|------|------|----------------|
| insert(i) | insert(j) | i > j → i += len(b.text) |
| insert(i) | delete(j) | i > j → i -= min(b.len, i - j) |
| delete(i) | insert(j) | i >= j → i += len(b.text) |
| delete(i) | delete(j) | i >= j → i -= min(b.len, i - j) |

**Server-side flow per incoming op:**
1. Load ops applied since `client_version` from DB
2. Transform incoming op against each in order
3. Apply transformed op to document content
4. Increment `document.version`
5. Persist op + new document state
6. Broadcast transformed op to other room clients

### Phase 2 — Data Layer

**`Document` model** — add `version: Mapped[int]` field.

**New `Operation` model** (`app/models/operation.py`):
- document_id, user_id, op_type, pos, text, length, version (server-assigned sequential)

**New schemas** (`app/schemas/operation.py`):
- `OperationCreate`, `OperationRead`, `DocumentContent` (content + version)

### Phase 3 — REST API

| Method | Path | Purpose |
|--------|------|---------|
| POST | `/documents` | Create doc |
| GET | `/documents` | List user's docs |
| GET | `/documents/{id}` | Get content + version |
| PATCH | `/documents/{id}` | Rename title |
| DELETE | `/documents/{id}` | Delete doc + ops |
| POST | `/documents/{id}/operations` | Submit op (transform + apply + broadcast) |
| GET | `/documents/{id}/operations?since={v}` | Pull ops since version v |

All routes behind JWT auth (implement in `app/core/security.py`).

### Phase 4 — WebSocket Layer

**New `ConnectionManager`** (`app/core/ws_manager.py`):
```python
class ConnectionManager:
    rooms: dict[int, set[WebSocket]]  # document_id -> connections
    async def join(doc_id, ws)
    async def leave(doc_id, ws)
    async def broadcast(doc_id, message, exclude)
```

**Endpoint**: `WS /ws/documents/{doc_id}?token={jwt}`

**Messages**:

| Direction | type | Purpose |
|-----------|------|---------|
| C→S | `op` | Submit operation + client_version |
| C→S | `cursor` | Broadcast cursor/selection |
| C→S | `ping` | Keepalive |
| S→C | `op_ack` | Confirm op with server_version |
| S→C | `op_broadcast` | Remote user's op |
| S→C | `cursor` | Remote user's cursor |
| S→C | `snapshot` | Full content + version (on reconnect) |
| S→C | `pong` | Keepalive response |

**Reconnect flow**: Client sends `client_version` on join → server computes missed ops, transforms them, sends `snapshot`.

### Phase 5 — Wiring

- `app/main.py`: Use `lifespan` context manager for `Base.metadata.create_all()`; include all routers
- Router prefixes: REST at `/api/v1`, WS at `/ws`

### Phase 6 — Client responsibilities

1. Fetch doc via REST, open WS
2. Apply ops locally immediately (optimistic); queue unacknowledged ops
3. Send each op with `client_version`
4. Transform pending local ops against incoming remote ops before applying
5. On `op_ack`, remove from pending; advance `client_version`
6. On reconnect, send last version, apply snapshot + missed ops

### Key design decisions

| Decision | Rationale |
|----------|-----------|
| Server-authoritative OT | Server transforms, persists, then broadcasts. No two-phase commit. |
| Linear version per doc | Simpler than vector clocks. Server serializes all ops. |
| Per-op persistence | Enables reconnect/resync by computing missed ops. |
| REST + WS split | CRUD over REST; real-time edits over WS. |
| No CRDT | OT is simpler for single-server. CRDT (Yjs) better for P2P/offline. |

### Future

- Undo/redo (store inverse ops per user, transform against concurrent op)
- Cursor & selection broadcasting
- Rate limiting per user
- Redis pub/sub for multi-process scaling
