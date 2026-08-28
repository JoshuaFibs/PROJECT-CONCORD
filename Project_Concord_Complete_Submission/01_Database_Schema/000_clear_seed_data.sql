-- =====================================================================
-- Project Concord | Clear seed data before loading full synthetic set
-- CASCADE lets Postgres resolve the full foreign-key dependency order
-- automatically -- you don't need to list tables in a specific order.
-- Safe to run even if some tables are already empty.
-- =====================================================================

truncate table
    hub_customers, hub_employees, hub_suppliers, hub_locations,
    hub_products, hub_financial_account_refs,
    ret_stores, ret_pos_transactions, ret_line_items, ret_stock_levels,
    ret_promotions, ret_loyalty_accounts, ret_supplier_deliveries,
    log_vehicles, log_drivers, log_shipments, log_shipment_legs,
    log_routes, log_warehouses, log_maintenance_logs,
    vfs_wallet_accounts, vfs_wallet_transactions, vfs_loans,
    vfs_loan_repayments, vfs_kyc_records, vfs_merchant_settlements,
    agr_farms, agr_farmers, agr_harvest_batches, agr_processing_runs,
    agr_quality_grades, agr_wholesale_shipments, agr_farmer_loans_reference,
    prop_properties, prop_tenants, prop_leases, prop_maintenance_requests,
    prop_valuations, prop_utility_accounts, prop_facility_assets
cascade;

-- Confirm every table is now empty
select relname, n_live_tup from pg_stat_user_tables
where relname != 'app_user_roles' order by relname;
