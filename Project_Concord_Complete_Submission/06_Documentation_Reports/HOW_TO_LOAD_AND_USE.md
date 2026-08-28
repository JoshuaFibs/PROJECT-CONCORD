# Project Concord — How to Load and Use the Database

This guide takes you from an empty Supabase project to a fully working,
queryable database with data in it, using the files already delivered:

- `project_concord_full_database.sql` (schema + RLS, consolidated)
- `004_seed_10_rows.sql` (10 rows per table, for quick manual inspection)
- `003_load_synthetic_data.sql` + `synthetic_data.zip` (2.37M rows, for realistic testing)

---

## Part 1 — Create your Supabase project

1. Go to [supabase.com](https://supabase.com) and sign in (or create a free account).
2. Click **New Project**.
3. Choose an organisation, name the project (e.g. `project-concord`), set a
   **database password** — write this down, you'll need it in Part 2.
4. Choose a region close to you, leave the plan on **Free**.
5. Click **Create new project**. This takes 1–2 minutes to provision.

While it provisions: Supabase is automatically creating the `auth` schema,
the `auth.uid()` function, and the `authenticated` role for you — the three
things the RLS half of the script depends on. You do **not** need to create
these yourself; that's only necessary if you were testing against a bare,
non-Supabase PostgreSQL install.

---

## Part 2 — Get your connection details

1. In your Supabase project, go to **Project Settings** (gear icon) →
   **Database**.
2. Under **Connection string**, choose the **URI** tab. It looks like:
   ```
   postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres
   ```
3. Replace `[YOUR-PASSWORD]` with the database password from Part 1.
4. Keep this string somewhere safe — you'll paste it into pgAdmin next.

---

## Part 3 — Connect with pgAdmin

1. Download and install [pgAdmin 4](https://www.pgadmin.org/download/) if
   you don't already have it.
2. Open pgAdmin. Right-click **Servers** in the left panel → **Register** →
   **Server...**
3. **General tab:** Name it `Project Concord`.
4. **Connection tab:**
   - Host name/address: the part after `@` and before `:5432` in your
     connection string (e.g. `db.xxxxxxxxxxxx.supabase.co`)
   - Port: `5432`
   - Maintenance database: `postgres`
   - Username: `postgres`
   - Password: your database password (tick "Save password" for convenience)
5. Click **Save**. pgAdmin connects and shows your Supabase database in the
   tree on the left.

---

## Part 4 — Run the schema + RLS script

1. In pgAdmin's tree, click on your `postgres` database under the new
   server to select it.
2. Open the **Query Tool**: right-click the database → **Query Tool** (or
   the lightning-bolt icon in the toolbar).
3. Open `project_concord_full_database.sql`: **File → Open**, navigate to
   the file, select it.
4. Click **Execute/Run** (the ▶ play button, or F5).
5. Watch the **Messages** tab at the bottom. You're looking for a clean
   scroll of `CREATE TABLE`, `CREATE INDEX`, `CREATE POLICY`, etc., ending
   with no red error text. If everything ran, the last line will be from
   the final `GRANT` or `COMMENT` statement in the file with no error above it.

**If you see an error mentioning `auth.uid()` or `role "authenticated" does
not exist`:** you're not actually connected to a Supabase database (Supabase
creates these automatically) — double check you're connected to the right
server in Part 3, not a local Postgres install.

6. Confirm it worked: in the Query Tool, run
   ```sql
   select count(*) from information_schema.tables
   where table_schema = 'public' and table_type = 'BASE TABLE';
   ```
   You should get **41** (40 business tables + the `app_user_roles` mapping
   table).

---

## Part 5 — Load data

You have two options — pick one, or do the 10-row version first to sanity-check, then the full dataset.

### Option A: Quick 10-row seed (fast, easy to read manually)

1. In pgAdmin's Query Tool, **File → Open** → `004_seed_10_rows.sql`.
2. Click **Execute/Run**.
3. It's wrapped in a transaction, so it either loads completely or not at
   all — you'll see `INSERT 0 1` repeated 400 times, then a final `COMMIT`.
4. Browse it: in the left tree, expand **Databases → postgres → Schemas →
   public → Tables**, right-click any table (e.g. `hub_customers`) → **View/Edit
   Data → All Rows**.

### Option B: Full synthetic dataset (2.37M rows, realistic scale)

pgAdmin's Query Tool doesn't run `\copy` (that's a `psql`-only client
command), so use one of these instead:

**If you have `psql` installed locally** (comes with PostgreSQL, or install
just the client tools):
```bash
unzip synthetic_data.zip
psql "postgresql://postgres:[YOUR-PASSWORD]@db.xxxxxxxxxxxx.supabase.co:5432/postgres" \
  -f 003_load_synthetic_data.sql
```
Run this from the folder containing both the `.sql` file and the unzipped
`synthetic_data/` folder, since the script uses relative paths.

**If you don't want to install `psql`:** use Supabase's **Table Editor** →
select a table → **Insert → Import data from CSV**, and upload each CSV from
`synthetic_data.zip` one at a time, in this order (it matters — later
tables reference earlier ones):
```
hub_customers → hub_employees → hub_suppliers → hub_locations → hub_products
→ hub_financial_account_refs → ret_stores → ret_pos_transactions →
ret_line_items → ret_stock_levels → ret_promotions → ret_loyalty_accounts →
ret_supplier_deliveries → log_vehicles → log_drivers → log_shipments →
log_shipment_legs → log_routes → log_maintenance_logs →
vfs_wallet_accounts → vfs_wallet_transactions → vfs_loans →
vfs_loan_repayments → vfs_kyc_records → vfs_merchant_settlements →
agr_farmers → agr_farms → agr_harvest_batches → agr_processing_runs →
agr_quality_grades → agr_wholesale_shipments → agr_farmer_loans_reference →
prop_properties → log_warehouses → prop_tenants → prop_leases →
prop_maintenance_requests → prop_valuations → prop_utility_accounts →
prop_facility_assets
```
This is exactly the order in `003_load_synthetic_data.sql` — that file is
your reference even if you're clicking through the UI instead of running it
as a script.

---

## Part 6 — Using it: querying, and testing the RLS roles

### Querying normally
Once data is loaded, just write SQL in pgAdmin's Query Tool as normal —
e.g.:
```sql
select store_format, count(*), sum(total_amount)
from ret_pos_transactions t join ret_stores s on s.store_id = t.store_id
group by store_format;
```
By default, the Query Tool connects as the `postgres` superuser, which
**bypasses RLS entirely** — you'll see all rows in every table regardless
of policy. This is normal and expected for admin work.

### Testing the RLS roles for real
To actually see the access restrictions in effect (e.g. confirm
`retail_ops` genuinely cannot read `vfs_kyc_records`), you need to
simulate a logged-in user with a role assigned:

1. Create a test user via Supabase's **Authentication → Users → Add user**
   in the Supabase dashboard (not pgAdmin). Note the generated `user_id` (a UUID).
2. Back in pgAdmin's Query Tool, assign that user a role:
   ```sql
   insert into app_user_roles (user_id, role_name)
   values ('paste-the-uuid-here', 'retail_ops');
   ```
3. To test as that user, you'd query through Supabase's API with that
   user's auth token (not through pgAdmin's superuser connection) — pgAdmin
   itself has no concept of "logged in as a specific app user." This is
   normally tested from your application code or Supabase's API testing
   tools, not the database client directly.

