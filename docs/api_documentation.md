# API contract

All /api endpoints except /health and auth/login require Bearer JWT. JSON errors:
{error: string}; validation errors also include details. Lists accept page and
per_page (max 100), return {items,total,page,pages}. IDs are integers.

Auth: POST /auth/login {username,password}, GET /auth/me,
POST /auth/logout, POST /auth/register {username,email,password,role} (admin).
Public analyst signup: POST /auth/signup {username,email,password}; password must
contain 8–128 characters. A role field is rejected. GET /auth/config exposes only
the registration-enabled and demo-mode flags. ALLOW_SELF_REGISTRATION controls
signup (enabled by default in demo mode). Duplicate username/email checks are
case-insensitive. Successful signup returns a JWT and the new analyst profile.
Entities: GET/POST /entities, GET/PUT/DELETE /entities/:id,
GET /entities/search?q=&jurisdiction=&entity_type=&exact=true.
Relationships: GET/POST /relationships; POST is admin/analyst only.
Ownership: GET /ownership/:id[ /direct | /indirect | /ubo | /paths ]; accepts
depth (1–12), threshold (0–100), as_of (ISO date).
Graph: GET /graph/:id[ /analytics | /cycles | /connections ]; POST /graph/sync (admin).
Risk: POST /risk/assess/:id; GET /risk/:id[ /explanation ].
Investigations: GET/POST /investigations, GET/PUT/DELETE /investigations/:id.
Create {title,target_entity_id}; update {status,reviewer_id,decision}.
POST /investigations/:id/notes {note,evidence_references:[]}.
Agents: POST /agents/run/:id; GET /agents/status/:id or /agents/logs/:id.
Assistant: POST /assistant {entity_id,question}; grounded deterministic retrieval.
Dashboard: GET /dashboard/summary, /dashboard/risk-distribution, /dashboard/trends.
Reports: POST /reports/generate/:id {format: pdf|csv}; returns download URL.
GET /reports/:id/download enforces investigation access.
Import: POST /import/entities or /import/ownership multipart file CSV/XLSX,
dry_run=true by default; atomic validation. GET /import/status/:id.
Admin: GET/PUT /settings, GET /users, PUT /users/:id, GET /audit.

Reviewer decisions require assigned reviewer or administrator. Analysts access
their own investigations; reviewer access is assignment-scoped. Admin sees all.
