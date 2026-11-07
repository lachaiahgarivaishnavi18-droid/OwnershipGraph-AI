# Vercel deployment

The repository root is the Vercel project root. The Flask framework preset loads
index.py. The build compiles the React application into public/ for Vercel's CDN;
frontend routes rewrite to index.html, while /api remains on Flask. This follows
the [Vercel Flask deployment contract](https://vercel.com/docs/frameworks/backend/flask).

Required environment variables (Production and Preview as appropriate):

- DATABASE_URL or POSTGRES_URL: dedicated managed PostgreSQL connection URL.
- JWT_SECRET_KEY: a stable random secret of at least 32 characters.
- DEMO_MODE=true for the synthetic demonstration.
- DEMO_PASSWORD: at least 8 characters, used only for initial synthetic accounts.
- VERCEL_INITIALIZE_DATABASE=true for the first deployment to a new database.
- LLM_ENABLED=false unless an external provider is intentionally configured.

Connect a PostgreSQL integration in Vercel Storage, or supply an existing dedicated
database through Vercel's environment settings. No database credential belongs in
source control. The cloud entrypoint rejects SQLite and missing/unstable JWT keys.
Do not point this application's migrations at another application's database.

Once authenticated with the Vercel CLI:

```sh
vercel link
vercel env add JWT_SECRET_KEY production
vercel env add DEMO_MODE production
vercel env add DEMO_PASSWORD production
vercel env add VERCEL_INITIALIZE_DATABASE production
vercel --prod
```

The database integration normally supplies POSTGRES_URL automatically; otherwise
add DATABASE_URL as a secret through the dashboard or CLI. After the first
successful migration/seed, remove VERCEL_INITIALIZE_DATABASE or set it to false.
Existing users' passwords are not changed by subsequent seed executions.

Verify the deployed /api/health, sign-in, investigation run, reviewer decision and
PDF/CSV export. The standard cloud bundle omits the optional experimental ML
artifact and large scientific libraries; the workflow reports ML as unavailable.
The local application retains its full synthetic ML capability. Neo4j and LLM
connections remain optional. SQL/NetworkX and deterministic summaries work without
them. Configure a shared rate-limit backend before relying on global rate limits
across Vercel instances.

Local packaging check (with frontend dependencies already installed):

```sh
python scripts/build_vercel.py --skip-install
```

Deployed and verified on 7 November 2026:
https://ownershipgraph-ai.vercel.app

The checkout is linked to resume-project3/ownershipgraph-ai. A dedicated Neon
resource, ownershipgraph-db, is connected on its free_v3 plan. Database credentials
are supplied by the integration, and app secrets are stored in Production settings.
The root requirements file is intentionally flattened because the Vercel parser
rejected a nested -r include. Built public/ assets are included in deployment uploads
so Vercel discovers and serves the frontend; the remote build refreshes them.

Live checks passed: frontend, direct navigation to /investigations, API health,
analyst/reviewer sign-in, 12 synthetic entities, all seven agent stages, a saved
assessment, PDF/CSV downloads, independent review approval and case closure.
Verification used a separate closed synthetic case; the original two demo cases
remain available. Optional ML remains explicitly unavailable in the lean cloud
bundle. Local cloud-configuration/import tests bring the backend suite to 29 tests.

Account-creation update: /register now provides public Analyst signup with username,
email and confirmed password (8–128 characters). ALLOW_SELF_REGISTRATION is enabled
for this demonstration. Signup cannot create privileged roles. The requested demo
password was applied to the three synthetic demo accounts through a one-time build
operation, which is disabled after completion. Personal account passwords are not
reset by this operation. Verification passed 33 backend and 9 frontend tests plus
live registration, duplicate rejection, login, role access and logout checks.
