# Organization Management Service

FastAPI-based multi-tenant org management service using MongoDB. Provides org lifecycle APIs, admin authentication (JWT), and dynamic per-organization collections.

flowchart LR
    subgraph Client
        U[User / Admin]
    end

    subgraph Render ["API Service"]
        direction TB
        API["FastAPI App (app.main)"]
        AUTH["Auth Routes /admin/login"]
        ORG["Org Routes /org/create|get|update"]
        SRV["Services AuthService / OrganizationService"]
    end

    subgraph Sec ["Security Util"]
        JWT["JWT Issuer create_access_token"]
        HASH["Password Hashing (passlib bcrypt)"]
    end

    subgraph Mongo ["MongoDB"]
        MASTER[("Master DB (org_master_db)")]
        ORG_COLL[("Per-Org Collections org_&lt;slug&gt;")]
    end

    %% Connections
    U -->|HTTP| API
    API --> AUTH
    API --> ORG
    AUTH --> SRV
    ORG --> SRV

    SRV -->|hash/verify| HASH
    SRV -->|issue/verify| JWT

    SRV -->|admin_users| MASTER
    SRV -->|organizations| MASTER
    SRV -->|tenant data| ORG_COLL
  
## Quick start

### Common setup
1) **Clone**: `git clone <repo> && cd Organization-Management-Service`
2) **Env vars**: create a `.env` (or set environment variables). Example placeholders — replace with your own values:
  ```env
  MONGO_URI=mongodb://mongo:27017   # your Mongo URI (if running locally change host/port as needed)
  MASTER_DB=org_master_db           # master database name
  JWT_SECRET=change_me              # set a strong secret
  JWT_ALGORITHM=HS256
  ACCESS_TOKEN_EXPIRE_MINUTES=60
  ```

### Option A: Run locally
1) **Prereqs**: Python 3.10+ and MongoDB reachable at `MONGO_URI`.
2) **Install deps** (virtual env recommended):
  ```bash
  python -m pip install -r requirements.txt
  ```
3) **Start API**:
  ```bash
  uvicorn app.main:app --reload
  ```

### Option B: Run with Docker / Docker Compose
**Single container (external Mongo):**
```bash
docker build -t org-mgmt-api .
docker run -d -p 8000:8000 \
  -e MONGO_URI=mongodb://host.docker.internal:27017 \
  -e MASTER_DB=org_master_db \
  -e JWT_SECRET=change_me \
  org-mgmt-api
```

**Compose (API + Mongo):**
Compose reads a `.env` in the project root automatically. You can override values there or via your shell.
```bash
docker compose up -d --build
```
Starts API on `localhost:8000` and Mongo on `localhost:27017` with volume `mongo_data`.

Docker tips (Windows): start Docker Desktop in Linux mode; confirm `docker info` works before running compose.

## API overview

Base URL examples assume `http://127.0.0.1:8000`.

### Health
- `GET /help` → simple status message.
- `GET /ping` → counts organizations in master DB.

### Auth
- `POST /admin/login` — body `{ "email": "...", "password": "..." }` → returns `{ access_token, token_type }` (JWT). No refresh flow; re-login after expiry.

### Organization
- `POST /org/create` — body `{ organization_name, email, password }`.
  - Creates org metadata in master DB, creates collection `org_<slug>`, creates initial admin linked to org.
- `GET /org/get?organization_name=Acme` — returns org metadata (no internal `_id`, includes `owner_email`).
- `PUT /org/update` — body `{ organization_name, email, password }`.
  - Renames org to `organization_name`, authenticating with admin email/password of that org. Migrates collection to new name.
- `PUT /org/update_better` — body `{ current_organization_name, new_organization_name, email, password }`.
  - Explicit current/new names; errors if current missing or new already exists; verifies admin belongs to org; migrates collection.
- `DELETE /org/delete` — auth via `Authorization: Bearer <token>` header (JWT from login). Provide `organization_name` via query or body `{ "organization_name": "..." }`. Drops org collection, deletes admins for that org, removes org record.

### Collections & data model
- **Master DB** (`MASTER_DB`):
  - `organizations`: org metadata (`name` slug, `display_name`, `collection_name`, `owner_admin_id`, `status`, timestamps).
  - `admin_users`: admins with `org_id`, `email`, `password_hash`, `role`, `is_active`.
- **Per-org collections**: created as `org_<slug>` and hold tenant-specific data (currently empty schema; copied during rename operations).

## Testing with examples

Use curl/Postman; ensure JSON bodies and `Content-Type: application/json`.

- Create org:
  ```bash
  curl -X POST http://127.0.0.1:8000/org/create \
    -H "Content-Type: application/json" \
    -d '{"organization_name":"Acme Inc","email":"admin@example.com","password":"Secret123!"}'
  ```
- Login:
  ```bash
  curl -X POST http://127.0.0.1:8000/admin/login \
    -H "Content-Type: application/json" \
    -d '{"email":"admin@example.com","password":"Secret123!"}'
  ```
- Delete org with token:
  ```bash
  curl -X DELETE "http://127.0.0.1:8000/org/delete?organization_name=Acme Inc" \
    -H "Authorization: Bearer <token>"
  ```

## Notes & assumptions
- Email validation uses `EmailStr`; special-use domains (e.g., `.local`) are rejected unless models are relaxed.
- JWT tokens are only issued at login; no refresh/rotation implemented.
- Org names are normalized to lowercase slug with underscores for collection naming; uniqueness enforced on the normalized value.
- Renames migrate data by copying documents to a new collection, then dropping the old one.


## Design notes
- Simple single-DB, per-org collection approach keeps isolation while staying on one Mongo deployment.
- JWT-only auth keeps the flow minimal; tokens embed `sub` (admin) and `org` for authorization checks.
- Org names normalize to lowercase+underscores for safe collection naming and uniqueness.

## Project layout
```
app/
  main.py            # FastAPI app + router wiring
  core/              # config, security (JWT, hashing)
  db/                # Mongo client helpers
  routes/            # FastAPI routers (auth, org)
  services/          # business logic (auth, org)
  models/            # pydantic models and utils
create_admin.py      # helper script to seed a master admin
```
