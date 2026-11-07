# OwnershipGraph AI architecture

React/Vite → authenticated Flask REST API → SQLAlchemy/PostgreSQL (system of record).
Neo4j is an optional graph projection keyed by SQL entity and relationship IDs.
The demo uses SQLite and NetworkX with the same calculation service. All seeded
records and their evidence source are explicitly synthetic.

The API owns validation, authorization, transactions, audit records and exports.
LangGraph runs seven typed, validated processing stages: entity intelligence,
ownership, network analytics, experimental ML, deterministic risk scoring,
recommendations and reporting. Human review is a separate persisted decision;
automation cannot approve a report. A disconnected LLM uses evidence templates.
An explicitly enabled Responses API adapter selects only existing fact IDs under
a strict schema; the server supplies all displayed sentences and citations.

Ownership traverses active economic OWNS/SHAREHOLDER_OF edges, multiplies each
path and sums person interests only when data has no cycles, duplicate owner/target
records, overallocated share registers or missing percentages. Otherwise path
estimates are shown with aggregation withheld. Control rights remain separate.
Depth limits and incomplete registers propagate uncertainty. An illustrative
configurable threshold identifies candidates, not a legal UBO determination.

Risk uses bounded features and versioned configurable weights. Unconnected
screening and jurisdiction references are unavailable, never negative matches.
No jurisdiction risk is inferred from nationality. The score is a review-priority
indicator and not a probability or accusation. ML is exploratory Isolation Forest
only unless independently validated labels become available.

Deployment: nginx serves React and proxies /api to Gunicorn; PostgreSQL stores
records; Neo4j holds the graph projection. TLS terminates at a trusted reverse
proxy. Secrets are environment-only. No public deployment is configured here.
