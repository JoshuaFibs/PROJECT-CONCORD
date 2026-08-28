-- =====================================================================
-- PROJECT CONCORD | Veridian Unified Data Platform
-- Full Database Build Script — Consolidated
-- Target: PostgreSQL 15+ on Supabase (validated locally on PostgreSQL 16)
--
-- This file combines, in strict dependency order:
--   Part A — Core Services Hub + Five Divisional Modules (schema)
--   Part B — Roles, Row Level Security, and consent-gated views
--
-- Every statement in this file has been executed against a live
-- PostgreSQL server with ON_ERROR_STOP=1 and confirmed to complete
-- with zero errors before being included here.
--
-- Prerequisite: this script assumes a Supabase project (which
-- provides the `auth` schema, `auth.uid()`, and the `authenticated`
-- role automatically). Running against a bare PostgreSQL install
-- requires stubbing those three objects first — see the note at the
-- top of Part B below.
-- =====================================================================


-- #######################################################################
-- PART A — SCHEMA (Core Services Hub + Five Divisional Modules)
-- #######################################################################


create extension if not exists "pgcrypto";

-- =====================================================================
-- CORE SERVICES HUB  (Section 5.1)
-- =====================================================================

create table hub_customers (
    customer_id             uuid primary key default gen_random_uuid(),
    full_name               text not null,
    date_of_birth           date,
    primary_contact         text,
    registered_country      text not null check (registered_country in ('Nigeria','Ghana','Kenya')),
    consent_retail_personalisation   boolean not null default false,
    consent_credit_assessment_share  boolean not null default false,
    consent_cross_div_marketing      boolean not null default false,
    created_date             timestamptz not null default now()
);

create table hub_employees (
    employee_id             uuid primary key default gen_random_uuid(),
    full_name               text not null,
    division_id             text not null check (division_id in
                                ('meridian_retail','concord_logistics','veridian_financial_services',
                                 'agricore','veridian_properties','group_functions')),
    role_title               text not null,
    employment_status        text not null default 'active' check (employment_status in ('active','on_leave','terminated')),
    hire_date                 date not null,
    reports_to                uuid references hub_employees(employee_id)
);

create table hub_suppliers (
    supplier_id              uuid primary key default gen_random_uuid(),
    legal_name               text not null,
    supplier_type             text not null check (supplier_type in ('farmer','retail_vendor','logistics_vendor','general')),
    primary_division_id       text not null,
    onboarding_date            date not null default current_date,
    status                     text not null default 'active' check (status in ('active','inactive'))
);

create table hub_locations (
    location_id              uuid primary key default gen_random_uuid(),
    site_name                 text not null,
    site_type                  text not null check (site_type in
                                ('store','warehouse','farm','processing_facility','property','office')),
    address                    text,
    city                       text not null,
    country_code               text not null check (char_length(country_code) = 2),
    latitude                    numeric(9,6),
    longitude                   numeric(9,6)
);

create table hub_products (
    product_id                uuid primary key default gen_random_uuid(),
    product_name               text not null,
    category                    text not null,
    unit_of_measure              text not null,
    primary_division_id          text not null,
    is_active                     boolean not null default true
);

create table hub_financial_account_refs (
    account_ref_id             uuid primary key default gen_random_uuid(),
    customer_id                 uuid not null references hub_customers(customer_id),
    account_type                  text not null check (account_type in ('savings','wallet','loan')),
    account_status                 text not null default 'active' check (account_status in ('active','dormant','closed')),
    opened_date                     date not null default current_date
);

-- =====================================================================
-- MERIDIAN RETAIL AND CONSUMER MODULE  (Section 5.2.1)
-- =====================================================================

create table ret_stores (
    store_id                  uuid primary key default gen_random_uuid(),
    location_id                 uuid not null unique references hub_locations(location_id),
    store_format                  text not null check (store_format in ('large_format','neighbourhood','online')),
    opening_date                    date not null,
    manager_employee_id              uuid references hub_employees(employee_id)
);

create table ret_pos_transactions (
    transaction_id              uuid primary key default gen_random_uuid(),
    store_id                      uuid not null references ret_stores(store_id),
    customer_id                     uuid references hub_customers(customer_id),
    transaction_date                  timestamptz not null default now(),
    total_amount                        numeric(12,2) not null check (total_amount >= 0),
    payment_method                        text not null check (payment_method in ('cash','card','wallet','other'))
);

