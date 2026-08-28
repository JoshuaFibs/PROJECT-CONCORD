# Project Concord — ELT Pipeline: Full Setup and Run Guide

This takes you from nothing to a working nightly Postgres-to-BigQuery
pipeline. Skip to Part 3 if you already have a Google Cloud project
with BigQuery enabled.

---

## Part 1 — Load the curated views into your Supabase project

1. Open pgAdmin, connect to your Supabase project (same connection
   you used for the main schema).
2. **Query Tool** → **File → Open** → `005_elt_curated_views.sql`.
3. Click **Execute/Run**.
4. Confirm it worked:
   ```sql
   select table_name from information_schema.views
   where table_schema = 'analytics';
   ```
   You should see all 5 views listed.

---

## Part 2 — Create a dedicated read-only role for the pipeline

This matters: the pipeline should never connect using your admin
credentials, and should never be able to see anything outside the
`analytics` schema — even if the script had a bug, it structurally
couldn't leak raw wallet transactions or KYC data.

In pgAdmin's Query Tool, run:
```sql
create role elt_readonly with login password 'choose-a-strong-password-here';
grant usage on schema analytics to elt_readonly;
grant select on all tables in schema analytics to elt_readonly;
alter default privileges in schema analytics
    grant select on tables to elt_readonly;
```

---

## Part 3 — Set up Google Cloud + BigQuery

**Skip to step 6 if you already have a project.**

