-- =====================================================================
-- Project Concord | 003_load_synthetic_data.sql
-- Loads synthetic_data/*.csv into the schema created by 001 + 002.
-- Order respects foreign key dependencies exactly.
-- Run from the directory containing synthetic_data/ (uses relative
-- paths via \copy, which is a psql client-side command — safe to run
-- from pgAdmin's Query Tool too, since pgAdmin also supports \copy
-- through its own file picker, or you can swap \copy for server-side
-- COPY with an absolute path if you prefer).
-- =====================================================================

\copy hub_customers from 'synthetic_data/hub_customers.csv' with (format csv, header true, null '')
\copy hub_employees from 'synthetic_data/hub_employees.csv' with (format csv, header true, null '')
\copy hub_suppliers from 'synthetic_data/hub_suppliers.csv' with (format csv, header true, null '')
\copy hub_locations from 'synthetic_data/hub_locations.csv' with (format csv, header true, null '')
\copy hub_products from 'synthetic_data/hub_products.csv' with (format csv, header true, null '')
\copy hub_financial_account_refs from 'synthetic_data/hub_financial_account_refs.csv' with (format csv, header true, null '')

\copy ret_stores from 'synthetic_data/ret_stores.csv' with (format csv, header true, null '')
\copy ret_pos_transactions from 'synthetic_data/ret_pos_transactions.csv' with (format csv, header true, null '')
\copy ret_line_items from 'synthetic_data/ret_line_items.csv' with (format csv, header true, null '')
\copy ret_stock_levels from 'synthetic_data/ret_stock_levels.csv' with (format csv, header true, null '')
\copy ret_promotions from 'synthetic_data/ret_promotions.csv' with (format csv, header true, null '')
\copy ret_loyalty_accounts from 'synthetic_data/ret_loyalty_accounts.csv' with (format csv, header true, null '')
\copy ret_supplier_deliveries from 'synthetic_data/ret_supplier_deliveries.csv' with (format csv, header true, null '')

\copy log_vehicles from 'synthetic_data/log_vehicles.csv' with (format csv, header true, null '')
\copy log_drivers from 'synthetic_data/log_drivers.csv' with (format csv, header true, null '')
\copy log_shipments from 'synthetic_data/log_shipments.csv' with (format csv, header true, null '')
\copy log_shipment_legs from 'synthetic_data/log_shipment_legs.csv' with (format csv, header true, null '')
\copy log_routes from 'synthetic_data/log_routes.csv' with (format csv, header true, null '')
\copy log_maintenance_logs from 'synthetic_data/log_maintenance_logs.csv' with (format csv, header true, null '')

\copy vfs_wallet_accounts from 'synthetic_data/vfs_wallet_accounts.csv' with (format csv, header true, null '')
\copy vfs_wallet_transactions from 'synthetic_data/vfs_wallet_transactions.csv' with (format csv, header true, null '')
\copy vfs_loans from 'synthetic_data/vfs_loans.csv' with (format csv, header true, null '')
\copy vfs_loan_repayments from 'synthetic_data/vfs_loan_repayments.csv' with (format csv, header true, null '')
\copy vfs_kyc_records from 'synthetic_data/vfs_kyc_records.csv' with (format csv, header true, null '')
\copy vfs_merchant_settlements from 'synthetic_data/vfs_merchant_settlements.csv' with (format csv, header true, null '')

\copy agr_farmers from 'synthetic_data/agr_farmers.csv' with (format csv, header true, null '')
\copy agr_farms from 'synthetic_data/agr_farms.csv' with (format csv, header true, null '')
\copy agr_harvest_batches from 'synthetic_data/agr_harvest_batches.csv' with (format csv, header true, null '')
\copy agr_processing_runs from 'synthetic_data/agr_processing_runs.csv' with (format csv, header true, null '')
\copy agr_quality_grades from 'synthetic_data/agr_quality_grades.csv' with (format csv, header true, null '')
\copy agr_wholesale_shipments from 'synthetic_data/agr_wholesale_shipments.csv' with (format csv, header true, null '')
\copy agr_farmer_loans_reference from 'synthetic_data/agr_farmer_loans_reference.csv' with (format csv, header true, null '')

\copy prop_properties from 'synthetic_data/prop_properties.csv' with (format csv, header true, null '')
\copy log_warehouses from 'synthetic_data/log_warehouses.csv' with (format csv, header true, null '')
\copy prop_tenants from 'synthetic_data/prop_tenants.csv' with (format csv, header true, null '')
\copy prop_leases (lease_id, property_id, tenant_id, start_date, end_date, monthly_rent) from 'synthetic_data/prop_leases.csv' with (format csv, header true, null '')
\copy prop_maintenance_requests from 'synthetic_data/prop_maintenance_requests.csv' with (format csv, header true, null '')
\copy prop_valuations from 'synthetic_data/prop_valuations.csv' with (format csv, header true, null '')
\copy prop_utility_accounts from 'synthetic_data/prop_utility_accounts.csv' with (format csv, header true, null '')
\copy prop_facility_assets from 'synthetic_data/prop_facility_assets.csv' with (format csv, header true, null '')