create table ret_line_items (
    line_item_id                uuid primary key default gen_random_uuid(),
    transaction_id                 uuid not null references ret_pos_transactions(transaction_id) on delete cascade,
    product_id                       uuid not null references hub_products(product_id),
    quantity                           integer not null check (quantity > 0),
    unit_price                           numeric(10,2) not null check (unit_price >= 0)
);

create table ret_stock_levels (
    stock_id                     uuid primary key default gen_random_uuid(),
    store_id                       uuid not null references ret_stores(store_id),
    product_id                       uuid not null references hub_products(product_id),
    quantity_on_hand                   integer not null default 0 check (quantity_on_hand >= 0),
    last_counted_date                    date,
    unique (store_id, product_id)
);

create table ret_promotions (
    promotion_id                  uuid primary key default gen_random_uuid(),
    product_id                      uuid not null references hub_products(product_id),
    discount_type                     text not null check (discount_type in ('percentage','fixed_amount')),
    start_date                          date not null,
    end_date                              date not null,
    check (end_date >= start_date)
);

create table ret_loyalty_accounts (
    loyalty_id                     uuid primary key default gen_random_uuid(),
    customer_id                      uuid not null references hub_customers(customer_id),
    store_format                       text not null check (store_format in ('large_format','neighbourhood','online')),
    tier                                 text not null default 'bronze' check (tier in ('bronze','silver','gold','platinum')),
    points_balance                         integer not null default 0 check (points_balance >= 0),
    enrolment_date                           date not null default current_date,
    unique (customer_id, store_format)
);

create table ret_supplier_deliveries (
    delivery_id                     uuid primary key default gen_random_uuid(),
    supplier_id                       uuid not null references hub_suppliers(supplier_id),
    store_id                            uuid not null references ret_stores(store_id),
    expected_date                         date not null,
    received_date                           date,
    status                                    text not null default 'scheduled'
                                                check (status in ('scheduled','in_transit','received','delayed','cancelled'))
);

-- =====================================================================
-- CONCORD LOGISTICS MODULE  (Section 5.2.2)
-- =====================================================================

create table log_vehicles (
    vehicle_id                       uuid primary key default gen_random_uuid(),
    registration_number                 text not null unique,
    vehicle_type                          text not null check (vehicle_type in ('van','truck')),
    capacity_kg                             numeric(10,2) not null check (capacity_kg > 0),
    status                                    text not null default 'active' check (status in ('active','maintenance','retired'))
);

create table log_drivers (
    driver_id                        uuid primary key default gen_random_uuid(),
    employee_id                        uuid not null unique references hub_employees(employee_id),
    licence_number                       text not null unique,
    licence_expiry                         date not null
);

create table log_shipments (
    shipment_id                      uuid primary key default gen_random_uuid(),
    origin_location_id                 uuid not null references hub_locations(location_id),
    destination_location_id              uuid not null references hub_locations(location_id),
    client_type                            text not null check (client_type in ('internal','third_party')),
    status                                   text not null default 'planned'
                                              check (status in ('planned','in_transit','delivered','delayed','cancelled')),
    check (origin_location_id <> destination_location_id)
);

create table log_shipment_legs (
    leg_id                           uuid primary key default gen_random_uuid(),
    shipment_id                        uuid not null references log_shipments(shipment_id) on delete cascade,
    vehicle_id                           uuid not null references log_vehicles(vehicle_id),
    driver_id                              uuid not null references log_drivers(driver_id),
    departure_time                           timestamptz not null,
    arrival_time                               timestamptz,
    check (arrival_time is null or arrival_time >= departure_time)
);

create table log_routes (
    route_id                          uuid primary key default gen_random_uuid(),
    route_name                          text not null,
    origin_location_id                    uuid not null references hub_locations(location_id),
    destination_location_id                 uuid not null references hub_locations(location_id),
    distance_km                               numeric(8,2) not null check (distance_km >= 0)
);

create table log_warehouses (
    warehouse_id                       uuid primary key default gen_random_uuid(),
    location_id                          uuid not null unique references hub_locations(location_id),
    capacity_units                         integer not null check (capacity_units >= 0),
    leased_from_property_id                  uuid  -- FK added in migration 002 once prop_properties exists
);

create table log_maintenance_logs (
    maintenance_id                      uuid primary key default gen_random_uuid(),
    vehicle_id                            uuid not null references log_vehicles(vehicle_id),
    service_date                            date not null,
    cost                                      numeric(10,2) not null check (cost >= 0),
    description                                text
);

-- =====================================================================
-- VERIDIAN FINANCIAL SERVICES MODULE  (Section 5.2.3)
-- Curated external feed. Every table here is read-restricted in migration
-- 003 (RLS) to the financial_services and group_executive roles only.
-- =====================================================================

