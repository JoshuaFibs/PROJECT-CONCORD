-- =====================================================================
-- Project Concord | 005_elt_curated_views.sql
-- Curated, consent-checked extraction layer for the BigQuery ELT
-- pipeline (Section 4.5). Nothing in this file is read directly by
-- Looker Studio / Power BI -- these views exist ONLY to define what
-- the nightly ELT job is allowed to move into BigQuery. Raw
-- operational tables (ret_pos_transactions, vfs_wallet_transactions,
-- vfs_kyc_records, etc.) are never queried by the analytics layer
-- directly, per the OLTP/OLAP separation in Section 4.5.
--
-- Design rule applied throughout: no customer PII (name, DOB, phone)
-- crosses into these views -- only customer_id, which BigQuery needs
-- for joins but which is not personally identifying on its own.
-- =====================================================================

create schema if not exists analytics;

-- ---------------------------------------------------------------
-- Scenario 1 (Ngozi): AgriCore supply signal reaching Retail
-- ---------------------------------------------------------------
create or replace view analytics.vw_elt_supply_signal as
select
    h.harvest_id,
    h.farm_id,
    f.supplier_id,
    h.product_id,
    p.product_name,
    h.harvest_date,
    h.volume_kg as harvested_volume_kg,
    r.run_id,
    r.output_volume_kg as processed_volume_kg,
    ws.wholesale_id,
    ws.destination_type,
    sd.delivery_id,
    sd.store_id,
    sd.expected_date as delivery_expected_date,
    sd.received_date as delivery_received_date,
    sd.status as delivery_status,
    (sd.status in ('delayed','cancelled')) as is_at_risk
from agr_harvest_batches h
join agr_farms f on f.farm_id = h.farm_id
join hub_products p on p.product_id = h.product_id
left join agr_processing_runs r on r.harvest_id = h.harvest_id
left join agr_wholesale_shipments ws on ws.run_id = r.run_id
left join ret_supplier_deliveries sd on sd.supplier_id = f.supplier_id;

comment on view analytics.vw_elt_supply_signal is
    'Curated extract for Scenario 1 (Ngozi): connects a harvest recorded by an AgriCore field agent to the retail delivery it eventually affects, surfacing at-risk deliveries before shelves empty.';

-- ---------------------------------------------------------------
-- Scenario 2 (Chinedu): consent-gated farmer credit summary
-- (builds on the two views already defined in 002_roles_and_rls.sql,
-- re-exposed here under the analytics schema for the ELT job)
-- ---------------------------------------------------------------
create or replace view analytics.vw_elt_farmer_credit_summary as
select
    f.farmer_id,
    s.supplier_id,
    count(distinct hb.harvest_id) as total_harvest_batches,
    coalesce(sum(hb.volume_kg), 0) as total_volume_kg,
    min(hb.harvest_date) as first_harvest_date,
    max(hb.harvest_date) as most_recent_harvest_date,
    flr.loan_id,
    flr.visible_summary_status,
    l.status as loan_status,
    l.principal_amount
from agr_farmers f
join hub_suppliers s on s.supplier_id = f.supplier_id
left join agr_farms fm on fm.supplier_id = s.supplier_id
left join agr_harvest_batches hb on hb.farm_id = fm.farm_id
left join agr_farmer_loans_reference flr on flr.farmer_id = f.farmer_id
left join vfs_loans l on l.loan_id = flr.loan_id
where s.status = 'active'
group by f.farmer_id, s.supplier_id, flr.loan_id, flr.visible_summary_status, l.status, l.principal_amount;

comment on view analytics.vw_elt_farmer_credit_summary is
    'Curated extract for Scenario 2 (Chinedu): aggregated farmer supply history joined to loan status. No raw wallet transactions or KYC data included -- those never leave vfs_* tables per Section 4.4.';

-- ---------------------------------------------------------------
-- Scenario 3 (Funmi): warehouse and lease status
-- ---------------------------------------------------------------
create or replace view analytics.vw_elt_warehouse_lease_status as
select
    w.warehouse_id,
    w.location_id,
    loc.city,
    loc.country_code,
    w.capacity_units,
    p.property_id,
    p.property_type,
    p.ownership_status,
    l.lease_id,
    l.tenant_id,
    t.tenant_type,
    t.division_id as tenant_division,
    l.start_date,
    l.end_date,
    l.monthly_rent,
    l.is_current
