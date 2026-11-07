# Local verification record - 7 November 2026

Environment: Windows, Python 3.15.2 project virtual environment, Node 24.22.1.
The Docker baseline uses Python 3.12 and Node 22. PostgreSQL and Neo4j were not
available locally; Docker is not installed on this host.

Verified:

- Backend unit/integration suite: 24 tests covering authentication, revocation,
  role and assignment access, entity validation/search, economic multipath
  ownership, missing/conflicting registers, cycles, temporal filtering, depth,
  analytics, score arithmetic, imports, seven LangGraph stages, independent
  reviewer decisions, report snapshots, PDF/CSV, model inference, optional LLM
  success/rejection/timeout/fallback, settings and retention holds/purging.
- Frontend interaction suite: 6 tests covering login, API-backed search,
  Cytoscape initialization, case creation, missing risk indicators and exports.
- Vite production build succeeds with separate graph, chart and vendor chunks.
- Alembic baseline and snapshot migration applied to the local SQLite database;
  current revision is 002. pip check reports no broken dependencies.
- Reproducible synthetic Isolation Forest trained with 480 training rows and
  120 held-out rows. Descriptive novelty statistics saved in model_metadata.json.
- Live browser: analyst sign-in, dashboard from database records, running the
  seven-stage investigation, generated evidence summary, graph search/fit,
  person-path highlighting. No browser console errors observed in these checks.
- Responsive layout inspected at a 390px viewport and desktop default; temporary
  viewport override restored.
- A three-page synthetic PDF was generated, text checked for all 15 numbered
  sections, rendered with Poppler and visually reviewed. Includes deterministic
  path diagram, contributions, references, limitations and reviewer status.

Limits:

- PostgreSQL, Neo4j live synchronization/traversal and container startup require
  integration verification with those services. Neo4j failure uses the SQL graph;
  a configured successful query is cross-checked against deterministic SQL paths.
- External LLM requests were stubbed in tests. No paid API request or real key
  was used. Missing credentials, refused/invalid output and timeouts fall back.
- The pinned LangGraph release produces asyncio deprecation warnings on Python
  3.15; tests pass. Review dependency upgrades before moving to Python 3.16.
- No real screening data, labeled crime outcomes, operational ML validation,
  penetration test, TLS deployment or financial-services accreditation is claimed.
- The application implements synchronous local workflow stages; graph connection
  and LLM requests have explicit timeouts, traversal has depth/step budgets.
  Durable background jobs, parallel transactional stage execution and cancellation
  are future deployment work, not demonstrated capabilities.
- Initial schema metadata is frozen in migrations/schema_001.py; subsequent
  schema changes require independent Alembic revisions.

`scripts/verify_demo.py` regenerates the isolated synthetic PDF. `pytest.ini`
keeps test temporary files inside the workspace for restricted Windows sandboxes.