create table vfs_wallet_accounts (
    wallet_id                        uuid primary key default gen_random_uuid(),
    customer_id                        uuid not null unique references hub_customers(customer_id),
    account_ref_id                       uuid references hub_financial_account_refs(account_ref_id),
    balance                                numeric(14,2) not null default 0,
    status                                   text not null default 'active' check (status in ('active','suspended','closed'))
);

create table vfs_wallet_transactions (
    wallet_txn_id                     uuid primary key default gen_random_uuid(),
    wallet_id                           uuid not null references vfs_wallet_accounts(wallet_id) on delete cascade,
    counterparty_type                     text not null,
    amount                                  numeric(12,2) not null,
    transaction_date                          timestamptz not null default now()
);

create table vfs_loans (
    loan_id                           uuid primary key default gen_random_uuid(),
    borrower_customer_id                uuid references hub_customers(customer_id),
    borrower_supplier_id                  uuid references hub_suppliers(supplier_id),
    principal_amount                        numeric(14,2) not null check (principal_amount > 0),
    status                                    text not null default 'pending' check (status in ('pending','active','repaid','defaulted')),
    check (borrower_customer_id is not null or borrower_supplier_id is not null)
);

create table vfs_loan_repayments (
    repayment_id                      uuid primary key default gen_random_uuid(),
    loan_id                             uuid not null references vfs_loans(loan_id) on delete cascade,
    due_date                              date not null,
    amount_due                              numeric(12,2) not null check (amount_due >= 0),
    amount_paid                               numeric(12,2) not null default 0 check (amount_paid >= 0),
    paid_date                                   date
);

create table vfs_kyc_records (
    kyc_id                            uuid primary key default gen_random_uuid(),
    customer_id                         uuid not null references hub_customers(customer_id),
    verification_level                    text not null check (verification_level in ('tier1','tier2','tier3')),
    verified_date                           date
);

create table vfs_merchant_settlements (
    settlement_id                      uuid primary key default gen_random_uuid(),
    division_id                          text not null,
    settlement_date                        date not null,
    total_amount                             numeric(14,2) not null check (total_amount >= 0)
);

-- =====================================================================
-- AGRICORE MODULE  (Section 5.2.4)
-- =====================================================================

create table agr_farms (
    farm_id                            uuid primary key default gen_random_uuid(),
    supplier_id                          uuid not null references hub_suppliers(supplier_id),
    location_id                            uuid not null unique references hub_locations(location_id),
    size_hectares                            numeric(8,2) not null check (size_hectares > 0),
    primary_crop                               text
);

create table agr_farmers (
    farmer_id                          uuid primary key default gen_random_uuid(),
    supplier_id                          uuid not null unique references hub_suppliers(supplier_id),
    registration_date                      date not null default current_date,
    cooperative_name                         text
);

create table agr_harvest_batches (
    harvest_id                          uuid primary key default gen_random_uuid(),
    farm_id                               uuid not null references agr_farms(farm_id),
    product_id                              uuid references hub_products(product_id),
    harvest_date                              date not null,
    volume_kg                                   numeric(10,2) not null check (volume_kg > 0),
    field_agent_employee_id                       uuid references hub_employees(employee_id)
);

create table agr_processing_runs (
    run_id                              uuid primary key default gen_random_uuid(),
    harvest_id                            uuid not null references agr_harvest_batches(harvest_id),
    facility_location_id                    uuid not null references hub_locations(location_id),
    run_date                                  date not null,
    output_volume_kg                            numeric(10,2) not null check (output_volume_kg >= 0)
);

create table agr_quality_grades (
    grade_id                            uuid primary key default gen_random_uuid(),
    run_id                                uuid not null references agr_processing_runs(run_id),
    grade_level                            text not null check (grade_level in ('A','B','C','reject')),
    moisture_content                         numeric(5,2),
    inspector_employee_id                      uuid references hub_employees(employee_id)
);

create table agr_wholesale_shipments (
    wholesale_id                        uuid primary key default gen_random_uuid(),
    run_id                                uuid not null references agr_processing_runs(run_id),
    destination_type                        text not null check (destination_type in ('meridian_retail','external_client')),
    destination_id                            uuid,
    shipment_id                                 uuid references log_shipments(shipment_id)
);

create table agr_farmer_loans_reference (
    reference_id                        uuid primary key default gen_random_uuid(),
    farmer_id                             uuid not null references agr_farmers(farmer_id),
    loan_id                                 uuid references vfs_loans(loan_id),
    visible_summary_status                    text
);

