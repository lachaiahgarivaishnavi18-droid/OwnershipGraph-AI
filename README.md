# OwnershipGraph AI

[Live application](https://ownershipgraph-ai.vercel.app/) ·
[Create account](https://ownershipgraph-ai.vercel.app/register)

An academic beneficial ownership and investigation application: React/Vite,
Flask, SQLAlchemy, NetworkX, Cytoscape, LangGraph and optional Neo4j/PostgreSQL.
All bundled people, companies and relationships are **synthetic**. Scores indicate
review priority, never criminal activity. No real screening feed is connected.

## Local setup

Use Python 3.12+ and Node 22+ with npm (or pnpm). Python 3.12 is the Docker baseline.
The local demo needs neither database containers nor an LLM key.

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
$env:DEMO_MODE='true'
$env:DEMO_PASSWORD='choose-a-demo-password-of-12-or-more-characters'
python backend/manage.py init
python backend/manage.py seed
python backend/run.py
```

In a second terminal:

```powershell
cd frontend
npm install
npm run dev
```

Open http://127.0.0.1:5173. Log in as `analyst`, `reviewer`, or `admin` using the
password supplied to the seed command. The seeder is idempotent; changing the
environment variable does not change an existing account password. No passwords
are committed. `scripts/start-demo.ps1` wraps these steps on Windows.

The sign-in page also offers **Create account**. Registration creates an Analyst
account and signs the user in. Passwords require at least 8 characters; the
requested example `demo@2026` is accepted. Public signup cannot assign Reviewer
or Administrator access. Use ALLOW_SELF_REGISTRATION=false to disable it.

On macOS/Linux: use `source .venv/bin/activate` and `export KEY=value` instead.
Copy `.env.example` for reference; environment variables must be exported by your
shell or container (the application does not implicitly read a dotenv file).

## Demonstrate a complete investigation

1. Log in as analyst. Search for the synthetic Aster Maritime Group.
2. Open the entity profile and graph. Inspect a node or edge for source references.
3. Open Beneficial ownership. Review Elena/Marcus path estimates and the unknown
   trust percentage. Combined ownership is deliberately withheld in this example.
4. Import `data/sample/ownership.csv` after validation to add a complete simple
   share register for synthetic Atlas Research; create an investigation for Atlas
   to demonstrate valid aggregated UBO candidates.
5. Open Case workspace, choose Aster or create a case, and Run investigation.
   Seven LangGraph stages save outputs, findings, indicators and execution logs.
6. Add an analyst note, assign the reviewer, and Submit for review.
7. Log out; log in as reviewer. Approve, reject, or request changes with a reason.
8. Download the PDF or CSV snapshot from the case or Reports & exports.
9. Log in as admin to inspect audit logs, add users or configure weights.

Model absence is a supported state. To train the **synthetic-only exploratory**
Isolation Forest, run `python backend/train_model.py`, then rerun an investigation.
Its novelty score is not a crime probability. No real-world predictive performance
is claimed. Generated joblib artifacts must only come from trusted operators.

## Tests and build

```powershell
python -m pytest backend/tests -q
cd frontend
npm test
npm run build
```

Backend tests cover access, revocation, entity validation, temporal/multipath
ownership, cycles, incomplete/conflicting registers, analytics, score arithmetic,
imports, orchestration, reviewer decisions and both export formats. Frontend tests
cover login, search, graph initialization, creation, risk and download interactions.

## PostgreSQL and Neo4j

Export DATABASE_URL=`postgresql+psycopg://user:password@localhost/ownershipgraph`.
Run `alembic upgrade head` from the repo root before starting the backend.
SQLite uses the same ORM schema. Do not run init/create_all against an existing
managed production schema. Migration 001 establishes the baseline; future schema
changes require new immutable Alembic revisions.

Export NEO4J_URI, NEO4J_USER and NEO4J_PASSWORD. Run
`python backend/manage.py sync-graph` or POST `/api/graph/sync` as admin to project
stable SQL IDs into Neo4j. Cypher constraints, traversal and analysis queries live
in `neo4j/`. SQL is the source of truth and calculations use NetworkX in demo mode.
Synchronization is explicit; re-sync after imports or corrections.

## Docker

For Vercel, see [the prepared deployment configuration](docs/vercel_deployment.md).
The Vercel project requires a managed PostgreSQL connection and stable cloud secrets.
Local SQLite files are not used by the cloud entrypoint.

Set POSTGRES_PASSWORD (URL-safe), NEO4J_PASSWORD, JWT_SECRET_KEY (32+ random
characters), DEMO_PASSWORD and DEMO_MODE in an untracked `.env` for Compose.

```sh
docker compose up -d postgres neo4j
docker compose run --rm backend python manage.py init
docker compose run --rm backend python manage.py seed
docker compose up -d --build backend frontend
```

Open http://localhost:8080. The Compose ports bind to loopback. For production,
set DEMO_MODE=false, migrate using Alembic, run `bootstrap-admin` interactively,
and do not seed synthetic accounts. Serve through a trusted TLS reverse proxy,
use a shared rate-limit store, managed database backups, centralized audit export,
restricted network access and a secrets manager. Credentials, operational
monitoring, retention enforcement, privacy/legal review and independent security
testing are deployment responsibilities; this academic application is not a
certified financial-crime screening product.

## Documentation and limits

- [Architecture](docs/architecture.md), [database](docs/database_schema.md),
  [API contract](docs/api_documentation.md), [implementation plan](docs/implementation_plan.md).
- [Methodology](docs/methodology.md), [user manual](docs/user_manual.md),
  [verification record](docs/verification.md).
- Unconnected sanctions, PEP, adverse-media, jurisdiction and change-history
  indicators remain unavailable. Low observed scores do not establish low risk.
- The assistant defaults to deterministic retrieval. An optional extractive LLM
  adapter selects existing evidence statements only; see [configuration](docs/llm_adapter.md).
- No labeled real financial-crime dataset exists here; supervised model comparison,
  SHAP and calibrated probability claims are intentionally unavailable.
- Neo4j/PostgreSQL deployments require live integration testing in your environment.
- Graph paths are bounded; cycles and conflicting registers require reconciliation.
- Retention days records policy. `python backend/retention.py` previews closed
  cases eligible for content removal; `--hold 1 2` excludes legal holds. An
  operator can use `--apply` after reviewing the preview. It preserves case
  metadata, source records and audit history. No automatic deletion is scheduled.