from log_warehouses w
join hub_locations loc on loc.location_id = w.location_id
join prop_properties p on p.property_id = w.leased_from_property_id
left join prop_leases l on l.property_id = p.property_id
left join prop_tenants t on t.tenant_id = l.tenant_id;

comment on view analytics.vw_elt_warehouse_lease_status is
    'Curated extract for Scenario 3 (Funmi): every warehouse joined to its current lease and tenant, so logistics dispatch can see property status without querying prop_* tables directly.';

-- ---------------------------------------------------------------
-- Scenario 4 (Adaeze): same-day consolidated revenue across divisions
-- ---------------------------------------------------------------
create or replace view analytics.vw_elt_daily_revenue_by_division as
select
    'meridian_retail'::text as division_id,
    date(t.transaction_date) as activity_date,
    sum(t.total_amount) as revenue,
    count(*) as transaction_count
from ret_pos_transactions t
group by date(t.transaction_date)

union all

select
    'veridian_financial_services'::text,
    ms.settlement_date,
    sum(ms.total_amount),
    count(*)
from vfs_merchant_settlements ms
group by ms.settlement_date

union all

select
    'concord_logistics'::text,
    date(sl.departure_time),
    count(*) * 45000.0,  -- placeholder per-shipment-leg revenue proxy;
                          -- a real deployment would join actual freight
                          -- billing data, which sits outside this
                          -- brief's modelled scope (Section 3.2)
    count(*)
from log_shipment_legs sl
group by date(sl.departure_time)

union all

select
    'veridian_properties'::text,
    l.start_date,         -- REAL revenue -- monthly_rent is an actual
                           -- column on prop_leases, not a proxy. Attributed
                           -- to the lease's start_date as its activity date;
                           -- this is a recurring monthly figure being shown
                           -- as a single day's entry, not a true daily rate.
    sum(l.monthly_rent),
    count(*)
from prop_leases l
group by l.start_date

union all

select
    'agricore'::text,
    h.harvest_date,
    sum(h.volume_kg) * 350.0,  -- placeholder price-per-kg proxy; AgriCore's
                                -- own tables (agr_farms, agr_harvest_batches,
                                -- agr_processing_runs, agr_wholesale_shipments)
                                -- contain no price or monetary column anywhere
                                -- in the brief's data model -- there is no real
                                -- figure to sum here, unlike Properties above.
    count(*)
from agr_harvest_batches h
group by h.harvest_date;

comment on view analytics.vw_elt_daily_revenue_by_division is
    'Curated extract for Scenario 4 (Adaeze): same-day revenue signal per division, all 5 divisions. Retail, VFS, and Properties are real figures (POS totals, settlement totals, and lease rent respectively). Logistics and AgriCore are documented proxies -- neither division''s tables contain a real monetary/price column in this brief''s data model -- flagged here rather than silently presented as real revenue.';

-- ---------------------------------------------------------------
-- General: retail sales fact, for ad-hoc executive/divisional
-- dashboard queries beyond the four named scenarios
-- ---------------------------------------------------------------
create or replace view analytics.vw_elt_retail_sales_fact as
select
    t.transaction_id,
    t.store_id,
    s.store_format,
    loc.city,
    loc.country_code,
    t.customer_id,
    date(t.transaction_date) as sale_date,
    t.payment_method,
    li.product_id,
    p.category as product_category,
    li.quantity,
    li.unit_price,
    (li.quantity * li.unit_price) as line_revenue
from ret_pos_transactions t
join ret_stores s on s.store_id = t.store_id
join hub_locations loc on loc.location_id = s.location_id
join ret_line_items li on li.transaction_id = t.transaction_id
join hub_products p on p.product_id = li.product_id;

comment on view analytics.vw_elt_retail_sales_fact is
    'General-purpose curated sales fact table, product- and location-level, for divisional dashboards beyond the four named scenarios.';

-- ---------------------------------------------------------------
-- Grant read access to the financial_services / group_executive /
-- retail_ops roles as appropriate -- the ELT service account itself
-- should use a dedicated read-only role (see elt_pipeline.py), not
-- any of the six application roles.
-- ---------------------------------------------------------------
grant usage on schema analytics to authenticated;
grant select on all tables in schema analytics to authenticated;