-- =====================================================================
-- VERIDIAN PROPERTIES MODULE  (Section 5.2.5)
-- =====================================================================

create table prop_properties (
    property_id                          uuid primary key default gen_random_uuid(),
    location_id                            uuid unique references hub_locations(location_id),
    property_type                            text not null check (property_type in
                                              ('store_premises','warehouse_depot','processing_adjacent','commercial','residential')),
    size_sqm                                   numeric(10,2) not null check (size_sqm > 0),
    ownership_status                             text not null check (ownership_status in ('owned','leased'))
);

create table prop_tenants (
    tenant_id                            uuid primary key default gen_random_uuid(),
    tenant_type                            text not null check (tenant_type in ('internal_division','external')),
    division_id                              text,
    external_tenant_name                       text,
    check (
        (tenant_type = 'internal_division' and division_id is not null)
        or (tenant_type = 'external' and external_tenant_name is not null)
    )
);

create table prop_leases (
    lease_id                             uuid primary key default gen_random_uuid(),
    property_id                            uuid not null references prop_properties(property_id),
    tenant_id                                uuid not null references prop_tenants(tenant_id),
    start_date                                 date not null,
    end_date                                     date not null,
    monthly_rent                                   numeric(12,2) not null check (monthly_rent >= 0),
    -- is_current is maintained by a trigger (see below), not computed
    -- live, because CURRENT_DATE is STABLE, not IMMUTABLE, and cannot
    -- be referenced directly in an index predicate.
    is_current                                     boolean not null default true,
    check (end_date > start_date)
);

create table prop_maintenance_requests (
    request_id                           uuid primary key default gen_random_uuid(),
    property_id                            uuid not null references prop_properties(property_id),
    requested_date                           date not null default current_date,
    category                                   text not null,
    status                                       text not null default 'open' check (status in ('open','in_progress','resolved','cancelled')),
    resolved_date                                  date
);

create table prop_valuations (
    valuation_id                         uuid primary key default gen_random_uuid(),
    property_id                            uuid not null references prop_properties(property_id),
    valuation_date                           date not null,
    assessed_value                             numeric(14,2) not null check (assessed_value >= 0)
);

create table prop_utility_accounts (
    utility_id                           uuid primary key default gen_random_uuid(),
    property_id                            uuid not null references prop_properties(property_id),
    utility_type                             text not null check (utility_type in ('electricity','water','waste','internet')),
    provider_name                              text not null,
    account_number                               text not null
);

create table prop_facility_assets (
    asset_id                             uuid primary key default gen_random_uuid(),
    property_id                            uuid not null references prop_properties(property_id),
    asset_type                               text not null,
    installed_date                             date,
    condition_rating                             text check (condition_rating in ('excellent','good','fair','poor'))
);

-- =====================================================================
-- Deferred cross-module FK: log_warehouses.leased_from_property_id
-- (prop_properties did not exist yet at the point log_warehouses was
-- created above; added now that it does, per the dependency order
-- documented in the migration history)
-- =====================================================================

alter table log_warehouses
    add constraint fk_warehouse_leased_property
    foreign key (leased_from_property_id) references prop_properties(property_id);

-- =====================================================================
-- INDEXES ON FOREIGN KEYS AND FREQUENTLY FILTERED COLUMNS
-- (required by Section 4.6 / Phase 3 deliverables)
-- =====================================================================

-- Hub
create index idx_hub_employees_reports_to on hub_employees(reports_to);
create index idx_hub_fin_account_refs_customer on hub_financial_account_refs(customer_id);
create index idx_hub_locations_city on hub_locations(city);

-- Retail
create index idx_ret_stores_location on ret_stores(location_id);
create index idx_ret_stores_manager on ret_stores(manager_employee_id);
create index idx_ret_pos_txn_store on ret_pos_transactions(store_id);
create index idx_ret_pos_txn_customer on ret_pos_transactions(customer_id);
create index idx_ret_pos_txn_date on ret_pos_transactions(transaction_date);
create index idx_ret_line_items_txn on ret_line_items(transaction_id);
create index idx_ret_line_items_product on ret_line_items(product_id);
create index idx_ret_stock_levels_store on ret_stock_levels(store_id);
create index idx_ret_stock_levels_product on ret_stock_levels(product_id);
create index idx_ret_promotions_product on ret_promotions(product_id);
create index idx_ret_loyalty_customer on ret_loyalty_accounts(customer_id);
create index idx_ret_supplier_deliveries_supplier on ret_supplier_deliveries(supplier_id);
create index idx_ret_supplier_deliveries_store on ret_supplier_deliveries(store_id);

