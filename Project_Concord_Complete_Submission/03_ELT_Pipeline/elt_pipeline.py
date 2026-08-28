"""
Project Concord | ELT Pipeline: Supabase Postgres -> Google BigQuery
========================================================================
Implements Section 4.5 of the brief: a scheduled Extract-Load-Transform
process moving data from the curated, consent-checked views in
005_elt_curated_views.sql into BigQuery, structured for analytical
query patterns rather than mirroring the operational schema row-for-row.

Design decisions, and why:

- Extracts ONLY from the `analytics.vw_elt_*` views, never from raw
  tables. This is enforced structurally: the connection this script
  uses should be a dedicated read-only Postgres role granted SELECT
  on the `analytics` schema only (see the `elt_readonly` role setup
  at the bottom of this file's docstring) -- so even a bug in this
  script cannot accidentally pull raw wallet transactions or KYC data.
- WRITE_TRUNCATE load disposition: each nightly run replaces the prior
  day's snapshot rather than appending, since Section 4.5 specifies a
  nightly refresh, not incremental streaming, and the data volumes in
  this project (Section 5.4) are small enough that a full nightly
  reload is simpler and more reliable than incremental merge logic.
- Every extracted table is logged with row counts and timing, and a
  failure in one table does not stop the others -- partial failure is
  visible in the run log rather than silently blocking the whole job,
  addressing the brief's requirement (4.5) to describe "how the
  process would be monitored for failure."

Usage:
    python elt_pipeline.py --dry-run     # extract + validate, skip BigQuery
    python elt_pipeline.py               # full run

Environment variables required for a real run:
    SUPABASE_DB_URL       postgresql://... connection string
    GOOGLE_APPLICATION_CREDENTIALS   path to a service account JSON key
    BQ_PROJECT_ID         your Google Cloud project id
    BQ_DATASET            target BigQuery dataset (default: concord_analytics)
"""

import argparse
import logging
import os
import sys
import time
import uuid
from dataclasses import dataclass

import pandas as pd

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)-7s | %(message)s",
)
log = logging.getLogger("concord_elt")


@dataclass
class ExtractJob:
    source_view: str          # analytics.vw_elt_* in Postgres
    target_table: str         # table name in BigQuery
    description: str


# The five curated views defined in 005_elt_curated_views.sql, each
# mapped to its BigQuery target table name.
JOBS = [
    ExtractJob("analytics.vw_elt_supply_signal", "fact_supply_signal",
               "Scenario 1 (Ngozi): AgriCore harvest -> retail delivery traceability"),
    ExtractJob("analytics.vw_elt_farmer_credit_summary", "fact_farmer_credit_summary",
               "Scenario 2 (Chinedu): consent-gated farmer supply + loan summary"),
    ExtractJob("analytics.vw_elt_warehouse_lease_status", "fact_warehouse_lease_status",
               "Scenario 3 (Funmi): warehouse + current lease status"),
    ExtractJob("analytics.vw_elt_daily_revenue_by_division", "fact_daily_revenue_by_division",
               "Scenario 4 (Adaeze): same-day consolidated revenue"),
    ExtractJob("analytics.vw_elt_retail_sales_fact", "fact_retail_sales",
               "General-purpose retail sales fact for divisional dashboards"),
]


def get_postgres_engine():
    """Connect using a dedicated read-only role scoped to the
    `analytics` schema only -- never the migration/admin credentials.
    Provisioning (run once, by an admin, not by this script):

        create role elt_readonly login password '...';
        grant usage on schema analytics to elt_readonly;
        grant select on all tables in schema analytics to elt_readonly;
        alter default privileges in schema analytics
            grant select on tables to elt_readonly;
    """
    from sqlalchemy import create_engine
    db_url = os.environ.get("SUPABASE_DB_URL")
    if not db_url:
        raise RuntimeError("SUPABASE_DB_URL is not set. See module docstring.")
    return create_engine(db_url)


def get_bigquery_client():
    from google.cloud import bigquery
    project_id = os.environ.get("BQ_PROJECT_ID")
    if not project_id:
        raise RuntimeError("BQ_PROJECT_ID is not set. See module docstring.")
    return bigquery.Client(project=project_id)