### Verifying the four stakeholder scenarios
This is the acceptance test the brief actually cares about (Section 3.1).
With data loaded, try:
```sql
-- Scenario 1 (Ngozi): supply shortfall visibility
select h.harvest_date, h.volume_kg, d.status, d.expected_date
from agr_harvest_batches h
join agr_farms f on f.farm_id = h.farm_id
join ret_supplier_deliveries d on d.supplier_id = f.supplier_id
where d.status = 'delayed';

-- Scenario 3 (Funmi): warehouse lease status
select w.warehouse_id, p.property_type, l.tenant_id, l.end_date, l.is_current
from log_warehouses w
join prop_properties p on p.property_id = w.leased_from_property_id
join prop_leases l on l.property_id = p.property_id;
```

---

## Troubleshooting

| Symptom | Likely cause | Fix |
|---|---|---|
| `role "authenticated" does not exist` | Connected to a non-Supabase Postgres | Reconnect to your actual Supabase project |
| `relation already exists` | Script run twice on the same database | Either work on a fresh project, or drop the tables first (`drop schema public cascade; create schema public;`) — **this deletes everything**, only do this on a throwaway/dev project |
| `\copy` doesn't work in pgAdmin | It's a `psql`-only command | Use `psql` directly, or Supabase's Table Editor CSV import (Part 5, Option B) |
| Query Tool shows all rows regardless of role | Connected as `postgres` superuser | Expected — RLS only restricts non-superuser roles |

---

## Recommended order for your actual submission

1. Create a **development** Supabase project, run everything here against
   it first (Section 4.6 of the brief requires a dev environment separate
   from primary).
2. Once confirmed clean, create your **primary** Supabase project and
   repeat Parts 1–5 there — this is the one you present from.
3. Keep `project_concord_full_database.sql`, `003_load_synthetic_data.sql`,
   and `generate_synthetic_data.py` in your version control repository —
   Section 6.4 requires the schema, ELT code, and data generation method to
   all be submitted alongside the live database.