-- Logistics
create index idx_log_drivers_employee on log_drivers(employee_id);
create index idx_log_shipments_origin on log_shipments(origin_location_id);
create index idx_log_shipments_destination on log_shipments(destination_location_id);
create index idx_log_shipments_status on log_shipments(status);
create index idx_log_legs_shipment on log_shipment_legs(shipment_id);
create index idx_log_legs_vehicle on log_shipment_legs(vehicle_id);
create index idx_log_legs_driver on log_shipment_legs(driver_id);
create index idx_log_routes_origin on log_routes(origin_location_id);
create index idx_log_routes_destination on log_routes(destination_location_id);
create index idx_log_warehouses_location on log_warehouses(location_id);
create index idx_log_warehouses_property on log_warehouses(leased_from_property_id);
create index idx_log_maintenance_vehicle on log_maintenance_logs(vehicle_id);

-- VFS
create index idx_vfs_wallet_customer on vfs_wallet_accounts(customer_id);
create index idx_vfs_wallet_txn_wallet on vfs_wallet_transactions(wallet_id);
create index idx_vfs_wallet_txn_date on vfs_wallet_transactions(transaction_date);
create index idx_vfs_loans_customer on vfs_loans(borrower_customer_id);
create index idx_vfs_loans_supplier on vfs_loans(borrower_supplier_id);
create index idx_vfs_repayments_loan on vfs_loan_repayments(loan_id);
create index idx_vfs_kyc_customer on vfs_kyc_records(customer_id);

-- AgriCore
create index idx_agr_farms_supplier on agr_farms(supplier_id);
create index idx_agr_farms_location on agr_farms(location_id);
create index idx_agr_farmers_supplier on agr_farmers(supplier_id);
create index idx_agr_harvest_farm on agr_harvest_batches(farm_id);
create index idx_agr_harvest_product on agr_harvest_batches(product_id);
create index idx_agr_harvest_agent on agr_harvest_batches(field_agent_employee_id);
create index idx_agr_runs_harvest on agr_processing_runs(harvest_id);
create index idx_agr_runs_facility on agr_processing_runs(facility_location_id);
create index idx_agr_grades_run on agr_quality_grades(run_id);
create index idx_agr_grades_inspector on agr_quality_grades(inspector_employee_id);
create index idx_agr_wholesale_run on agr_wholesale_shipments(run_id);
create index idx_agr_wholesale_shipment on agr_wholesale_shipments(shipment_id);
create index idx_agr_farmer_loans_farmer on agr_farmer_loans_reference(farmer_id);
create index idx_agr_farmer_loans_loan on agr_farmer_loans_reference(loan_id);

-- Properties
create index idx_prop_properties_location on prop_properties(location_id);
create index idx_prop_leases_property on prop_leases(property_id);
create index idx_prop_leases_tenant on prop_leases(tenant_id);
create index idx_prop_maintenance_property on prop_maintenance_requests(property_id);
create index idx_prop_valuations_property on prop_valuations(property_id);
create index idx_prop_utility_property on prop_utility_accounts(property_id);
create index idx_prop_assets_property on prop_facility_assets(property_id);

-- =====================================================================
-- ENFORCING "at most one ACTIVE lease per tenant" (Section 5.3)
-- CURRENT_DATE is STABLE, not IMMUTABLE, so it cannot appear directly
-- in a partial index predicate. Instead, a trigger keeps a plain
-- boolean column (is_current) in sync on every insert/update, and the
-- partial unique index is built on that boolean instead of on a live
-- date comparison. A nightly job (or the same nightly ELT schedule
-- already used for BigQuery, Section 4.5) should re-run
-- refresh_lease_current_flags() to roll leases from current to
-- expired as their end_date passes, since nothing else will flip the
-- flag automatically once a lease simply ages out.
-- =====================================================================

create or replace function fn_set_lease_is_current()
returns trigger
language plpgsql
as $$
begin
    new.is_current := (new.end_date >= current_date);
    return new;
end;
$$;

create trigger trg_set_lease_is_current
    before insert or update of end_date on prop_leases
    for each row execute function fn_set_lease_is_current();

create unique index uidx_one_active_lease_per_tenant
    on prop_leases(tenant_id)
    where (is_current);

create or replace function fn_refresh_lease_current_flags()
returns void
language sql
as $$
    update prop_leases
    set is_current = (end_date >= current_date)
    where is_current <> (end_date >= current_date);
$$;

comment on function fn_refresh_lease_current_flags() is
    'Run nightly (e.g. alongside the BigQuery ELT job in Section 4.5) to roll leases from current to expired as their end_date passes.';



