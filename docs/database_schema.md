# Relational and graph schema

SQLAlchemy models in backend/app/models.py are the canonical schema. Alembic
migrations create the schema in PostgreSQL or SQLite. Foreign keys constrain
relationships and investigation references; users have unique usernames/emails;
entities have unique external IDs. JSON fields store structured evidence snapshots.

Tables: users, entities, ownership_relationships, evidence_sources,
investigations, risk_assessments, risk_indicators, graph_findings,
agent_execution_logs, analyst_notes, audit_logs, settings, revoked_tokens, reports.
Investigation assignment and review decision timestamps preserve accountability.

Neo4j (:Entity {id, name, type, jurisdiction}) nodes map to SQL entity IDs.
Relationship types are OWNS, SHAREHOLDER_OF, CONTROLS, DIRECTOR_OF,
BENEFICIARY_OF, TRUSTEE_OF, REGISTERED_AT and RELATED_TO. Every edge carries
its SQL id, percentage, validity interval, source ID, confidence and verification.
PERSON/COMPANY/TRUST/PARTNERSHIP/FOUNDATION/ADDRESS/DIRECTOR/JURISDICTION
labels are added alongside Entity. Projection synchronization is explicit and
idempotent. SQL remains authoritative if graph service is unavailable.