1. Go to [console.cloud.google.com](https://console.cloud.google.com),
   sign in (free tier is enough for this project's data volumes).
2. Click the project dropdown at the top → **New Project**. Name it
   e.g. `project-concord-analytics`. Create it.
3. Once created, select it, then go to **APIs & Services → Library**,
   search **BigQuery API**, click **Enable**.
4. Go to **BigQuery** (search it in the top bar) — this confirms it's
   active. You don't need to create a dataset manually; the pipeline
   script does that for you on first run.
5. **Billing:** BigQuery requires a billing account attached even on
   the free tier, but the free monthly quota (1 TB of queries, 10 GB
   storage) is far beyond what this project's data volumes will ever
   use — you should not be charged for this project.
6. **Create a service account** (this is how the script authenticates,
   instead of your personal login):
   - **IAM & Admin → Service Accounts → Create Service Account**
   - Name it `concord-elt-pipeline`
   - Grant it two roles: **BigQuery Data Editor** and **BigQuery Job User**
   - Click **Done**
7. **Create a key for it:**
   - Click into the service account you just made → **Keys** tab →
     **Add Key → Create new key → JSON**
   - This downloads a `.json` file. **Keep this file private** — it's
     equivalent to a password. Save it somewhere on your machine, e.g.
     `~/concord-elt-key.json`.

---

## Part 4 — Install what the script needs

On your own machine (not this sandbox), with Python installed:
```bash
pip install pandas sqlalchemy psycopg2-binary google-cloud-bigquery
```

---

## Part 5 — Set your environment variables

**Mac/Linux (Terminal):**
```bash
export SUPABASE_DB_URL="postgresql://elt_readonly:your-password@db.xxxxxxxxxxxx.supabase.co:5432/postgres"
export GOOGLE_APPLICATION_CREDENTIALS="/full/path/to/concord-elt-key.json"
export BQ_PROJECT_ID="project-concord-analytics"
export BQ_DATASET="concord_analytics"
```

**Windows (PowerShell):**
```powershell
$env:SUPABASE_DB_URL="postgresql://elt_readonly:your-password@db.xxxxxxxxxxxx.supabase.co:5432/postgres"
$env:GOOGLE_APPLICATION_CREDENTIALS="C:\full\path\to\concord-elt-key.json"
$env:BQ_PROJECT_ID="project-concord-analytics"
$env:BQ_DATASET="concord_analytics"
```

**Important:** use the `elt_readonly` role's connection string here, not
`postgres` — this is what makes the "read-only, curated-only" access
boundary real rather than theoretical. If you're on Supabase's Session
Pooler (recommended, per your earlier IPv4 issue), the username needs
the `elt_readonly.[project-ref]` format instead of plain `elt_readonly`
— check your pooler connection string format in Supabase's dashboard
under **Project Settings → Database → Connection Pooling**.

---

## Part 6 — Run it: dry-run first, always

```bash
python elt_pipeline.py --dry-run
```

This extracts from all 5 views for real and prints row counts, but
does **not** touch BigQuery — it's purely a "does the Postgres half
work" check. You should see something like:
```
2026-07-23 | INFO | EXTRACT  analytics.vw_elt_supply_signal ...
2026-07-23 | INFO |          10,719 rows extracted
2026-07-23 | INFO | LOAD     [dry-run] would replace ...
...
2026-07-23 | INFO | Completed in X.Xs. 5/5 jobs succeeded.
```

If this fails, the problem is your Postgres connection or the views —
fix that before touching BigQuery at all.

---

## Part 7 — Run it for real

```bash
python elt_pipeline.py
```

This time it actually writes to BigQuery. First run creates the
`concord_analytics` dataset automatically. Check it worked:
1. Go to the BigQuery console in Google Cloud.
2. In the left panel, find your project → `concord_analytics` dataset.
3. You should see 5 tables: `fact_supply_signal`,
   `fact_farmer_credit_summary`, `fact_warehouse_lease_status`,
   `fact_daily_revenue_by_division`, `fact_retail_sales`.
4. Click any table → **Preview** tab to see real rows.

---

## Part 8 — Schedule it to run nightly

The brief specifies a nightly refresh (Section 4.5). Two reasonable
options, from simplest to most "production-grade":

**Option A — cron, if you have any always-on machine**
```bash
crontab -e
```
Add a line to run at 2 AM daily (adjust the paths and env vars to
match your setup, since cron doesn't inherit your shell's environment):
```
0 2 * * * SUPABASE_DB_URL="..." GOOGLE_APPLICATION_CREDENTIALS="..." BQ_PROJECT_ID="..." /usr/bin/python3 /path/to/elt_pipeline.py >> /path/to/elt_log.txt 2>&1
```

**Option B — Google Cloud Scheduler + Cloud Run** (more setup, but
matches what a real production deployment would look like — worth
mentioning in your presentation even if you run Option A day-to-day):
1. Package the script and its dependencies into a container (a simple
   `Dockerfile` with `pip install -r requirements.txt` and
   `CMD ["python", "elt_pipeline.py"]`).
2. Deploy it to **Cloud Run** as a job (not a service — jobs run to
   completion and stop, which is what you want for a nightly batch).
3. Create a **Cloud Scheduler** trigger set to `0 2 * * *` (2 AM daily,
   cron syntax) that invokes the Cloud Run job.
4. Store your Supabase connection string as a **Secret Manager** secret
   rather than a plain environment variable, and grant the Cloud Run
   service account access to it.

For an 8-week academic engagement, Option A is entirely defensible —
Section 4.5 explicitly says "a scheduled script... is left to the
team's own judgement." Document whichever you choose; that
documentation is itself part of the graded deliverable.

---

## Troubleshooting

| Symptom | Cause | Fix |
|---|---|---|
| `permission denied for schema analytics` | Connected as the wrong role | Confirm you're using `elt_readonly`, and that Part 2's grants actually ran |
| `password authentication failed` | Same IPv4/pooler username issue as your team's earlier Supabase setup | Use the pooler connection string with the `role.[project-ref]` username format |
| `403 Forbidden` from BigQuery | Service account missing a role | Re-check Part 3 step 6 — needs both BigQuery Data Editor and BigQuery Job User |
| Script hangs on `load_job.result()` | Normal for large tables — this blocks until BigQuery finishes | `fact_retail_sales` (1.25M rows) took ~30s in testing; be patient, don't kill it early |
| One job fails, others still succeed | Working as designed | Check the specific error in the log for that one table; the pipeline deliberately doesn't abort the whole run |