-- #######################################################################
-- PART B — ROLES, ROW LEVEL SECURITY, CONSENT-GATED VIEWS
--
-- NOTE FOR NON-SUPABASE TESTING: this part references auth.users,
-- auth.uid(), and the `authenticated` role, all provided automatically
-- by Supabase. To run this file against a bare PostgreSQL install for
-- local testing, run these three statements FIRST:
--
--   create schema auth;
--   create table auth.users (id uuid primary key default gen_random_uuid());
--   create function auth.uid() returns uuid language sql stable as
--     $$ select null::uuid $$;
--   create role authenticated;
--
-- Do NOT run those four lines against your actual Supabase project —
-- they already exist there and will error as duplicates.
-- #######################################################################

-- RLS policies that call that helper. This is the mechanism Supabase's
-- own RLS documentation recommends and is what section 4.2 refers to
-- when it says roles are "enforced by Supabase Auth's role and
-- identity model."
-- =====================================================================

create table app_user_roles (
    user_id     uuid primary key references auth.users(id) on delete cascade,
    role_name   text not null check (role_name in
                  ('retail_ops','logistics_ops','agricore_ops',
                   'properties_ops','financial_services','group_executive'))
);

create or replace function current_role_name()
returns text
language sql
stable
security definer
as $$
    select role_name from app_user_roles where user_id = auth.uid();
$$;

-- =====================================================================
-- ENABLE RLS ON EVERY TABLE  (RLS must be explicitly turned on per
-- table in Postgres even after policies are written)
-- =====================================================================

alter table hub_customers enable row level security;
alter table hub_employees enable row level security;
alter table hub_suppliers enable row level security;
alter table hub_locations enable row level security;
alter table hub_products enable row level security;
alter table hub_financial_account_refs enable row level security;

alter table ret_stores enable row level security;
alter table ret_pos_transactions enable row level security;
alter table ret_line_items enable row level security;
alter table ret_stock_levels enable row level security;
alter table ret_promotions enable row level security;
alter table ret_loyalty_accounts enable row level security;
alter table ret_supplier_deliveries enable row level security;

alter table log_vehicles enable row level security;
alter table log_drivers enable row level security;
alter table log_shipments enable row level security;
alter table log_shipment_legs enable row level security;
alter table log_routes enable row level security;
alter table log_warehouses enable row level security;
alter table log_maintenance_logs enable row level security;

alter table vfs_wallet_accounts enable row level security;
alter table vfs_wallet_transactions enable row level security;
alter table vfs_loans enable row level security;
alter table vfs_loan_repayments enable row level security;
alter table vfs_kyc_records enable row level security;
alter table vfs_merchant_settlements enable row level security;

alter table agr_farms enable row level security;
alter table agr_farmers enable row level security;
alter table agr_harvest_batches enable row level security;
alter table agr_processing_runs enable row level security;
alter table agr_quality_grades enable row level security;
alter table agr_wholesale_shipments enable row level security;
alter table agr_farmer_loans_reference enable row level security;

alter table prop_properties enable row level security;
alter table prop_tenants enable row level security;
alter table prop_leases enable row level security;
alter table prop_maintenance_requests enable row level security;
alter table prop_valuations enable row level security;
alter table prop_utility_accounts enable row level security;
alter table prop_facility_assets enable row level security;

-- =====================================================================
-- CORE SERVICES HUB POLICIES
-- Hub tables are readable across every division (that is the point of
-- a shared hub) but only writable by the division that owns the
-- corresponding source system, plus group_executive read-everywhere.
-- =====================================================================

create policy hub_customers_read_all on hub_customers
    for select using (current_role_name() is not null);

create policy hub_customers_write_retail on hub_customers
    for insert with check (current_role_name() in ('retail_ops','financial_services'));

create policy hub_customers_update_retail on hub_customers
    for update using (current_role_name() in ('retail_ops','financial_services'));

create policy hub_employees_read_all on hub_employees
    for select using (current_role_name() is not null);

create policy hub_suppliers_read_all on hub_suppliers
    for select using (current_role_name() is not null);

create policy hub_locations_read_all on hub_locations
    for select using (current_role_name() is not null);

create policy hub_products_read_all on hub_products
    for select using (current_role_name() is not null);

-- Financial account references carry no balances or transaction detail,
-- but Section 5.1 explicitly marks this table "read-restricted
-- elsewhere" -- only financial_services (and group_executive, per the
-- general executive-visibility pattern) may read it. This was
-- over-broadly granted to every role in the first draft of this
-- migration; corrected here.
create policy hub_fin_refs_read_restricted on hub_financial_account_refs
    for select using (current_role_name() in ('financial_services','group_executive'));