def _stringify_uuid_columns(df: pd.DataFrame) -> pd.DataFrame:
    """Postgres `uuid` columns come back from psycopg2/pandas as Python
    uuid.UUID objects, not plain strings. BigQuery's Arrow-based loader
    cannot infer a type for that raw object and fails the whole table.
    Found via a real failed load against live data (every failing
    table had UUID columns; the one table with none succeeded) -- not
    something caught by the earlier dry-run testing, since dry-run
    never actually handed the data to the BigQuery client library.
    Converting any UUID-object column to plain text fixes it, and is
    harmless: BigQuery stores it as a STRING either way."""
    for col in df.columns:
        if df[col].dtype == object and df[col].apply(lambda v: isinstance(v, uuid.UUID)).any():
            df[col] = df[col].astype(str)
    return df


def extract(engine, job: ExtractJob) -> pd.DataFrame:
    log.info(f"EXTRACT  {job.source_view:45s} -> {job.description}")
    df = pd.read_sql(f"select * from {job.source_view}", engine)
    df = _stringify_uuid_columns(df)
    log.info(f"         {len(df):,} rows extracted")
    return df


def load(client, dataset: str, job: ExtractJob, df: pd.DataFrame, dry_run: bool):
    table_ref = f"{dataset}.{job.target_table}" if dry_run else f"{client.project}.{dataset}.{job.target_table}"
    if dry_run:
        log.info(f"LOAD     [dry-run] would replace {table_ref} with {len(df):,} rows")
        return
    from google.cloud import bigquery
    job_config = bigquery.LoadJobConfig(
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True,
    )
    load_job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)
    load_job.result()  # blocks until complete, raises on failure
    log.info(f"LOAD     {table_ref} replaced, {len(df):,} rows")


def ensure_dataset(client, dataset: str, dry_run: bool):
    dataset_ref = f"{dataset}" if dry_run else f"{client.project}.{dataset}"
    if dry_run:
        log.info(f"[dry-run] would ensure dataset {dataset_ref} exists")
        return
    from google.cloud import bigquery
    ds = bigquery.Dataset(dataset_ref)
    ds.location = "US"
    client.create_dataset(ds, exists_ok=True)


def run(dry_run: bool = False):
    started = time.time()
    dataset = os.environ.get("BQ_DATASET", "concord_analytics")
    log.info(f"Project Concord ELT run starting (dry_run={dry_run})")
    log.info(f"Target dataset: {dataset}")

    engine = get_postgres_engine()
    client = None if dry_run else get_bigquery_client()
    if client:
        ensure_dataset(client, dataset, dry_run)

    results = []
    for job in JOBS:
        job_start = time.time()
        try:
            df = extract(engine, job)
            load(client, dataset, job, df, dry_run)
            results.append((job.target_table, len(df), "OK", time.time() - job_start))
        except Exception as e:
            log.error(f"FAILED   {job.target_table}: {e}")
            results.append((job.target_table, 0, f"FAILED: {e}", time.time() - job_start))
            # Deliberately continue to the next job rather than aborting
            # the whole run -- a failure in one table (e.g. one view
            # temporarily broken) should not block the other four.

    log.info("=" * 70)
    log.info("RUN SUMMARY")
    log.info("=" * 70)
    failed = 0
    for table, rows, status, elapsed in results:
        marker = "OK  " if status == "OK" else "FAIL"
        log.info(f"  [{marker}] {table:35s} {rows:>10,} rows   {elapsed:6.1f}s   {status if status != 'OK' else ''}")
        if status != "OK":
            failed += 1

    total_elapsed = time.time() - started
    log.info(f"Completed in {total_elapsed:.1f}s. {len(results) - failed}/{len(results)} jobs succeeded.")

    if failed:
        log.error(f"{failed} job(s) failed -- see above. Exiting with non-zero status for monitoring/alerting.")
        sys.exit(1)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Project Concord ELT: Postgres -> BigQuery")
    parser.add_argument("--dry-run", action="store_true",
                         help="Extract and validate without writing to BigQuery")
    args = parser.parse_args()
    run(dry_run=args.dry_run)