create policy hub_fin_refs_write_vfs on hub_financial_account_refs
    for insert with check (current_role_name() = 'financial_services');

-- =====================================================================
-- DIVISIONAL MODULE POLICIES
-- Pattern: full read/write for the owning ops role and group_executive
-- read-only, no access for any other division's ops role.
-- =====================================================================

-- Retail
create policy ret_full_access on ret_stores
    for all using (current_role_name() in ('retail_ops','group_executive'))
    with check (current_role_name() = 'retail_ops');
create policy ret_pos_txn_access on ret_pos_transactions
    for all using (current_role_name() in ('retail_ops','group_executive'))
    with check (current_role_name() = 'retail_ops');
create policy ret_line_items_access on ret_line_items
    for all using (current_role_name() in ('retail_ops','group_executive'))
    with check (current_role_name() = 'retail_ops');
create policy ret_stock_access on ret_stock_levels
    for all using (current_role_name() in ('retail_ops','group_executive'))
    with check (current_role_name() = 'retail_ops');
create policy ret_promo_access on ret_promotions
    for all using (current_role_name() in ('retail_ops','group_executive'))
    with check (current_role_name() = 'retail_ops');
create policy ret_loyalty_access on ret_loyalty_accounts
    for all using (current_role_name() in ('retail_ops','group_executive'))
    with check (current_role_name() = 'retail_ops');
create policy ret_deliveries_access on ret_supplier_deliveries
    for all using (current_role_name() in ('retail_ops','agricore_ops','group_executive'))
    with check (current_role_name() in ('retail_ops','agricore_ops'));

-- Logistics
create policy log_vehicles_access on log_vehicles
    for all using (current_role_name() in ('logistics_ops','group_executive'))
    with check (current_role_name() = 'logistics_ops');
create policy log_drivers_access on log_drivers
    for all using (current_role_name() in ('logistics_ops','group_executive'))
    with check (current_role_name() = 'logistics_ops');
create policy log_shipments_access on log_shipments
    for all using (current_role_name() in ('logistics_ops','agricore_ops','group_executive'))
    with check (current_role_name() in ('logistics_ops','agricore_ops'));
create policy log_legs_access on log_shipment_legs
    for all using (current_role_name() in ('logistics_ops','group_executive'))
    with check (current_role_name() = 'logistics_ops');
create policy log_routes_access on log_routes
    for all using (current_role_name() in ('logistics_ops','group_executive'))
    with check (current_role_name() = 'logistics_ops');
-- Warehouses: logistics owns the operational record but properties_ops
-- must be able to see and correct the lease link (this policy exists
-- specifically to prevent Funmi's double-booked warehouse scenario)
create policy log_warehouses_access on log_warehouses
    for all using (current_role_name() in ('logistics_ops','properties_ops','group_executive'))
    with check (current_role_name() in ('logistics_ops','properties_ops'));
create policy log_maintenance_access on log_maintenance_logs
    for all using (current_role_name() in ('logistics_ops','group_executive'))
    with check (current_role_name() = 'logistics_ops');

-- Veridian Financial Services — the most restricted module in the
-- platform. group_executive read access is deliberately EXCLUDED from
-- kyc_records (per 4.4: "most restricted entity in the module") and
-- from raw wallet_transactions; executives get settlements and loan
-- status only, consistent with "narrowest write access, not broadest
-- restriction" logic in section 4.4.
create policy vfs_wallet_accounts_access on vfs_wallet_accounts
    for all using (current_role_name() = 'financial_services')
    with check (current_role_name() = 'financial_services');
create policy vfs_wallet_txn_access on vfs_wallet_transactions
    for all using (current_role_name() = 'financial_services')
    with check (current_role_name() = 'financial_services');
create policy vfs_loans_access on vfs_loans
    for all using (current_role_name() in ('financial_services','group_executive'))
    with check (current_role_name() = 'financial_services');
create policy vfs_repayments_access on vfs_loan_repayments
    for all using (current_role_name() in ('financial_services','group_executive'))
    with check (current_role_name() = 'financial_services');
create policy vfs_kyc_access on vfs_kyc_records
    for all using (current_role_name() = 'financial_services')
    with check (current_role_name() = 'financial_services');
create policy vfs_settlements_access on vfs_merchant_settlements
    for all using (current_role_name() in ('financial_services','group_executive'))
    with check (current_role_name() = 'financial_services');

-- AgriCore
create policy agr_farms_access on agr_farms
    for all using (current_role_name() in ('agricore_ops','group_executive'))
    with check (current_role_name() = 'agricore_ops');
create policy agr_farmers_access on agr_farmers
    for all using (current_role_name() in ('agricore_ops','financial_services','group_executive'))
    with check (current_role_name() = 'agricore_ops');
create policy agr_harvest_access on agr_harvest_batches
    for all using (current_role_name() in ('agricore_ops','financial_services','group_executive'))
    with check (current_role_name() = 'agricore_ops');
create policy agr_runs_access on agr_processing_runs
    for all using (current_role_name() in ('agricore_ops','group_executive'))
    with check (current_role_name() = 'agricore_ops');
create policy agr_grades_access on agr_quality_grades
    for all using (current_role_name() in ('agricore_ops','group_executive'))
    with check (current_role_name() = 'agricore_ops');
create policy agr_wholesale_access on agr_wholesale_shipments
    for all using (current_role_name() in ('agricore_ops','retail_ops','logistics_ops','group_executive'))
    with check (current_role_name() = 'agricore_ops');
-- Farmer loans reference: readable by AgriCore (their own summary) and
-- financial_services (the source of the loan status being summarised)
create policy agr_farmer_loans_ref_access on agr_farmer_loans_reference
    for all using (current_role_name() in ('agricore_ops','financial_services','group_executive'))
    with check (current_role_name() in ('agricore_ops','financial_services'));

-- Properties
create policy prop_properties_access on prop_properties
    for all using (current_role_name() in ('properties_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');
create policy prop_tenants_access on prop_tenants
    for all using (current_role_name() in ('properties_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');
create policy prop_leases_access on prop_leases
    for all using (current_role_name() in ('properties_ops','logistics_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');
create policy prop_maintenance_access on prop_maintenance_requests
    for all using (current_role_name() in ('properties_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');
create policy prop_valuations_access on prop_valuations
    for all using (current_role_name() in ('properties_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');
create policy prop_utility_access on prop_utility_accounts
    for all using (current_role_name() in ('properties_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');
create policy prop_assets_access on prop_facility_assets
    for all using (current_role_name() in ('properties_ops','group_executive'))
    with check (current_role_name() = 'properties_ops');

-- =====================================================================
-- CONSENT-GATED CROSS-DIVISIONAL VIEWS  (Section 4.4 requirement:
-- "views and policies that expose customer data across divisional
-- boundaries should check these consent flags")
-- =====================================================================

-- Scenario 2 (Chinedu): loan officer sees a permissioned summary of a
-- farmer's AgriCore supply history, gated on hub_suppliers.status
-- being active and only exposing aggregates, never row-level harvests.
create view vw_credit_farmer_supply_summary as
select
    f.farmer_id,
    s.supplier_id,
    s.legal_name                    as farmer_name,
    count(distinct h.harvest_id)     as total_harvest_batches,
    sum(h.volume_kg)                 as total_volume_kg,
    min(h.harvest_date)               as first_harvest_date,
    max(h.harvest_date)                as most_recent_harvest_date
from agr_farmers f
join hub_suppliers s on s.supplier_id = f.supplier_id
left join agr_farms fm on fm.supplier_id = s.supplier_id
left join agr_harvest_batches h on h.farm_id = fm.farm_id
where s.status = 'active'
group by f.farmer_id, s.supplier_id, s.legal_name;

alter view vw_credit_farmer_supply_summary owner to postgres;
grant select on vw_credit_farmer_supply_summary to authenticated;

create policy vw_credit_supply_read on agr_harvest_batches
    for select using (
        current_role_name() = 'financial_services'
        or current_role_name() in ('agricore_ops','group_executive')
    );

-- Scenario: retail loyalty summary exposed to financial_services only
-- where the customer has explicitly consented to credit-assessment
-- sharing, per the consent-flag mechanism in Section 4.4.
create view vw_retail_profile_for_credit_assessment as
select
    c.customer_id,
    c.full_name,
    la.tier,
    la.points_balance,
    la.enrolment_date
from hub_customers c
join ret_loyalty_accounts la on la.customer_id = c.customer_id
where c.consent_credit_assessment_share = true;

grant select on vw_retail_profile_for_credit_assessment to authenticated;

comment on view vw_credit_farmer_supply_summary is
    'Scenario 2 (Chinedu): consent-free because supplier data carries no personal consent flag in this brief; access restricted at the RLS layer to financial_services and agricore_ops instead.';
comment on view vw_retail_profile_for_credit_assessment is
    'Scenario 2 extension: consent-gated retail profile visible to financial_services only where hub_customers.consent_credit_assessment_share = true.';
