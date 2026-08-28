"""
Project Concord | Synthetic Data Generator
===========================================
Generates realistic synthetic data for all 40 tables in 001_schema.sql,
at volumes calibrated within the ranges specified in Section 5.4 of the
brief, with the deliberate cross-divisional overlaps the brief requires:

  - a meaningful proportion of AgriCore farmers also hold VFS loans
  - a meaningful proportion of retail loyalty customers also hold a
    VFS wallet account

Reproducibility: a fixed random seed (42) means re-running this script
produces byte-identical output, satisfying Section 4.6's requirement
that data generation be "reproducible and re-runnable against a
freshly migrated, empty schema."

Output: one CSV per table in ./synthetic_data/, ordered so that a
plain `\copy` load in FK-dependency order (see 003_load_data.sql)
will not violate any foreign key.
"""

import numpy as np
import pandas as pd
from faker import Faker
from pathlib import Path
import uuid
import datetime

SEED = 42
rng = np.random.default_rng(SEED)
fake = Faker()
Faker.seed(SEED)

OUT = Path("synthetic_data")
OUT.mkdir(exist_ok=True)

def new_id(n):
    return [str(uuid.uuid4()) for _ in range(n)]

def save(df, name):
    df.to_csv(OUT / f"{name}.csv", index=False)
    print(f"  {name:32s} {len(df):>9,} rows")

# Simulation window: eight weeks, matching the brief's own eight-week
# engagement horizon, used as the "one to two months" transaction
# window Section 5.4 calls for.
WINDOW_START = datetime.date(2026, 5, 1)
WINDOW_DAYS = 56
def random_dates(n, start=WINDOW_START, days=WINDOW_DAYS, weight_weekday=True):
    offsets = rng.integers(0, days, size=n)
    dates = np.array([start + datetime.timedelta(int(o)) for o in offsets])
    return dates

COUNTRY_WEIGHTS = {"Nigeria": 0.80, "Ghana": 0.12, "Kenya": 0.08}
COUNTRY_CODES = {"Nigeria": "NG", "Ghana": "GH", "Kenya": "KE"}
CITIES = {
    "Nigeria": ["Lagos","Kano","Ibadan","Enugu","Kaduna","Abuja","Port Harcourt"],
    "Ghana": ["Accra","Kumasi","Tamale"],
    "Kenya": ["Nairobi","Mombasa","Kisumu"],
}

print("=" * 70)
print("PROJECT CONCORD — SYNTHETIC DATA GENERATION")
print("=" * 70)

# =====================================================================
# CORE SERVICES HUB
# =====================================================================
print("\n[HUB]")

N_CUSTOMERS = 45_000
customer_id = new_id(N_CUSTOMERS)
countries = rng.choice(list(COUNTRY_WEIGHTS), size=N_CUSTOMERS, p=list(COUNTRY_WEIGHTS.values()))
consent_credit = rng.random(N_CUSTOMERS) < 0.55       # 55% consent to credit-assessment sharing
consent_retail = rng.random(N_CUSTOMERS) < 0.85       # 85% consent to retail personalisation
consent_marketing = rng.random(N_CUSTOMERS) < 0.60
hub_customers = pd.DataFrame({
    "customer_id": customer_id,
    "full_name": [fake.name() for _ in range(N_CUSTOMERS)],
    "date_of_birth": [fake.date_of_birth(minimum_age=18, maximum_age=75) for _ in range(N_CUSTOMERS)],
    "primary_contact": [fake.phone_number() for _ in range(N_CUSTOMERS)],
    "registered_country": countries,
    "consent_retail_personalisation": consent_retail,
    "consent_credit_assessment_share": consent_credit,
    "consent_cross_div_marketing": consent_marketing,
    "created_date": random_dates(N_CUSTOMERS, start=datetime.date(2019,1,1), days=2700),
})
save(hub_customers, "hub_customers")

N_EMPLOYEES = 2_000
DIVISIONS = ["meridian_retail","concord_logistics","veridian_financial_services",
             "agricore","veridian_properties","group_functions"]
DIVISION_WEIGHTS = [0.42, 0.19, 0.09, 0.23, 0.02, 0.05]  # roughly matches headcount table in 1.5
employee_id = new_id(N_EMPLOYEES)
employee_division = rng.choice(DIVISIONS, size=N_EMPLOYEES, p=DIVISION_WEIGHTS)
hub_employees = pd.DataFrame({
    "employee_id": employee_id,
    "full_name": [fake.name() for _ in range(N_EMPLOYEES)],
    "division_id": employee_division,
    "role_title": rng.choice(
        ["Store Assistant","Store Manager","Dispatcher","Driver","Loan Officer",
         "Field Agent","Facilities Coordinator","Analyst","Operations Lead","Clerk"],
        size=N_EMPLOYEES),
    "employment_status": rng.choice(["active","active","active","on_leave","terminated"], size=N_EMPLOYEES),
    "hire_date": random_dates(N_EMPLOYEES, start=datetime.date(2010,1,1), days=6000),
    "reports_to": [None] * N_EMPLOYEES,  # simple hierarchy omitted for synthetic build
})
save(hub_employees, "hub_employees")

# Suppliers: weighted heavily toward AgriCore's farmer network, per 5.4
N_SUPPLIERS = 9_000
N_FARMERS = 7_000
supplier_types = (["farmer"] * N_FARMERS
                   + ["retail_vendor"] * 1_200
                   + ["logistics_vendor"] * 500
                   + ["general"] * (N_SUPPLIERS - N_FARMERS - 1_200 - 500))
rng.shuffle(supplier_types)
supplier_id = new_id(N_SUPPLIERS)
hub_suppliers = pd.DataFrame({
    "supplier_id": supplier_id,
    "legal_name": [fake.name() if t == "farmer" else fake.company() for t in supplier_types],
    "supplier_type": supplier_types,
    "primary_division_id": ["agricore" if t == "farmer" else rng.choice(["meridian_retail","concord_logistics"]) for t in supplier_types],
    "onboarding_date": random_dates(N_SUPPLIERS, start=datetime.date(2010,1,1), days=6000),
    "status": rng.choice(["active","active","active","inactive"], size=N_SUPPLIERS),
})
save(hub_suppliers, "hub_suppliers")
farmer_supplier_ids = hub_suppliers.loc[hub_suppliers.supplier_type == "farmer", "supplier_id"].tolist()

# Locations: one per store / warehouse / farm / facility / property / office
N_STORES, N_WAREHOUSES, N_FARM_LOCATIONS = 68, 6, 8_500
N_FACILITIES, N_PROPERTIES, N_OFFICES = 4, 94, 10
location_defs = (
    [("store", N_STORES)] + [("warehouse", N_WAREHOUSES)] + [("farm", N_FARM_LOCATIONS)]
    + [("processing_facility", N_FACILITIES)] + [("property", N_PROPERTIES)] + [("office", N_OFFICES)]
)
loc_rows = []
for site_type, n in location_defs:
    for _ in range(n):
        country = rng.choice(list(COUNTRY_WEIGHTS), p=list(COUNTRY_WEIGHTS.values()))
        loc_rows.append({
            "location_id": str(uuid.uuid4()),
            "site_name": f"{site_type.replace('_',' ').title()} - {fake.city()}",
            "site_type": site_type,
            "address": fake.street_address(),
            "city": rng.choice(CITIES[country]),
            "country_code": COUNTRY_CODES[country],
            "latitude": round(rng.uniform(4.0, 13.5), 6),
            "longitude": round(rng.uniform(-3.5, 14.5), 6),
        })
hub_locations = pd.DataFrame(loc_rows)
save(hub_locations, "hub_locations")
loc_by_type = {t: hub_locations.loc[hub_locations.site_type == t, "location_id"].tolist()
               for t in ["store","warehouse","farm","processing_facility","property","office"]}

# Products
CATEGORIES = ["Grain","Vegetable","Fruit","Packaged Goods","Household","Dairy","Beverage"]
N_PRODUCTS = 220
hub_products = pd.DataFrame({
    "product_id": new_id(N_PRODUCTS),
    "product_name": [fake.word().title() + " " + rng.choice(["Pack","Bag","Crate","Bottle","Box"]) for _ in range(N_PRODUCTS)],
    "category": rng.choice(CATEGORIES, size=N_PRODUCTS),
    "unit_of_measure": rng.choice(["kg","litre","unit","crate"], size=N_PRODUCTS),
    "primary_division_id": rng.choice(["meridian_retail","agricore"], size=N_PRODUCTS, p=[0.6, 0.4]),
    "is_active": rng.random(N_PRODUCTS) < 0.92,
})
save(hub_products, "hub_products")

# Financial account refs: created for customers who will hold a wallet
# (drawn from the loyalty-overlap pool built below), so this must run
# after we decide wallet ownership. Placeholder built after VFS section.

# =====================================================================
# RETAIL MODULE
# =====================================================================
print("\n[RETAIL]")

ret_stores = pd.DataFrame({
    "store_id": new_id(N_STORES),
    "location_id": loc_by_type["store"],
    "store_format": rng.choice(["large_format","neighbourhood","online"], size=N_STORES, p=[0.35, 0.55, 0.10]),
    "opening_date": random_dates(N_STORES, start=datetime.date(2012,1,1), days=5000),
    "manager_employee_id": rng.choice(
        hub_employees.loc[hub_employees.division_id == "meridian_retail", "employee_id"], size=N_STORES),
})
save(ret_stores, "ret_stores")

N_POS = 500_000
# Day-of-week weighting: retail volume peaks Fri/Sat, per realistic pattern
txn_dates = random_dates(N_POS)
weekday = pd.to_datetime(txn_dates).weekday
dow_weight = np.where(np.isin(weekday, [4, 5]), 1.4, 1.0)  # Fri/Sat busier
keep_mask = rng.random(N_POS) < (dow_weight / dow_weight.max())
store_pick = rng.choice(ret_stores["store_id"], size=N_POS)
customer_pick = rng.choice(hub_customers["customer_id"], size=N_POS)
# ~20% of transactions are walk-ins with no captured customer identity
customer_pick = np.where(rng.random(N_POS) < 0.20, None, customer_pick)
ret_pos_transactions = pd.DataFrame({
    "transaction_id": new_id(N_POS),
    "store_id": store_pick,
    "customer_id": customer_pick,
    "transaction_date": [datetime.datetime.combine(d, datetime.time(int(h), int(m)))
                          for d, h, m in zip(txn_dates, rng.integers(7, 21, N_POS), rng.integers(0, 59, N_POS))],
    "total_amount": np.round(rng.gamma(3.0, 1800, N_POS), 2),
    "payment_method": rng.choice(["cash","card","wallet","other"], size=N_POS, p=[0.35, 0.25, 0.35, 0.05]),
})
save(ret_pos_transactions, "ret_pos_transactions")

avg_items = rng.integers(1, 5, N_POS)  # 1-4 line items per transaction
line_txn_ids = np.repeat(ret_pos_transactions["transaction_id"].values, avg_items)
N_LINES = len(line_txn_ids)
ret_line_items = pd.DataFrame({
    "line_item_id": new_id(N_LINES),
    "transaction_id": line_txn_ids,
    "product_id": rng.choice(hub_products["product_id"], size=N_LINES),
    "quantity": rng.integers(1, 8, N_LINES),
    "unit_price": np.round(rng.gamma(2.0, 350, N_LINES), 2),
})
save(ret_line_items, "ret_line_items")

stock_pairs = [(s, p) for s in ret_stores["store_id"] for p in rng.choice(hub_products["product_id"], size=150, replace=False)]
ret_stock_levels = pd.DataFrame(stock_pairs, columns=["store_id", "product_id"])
ret_stock_levels["stock_id"] = new_id(len(ret_stock_levels))
ret_stock_levels["quantity_on_hand"] = rng.integers(0, 500, len(ret_stock_levels))
ret_stock_levels["last_counted_date"] = random_dates(len(ret_stock_levels))
ret_stock_levels = ret_stock_levels[["stock_id","store_id","product_id","quantity_on_hand","last_counted_date"]]
save(ret_stock_levels, "ret_stock_levels")

N_PROMOS = 150
ret_promotions = pd.DataFrame({
    "promotion_id": new_id(N_PROMOS),
    "product_id": rng.choice(hub_products["product_id"], size=N_PROMOS),
    "discount_type": rng.choice(["percentage","fixed_amount"], size=N_PROMOS),
    "start_date": (starts := random_dates(N_PROMOS)),
})
ret_promotions["end_date"] = [s + datetime.timedelta(int(d)) for s, d in zip(starts, rng.integers(3, 21, N_PROMOS))]
save(ret_promotions, "ret_promotions")

# Loyalty accounts — the overlap pool used later for wallet ownership
loyalty_customer_pool = rng.choice(hub_customers["customer_id"], size=32_000, replace=False)
loyalty_rows = []
for cust in loyalty_customer_pool:
    n_formats = 1 if rng.random() < 0.9 else 2
    formats = rng.choice(["large_format","neighbourhood","online"], size=n_formats, replace=False)
    for fmt in formats:
        loyalty_rows.append({
            "loyalty_id": str(uuid.uuid4()),
            "customer_id": cust,
            "store_format": fmt,
            "tier": rng.choice(["bronze","silver","gold","platinum"], p=[0.5, 0.3, 0.15, 0.05]),
            "points_balance": int(rng.integers(0, 20_000)),
            "enrolment_date": random_dates(1, start=datetime.date(2018,1,1), days=3000)[0],
        })
ret_loyalty_accounts = pd.DataFrame(loyalty_rows)
save(ret_loyalty_accounts, "ret_loyalty_accounts")

N_DELIVERIES = 5_000
non_farmer_or_farmer_suppliers = hub_suppliers["supplier_id"].tolist()
ret_supplier_deliveries = pd.DataFrame({
    "delivery_id": new_id(N_DELIVERIES),
    "supplier_id": rng.choice(non_farmer_or_farmer_suppliers, size=N_DELIVERIES),
    "store_id": rng.choice(ret_stores["store_id"], size=N_DELIVERIES),
    "expected_date": (exp := random_dates(N_DELIVERIES)),
})
status_choice = rng.choice(["scheduled","in_transit","received","delayed","cancelled"],
                            size=N_DELIVERIES, p=[0.1, 0.1, 0.65, 0.1, 0.05])
ret_supplier_deliveries["received_date"] = [
    d + datetime.timedelta(int(rng.integers(0, 3))) if s == "received" else None
    for d, s in zip(exp, status_choice)
]
ret_supplier_deliveries["status"] = status_choice
save(ret_supplier_deliveries, "ret_supplier_deliveries")

# =====================================================================
# LOGISTICS MODULE
# =====================================================================
print("\n[LOGISTICS]")

N_VEHICLES = 310
log_vehicles = pd.DataFrame({
    "vehicle_id": new_id(N_VEHICLES),
    "registration_number": [f"VCH-{i:05d}-{rng.choice(list('ABCDEFGH'))}" for i in range(N_VEHICLES)],
    "vehicle_type": rng.choice(["van","truck"], size=N_VEHICLES, p=[0.4, 0.6]),
    "capacity_kg": np.round(rng.uniform(500, 15000, N_VEHICLES), 2),
    "status": rng.choice(["active","active","active","maintenance","retired"], size=N_VEHICLES),
})
save(log_vehicles, "log_vehicles")

logistics_employees = hub_employees.loc[hub_employees.division_id == "concord_logistics", "employee_id"].tolist()
driver_employee_ids = rng.choice(logistics_employees, size=min(180, len(logistics_employees)), replace=False)
log_drivers = pd.DataFrame({
    "driver_id": new_id(len(driver_employee_ids)),
    "employee_id": driver_employee_ids,
    "licence_number": [fake.bothify("DL-########") for _ in driver_employee_ids],
    "licence_expiry": random_dates(len(driver_employee_ids), start=datetime.date(2026,6,1), days=1500),
})
save(log_drivers, "log_drivers")

N_SHIPMENTS = 20_000
all_locations = hub_locations["location_id"].tolist()
origin = rng.choice(all_locations, size=N_SHIPMENTS)
destination = rng.choice(all_locations, size=N_SHIPMENTS)
same = origin == destination
destination[same] = rng.choice(all_locations, size=same.sum())
log_shipments = pd.DataFrame({
    "shipment_id": new_id(N_SHIPMENTS),
    "origin_location_id": origin,
    "destination_location_id": destination,
    "client_type": rng.choice(["internal","third_party"], size=N_SHIPMENTS, p=[0.55, 0.45]),
    "status": rng.choice(["planned","in_transit","delivered","delayed","cancelled"],
                          size=N_SHIPMENTS, p=[0.05, 0.10, 0.75, 0.08, 0.02]),
})
save(log_shipments, "log_shipments")

N_LEGS = int(N_SHIPMENTS * 1.1)
leg_shipment_ids = rng.choice(log_shipments["shipment_id"], size=N_LEGS)
dep_dates = random_dates(N_LEGS)
log_shipment_legs = pd.DataFrame({
    "leg_id": new_id(N_LEGS),
    "shipment_id": leg_shipment_ids,
    "vehicle_id": rng.choice(log_vehicles["vehicle_id"], size=N_LEGS),
    "driver_id": rng.choice(log_drivers["driver_id"], size=N_LEGS),
    "departure_time": [datetime.datetime.combine(d, datetime.time(int(h))) for d, h in zip(dep_dates, rng.integers(5, 20, N_LEGS))],
})
log_shipment_legs["arrival_time"] = log_shipment_legs["departure_time"] + pd.to_timedelta(rng.integers(1, 30, N_LEGS), unit="h")
save(log_shipment_legs, "log_shipment_legs")

N_ROUTES = 40
log_routes = pd.DataFrame({
    "route_id": new_id(N_ROUTES),
    "route_name": [f"Route {i+1}" for i in range(N_ROUTES)],
    "origin_location_id": rng.choice(all_locations, size=N_ROUTES),
    "destination_location_id": rng.choice(all_locations, size=N_ROUTES),
    "distance_km": np.round(rng.uniform(5, 900, N_ROUTES), 2),
})
save(log_routes, "log_routes")

log_warehouses = pd.DataFrame({
    "warehouse_id": new_id(N_WAREHOUSES),
    "location_id": loc_by_type["warehouse"],
    "capacity_units": rng.integers(500, 20000, N_WAREHOUSES),
    "leased_from_property_id": [None] * N_WAREHOUSES,  # filled in Properties section
})

N_MAINT = 1_200
log_maintenance_logs = pd.DataFrame({
    "maintenance_id": new_id(N_MAINT),
    "vehicle_id": rng.choice(log_vehicles["vehicle_id"], size=N_MAINT),
    "service_date": random_dates(N_MAINT, start=datetime.date(2024,1,1), days=900),
    "cost": np.round(rng.gamma(2.0, 15000, N_MAINT), 2),
    "description": rng.choice(["Routine service","Tyre replacement","Brake repair","Engine diagnostic","Bodywork"], size=N_MAINT),
})
save(log_maintenance_logs, "log_maintenance_logs")

# =====================================================================
# VERIDIAN FINANCIAL SERVICES MODULE
# =====================================================================
print("\n[VFS]")

# Deliberate overlap: wallet ownership skews heavily toward the loyalty
# customer pool, per the Section 5.4 requirement that "a meaningful
# proportion of Meridian Retail's loyalty customers should also hold a
# VFS wallet account."
N_WALLETS = 28_000
loyalty_unique = pd.unique(ret_loyalty_accounts["customer_id"])
n_from_loyalty = int(N_WALLETS * 0.65)
wallet_from_loyalty = rng.choice(loyalty_unique, size=min(n_from_loyalty, len(loyalty_unique)), replace=False)
remaining_customers = np.setdiff1d(hub_customers["customer_id"].values, wallet_from_loyalty)
wallet_from_other = rng.choice(remaining_customers, size=N_WALLETS - len(wallet_from_loyalty), replace=False)
wallet_customer_ids = np.concatenate([wallet_from_loyalty, wallet_from_other])
rng.shuffle(wallet_customer_ids)

hub_financial_account_refs = pd.DataFrame({
    "account_ref_id": new_id(N_WALLETS),
    "customer_id": wallet_customer_ids,
    "account_type": "wallet",
    "account_status": rng.choice(["active","dormant","closed"], size=N_WALLETS, p=[0.85, 0.10, 0.05]),
    "opened_date": random_dates(N_WALLETS, start=datetime.date(2019,1,1), days=2700),
})
save(hub_financial_account_refs, "hub_financial_account_refs")

vfs_wallet_accounts = pd.DataFrame({
    "wallet_id": new_id(N_WALLETS),
    "customer_id": wallet_customer_ids,
    "account_ref_id": hub_financial_account_refs["account_ref_id"],
    "balance": np.round(rng.gamma(2.0, 15000, N_WALLETS), 2),
    "status": hub_financial_account_refs["account_status"].map(
        {"active": "active", "dormant": "suspended", "closed": "closed"}),
})
save(vfs_wallet_accounts, "vfs_wallet_accounts")

N_WALLET_TXN = 300_000
wtx_dates = random_dates(N_WALLET_TXN)
vfs_wallet_transactions = pd.DataFrame({
    "wallet_txn_id": new_id(N_WALLET_TXN),
    "wallet_id": rng.choice(vfs_wallet_accounts["wallet_id"], size=N_WALLET_TXN),
    "counterparty_type": rng.choice(["retail_pos","merchant","peer_transfer","utility_bill","loan_repayment"], size=N_WALLET_TXN),
    "amount": np.round(rng.normal(0, 8000, N_WALLET_TXN), 2),
    "transaction_date": [datetime.datetime.combine(d, datetime.time(int(h), int(m)))
                          for d, h, m in zip(wtx_dates, rng.integers(0, 23, N_WALLET_TXN), rng.integers(0, 59, N_WALLET_TXN))],
})
save(vfs_wallet_transactions, "vfs_wallet_transactions")

# Loans: personal (customer) + working capital (farmer supplier), with
# the required farmer/VFS overlap
N_LOANS_CUSTOMER = 2_000
N_LOANS_FARMER = 1_500
loan_customer_ids = rng.choice(wallet_customer_ids, size=N_LOANS_CUSTOMER, replace=False)
loan_farmer_supplier_ids = rng.choice(farmer_supplier_ids, size=N_LOANS_FARMER, replace=False)

vfs_loans = pd.DataFrame({
    "loan_id": new_id(N_LOANS_CUSTOMER + N_LOANS_FARMER),
    "borrower_customer_id": list(loan_customer_ids) + [None] * N_LOANS_FARMER,
    "borrower_supplier_id": [None] * N_LOANS_CUSTOMER + list(loan_farmer_supplier_ids),
    "principal_amount": np.round(rng.gamma(3.0, 60000, N_LOANS_CUSTOMER + N_LOANS_FARMER), 2),
    "status": rng.choice(["pending","active","repaid","defaulted"], size=N_LOANS_CUSTOMER + N_LOANS_FARMER, p=[0.1, 0.55, 0.3, 0.05]),
})
save(vfs_loans, "vfs_loans")

installments = rng.integers(3, 12, len(vfs_loans))
repay_loan_ids = np.repeat(vfs_loans["loan_id"].values, installments)
N_REPAY = len(repay_loan_ids)
due = random_dates(N_REPAY, start=datetime.date(2025,1,1), days=550)
amount_due = np.round(rng.gamma(2.0, 8000, N_REPAY), 2)
paid_mask = rng.random(N_REPAY) < 0.8
vfs_loan_repayments = pd.DataFrame({
    "repayment_id": new_id(N_REPAY),
    "loan_id": repay_loan_ids,
    "due_date": due,
    "amount_due": amount_due,
    "amount_paid": np.where(paid_mask, amount_due, 0),
    "paid_date": [d if p else None for d, p in zip(due, paid_mask)],
})
save(vfs_loan_repayments, "vfs_loan_repayments")

vfs_kyc_records = pd.DataFrame({
    "kyc_id": new_id(N_WALLETS),
    "customer_id": wallet_customer_ids,
    "verification_level": rng.choice(["tier1","tier2","tier3"], size=N_WALLETS, p=[0.3, 0.5, 0.2]),
    "verified_date": random_dates(N_WALLETS, start=datetime.date(2019,1,1), days=2700),
})
save(vfs_kyc_records, "vfs_kyc_records")

N_SETTLEMENTS = 600
vfs_merchant_settlements = pd.DataFrame({
    "settlement_id": new_id(N_SETTLEMENTS),
    "division_id": rng.choice(["meridian_retail","concord_logistics","agricore"], size=N_SETTLEMENTS),
    "settlement_date": random_dates(N_SETTLEMENTS),
    "total_amount": np.round(rng.gamma(3.0, 250000, N_SETTLEMENTS), 2),
})
save(vfs_merchant_settlements, "vfs_merchant_settlements")

# =====================================================================
# AGRICORE MODULE
# =====================================================================
print("\n[AGRICORE]")

agr_farmers = pd.DataFrame({
    "farmer_id": new_id(N_FARMERS),
    "supplier_id": farmer_supplier_ids,
    "registration_date": random_dates(N_FARMERS, start=datetime.date(2010,1,1), days=6000),
    "cooperative_name": rng.choice(
        ["Kaduna Smallholders Cooperative","Kano Grain Growers Union","Northern Farmers Alliance", None, None],
        size=N_FARMERS),
})
save(agr_farmers, "agr_farmers")

N_FARMS = 8_500
farm_supplier_choice = rng.choice(farmer_supplier_ids, size=N_FARMS)  # some farmers have >1 farm
agr_farms = pd.DataFrame({
    "farm_id": new_id(N_FARMS),
    "supplier_id": farm_supplier_choice,
    "location_id": loc_by_type["farm"],
    "size_hectares": np.round(rng.gamma(2.0, 3.5, N_FARMS), 2),
    "primary_crop": rng.choice(["Maize","Sorghum","Cowpea","Cassava","Rice"], size=N_FARMS),
})
save(agr_farms, "agr_farms")

N_HARVESTS = 8_000
# Seasonal weighting: harvest volume peaks in a single growing season window
harvest_dates = random_dates(N_HARVESTS, start=datetime.date(2026,3,1), days=120)
agr_harvest_batches = pd.DataFrame({
    "harvest_id": new_id(N_HARVESTS),
    "farm_id": rng.choice(agr_farms["farm_id"], size=N_HARVESTS),
    "product_id": rng.choice(hub_products.loc[hub_products.primary_division_id == "agricore", "product_id"], size=N_HARVESTS),
    "harvest_date": harvest_dates,
    "volume_kg": np.round(rng.gamma(3.0, 400, N_HARVESTS), 2),
    "field_agent_employee_id": rng.choice(
        hub_employees.loc[hub_employees.division_id == "agricore", "employee_id"], size=N_HARVESTS),
})
save(agr_harvest_batches, "agr_harvest_batches")

# Zero-to-many processing runs per batch: sample batches with replacement
# skewed so most batches get exactly 1 run, some get 0, a few get 2+
run_counts = rng.choice([0, 1, 1, 1, 2], size=N_HARVESTS)
run_harvest_ids = np.repeat(agr_harvest_batches["harvest_id"].values, run_counts)
N_RUNS = len(run_harvest_ids)
agr_processing_runs = pd.DataFrame({
    "run_id": new_id(N_RUNS),
    "harvest_id": run_harvest_ids,
    "facility_location_id": rng.choice(loc_by_type["processing_facility"], size=N_RUNS),
    "run_date": random_dates(N_RUNS, start=datetime.date(2026,3,1), days=130),
    "output_volume_kg": np.round(rng.gamma(2.8, 350, N_RUNS), 2),
})
save(agr_processing_runs, "agr_processing_runs")

agr_quality_grades = pd.DataFrame({
    "grade_id": new_id(N_RUNS),
    "run_id": agr_processing_runs["run_id"],
    "grade_level": rng.choice(["A","B","C","reject"], size=N_RUNS, p=[0.4, 0.35, 0.2, 0.05]),
    "moisture_content": np.round(rng.uniform(8, 18, N_RUNS), 2),
    "inspector_employee_id": rng.choice(
        hub_employees.loc[hub_employees.division_id == "agricore", "employee_id"], size=N_RUNS),
})
save(agr_quality_grades, "agr_quality_grades")

N_WHOLESALE = int(N_RUNS * 0.9)
wholesale_run_ids = rng.choice(agr_processing_runs["run_id"], size=N_WHOLESALE, replace=False)
agr_wholesale_shipments = pd.DataFrame({
    "wholesale_id": new_id(N_WHOLESALE),
    "run_id": wholesale_run_ids,
    "destination_type": rng.choice(["meridian_retail","external_client"], size=N_WHOLESALE, p=[0.75, 0.25]),
    "destination_id": new_id(N_WHOLESALE),
    "shipment_id": rng.choice(log_shipments["shipment_id"], size=N_WHOLESALE),
})
save(agr_wholesale_shipments, "agr_wholesale_shipments")

# Farmer loans reference: farmers with an active VFS loan get a real
# reference; a smaller additional group is referenced with no active
# loan, matching the nullable loan_id in the spec.
farmers_with_loans = agr_farmers.loc[agr_farmers.supplier_id.isin(loan_farmer_supplier_ids)]
loan_by_supplier = dict(zip(vfs_loans.loc[vfs_loans.borrower_supplier_id.notna(), "borrower_supplier_id"],
                             vfs_loans.loc[vfs_loans.borrower_supplier_id.notna(), "loan_id"]))
extra_farmers = agr_farmers.loc[~agr_farmers.supplier_id.isin(loan_farmer_supplier_ids)].sample(n=300, random_state=SEED)
ref_rows = []
for _, row in farmers_with_loans.iterrows():
    ref_rows.append({"reference_id": str(uuid.uuid4()), "farmer_id": row.farmer_id,
                      "loan_id": loan_by_supplier.get(row.supplier_id), "visible_summary_status": "active_loan"})
for _, row in extra_farmers.iterrows():
    ref_rows.append({"reference_id": str(uuid.uuid4()), "farmer_id": row.farmer_id,
                      "loan_id": None, "visible_summary_status": "no_active_loan"})
agr_farmer_loans_reference = pd.DataFrame(ref_rows)
save(agr_farmer_loans_reference, "agr_farmer_loans_reference")

# =====================================================================
# VERIDIAN PROPERTIES MODULE
# =====================================================================
print("\n[PROPERTIES]")

prop_properties = pd.DataFrame({
    "property_id": new_id(N_PROPERTIES),
    "location_id": loc_by_type["property"],
    "property_type": rng.choice(
        ["store_premises","warehouse_depot","processing_adjacent","commercial","residential"],
        size=N_PROPERTIES, p=[0.35, 0.2, 0.15, 0.2, 0.1]),
    "size_sqm": np.round(rng.gamma(3.0, 400, N_PROPERTIES), 2),
    "ownership_status": rng.choice(["owned","leased"], size=N_PROPERTIES, p=[0.4, 0.6]),
})
save(prop_properties, "prop_properties")

# Fix the deferred FK now that properties exist
warehouse_property_pool = prop_properties.loc[
    prop_properties.property_type == "warehouse_depot", "property_id"].tolist()
if len(warehouse_property_pool) < N_WAREHOUSES:
    warehouse_property_pool = (warehouse_property_pool * N_WAREHOUSES)[:N_WAREHOUSES]
log_warehouses["leased_from_property_id"] = rng.choice(warehouse_property_pool, size=N_WAREHOUSES, replace=False)
save(log_warehouses, "log_warehouses")

N_TENANTS = 120
tenant_type = rng.choice(["internal_division","external"], size=N_TENANTS, p=[0.4, 0.6])
prop_tenants = pd.DataFrame({
    "tenant_id": new_id(N_TENANTS),
    "tenant_type": tenant_type,
    "division_id": [rng.choice(DIVISIONS[:-1]) if t == "internal_division" else None for t in tenant_type],
    "external_tenant_name": [fake.company() if t == "external" else None for t in tenant_type],
})
save(prop_tenants, "prop_tenants")

# Leases are generated per tenant as a sequential, non-overlapping
# history: at most the LAST lease in a tenant's sequence is allowed to
# be "current" (end_date >= today). This matches the Section 5.3
# cardinality rule ("at most one active lease per tenant at any given
# time") that uidx_one_active_lease_per_tenant enforces in the schema
# -- generating leases independently at random would eventually
# violate that constraint, exactly as the first attempt at this
# script did.
REFERENCE_DATE = datetime.date(2026, 7, 16)
lease_rows = []
tenant_ids = prop_tenants["tenant_id"].tolist()
property_ids = prop_properties["property_id"].tolist()
target_leases = 300
leases_per_tenant = max(1, target_leases // len(tenant_ids))
for tenant_id in tenant_ids:
    n_leases = int(rng.integers(1, leases_per_tenant + 3))
    cursor = datetime.date(2018, 1, 1) + datetime.timedelta(days=int(rng.integers(0, 400)))
    for i in range(n_leases):
        duration_days = int(rng.integers(180, 5 * 365))
        start = cursor
        end = start + datetime.timedelta(days=duration_days)
        is_last = (i == n_leases - 1)
        if not is_last and end >= REFERENCE_DATE:
            # force historical leases to actually be historical
            end = REFERENCE_DATE - datetime.timedelta(days=int(rng.integers(30, 700)))
            if end <= start:
                end = start + datetime.timedelta(days=90)
        lease_rows.append({
            "lease_id": str(uuid.uuid4()),
            "property_id": rng.choice(property_ids),
            "tenant_id": tenant_id,
            "start_date": start,
            "end_date": end,
            "monthly_rent": round(float(rng.gamma(3.0, 250000)), 2),
        })
        cursor = end + datetime.timedelta(days=int(rng.integers(1, 60)))
        if cursor >= REFERENCE_DATE and not is_last:
            break
prop_leases = pd.DataFrame(lease_rows)
save(prop_leases, "prop_leases")

N_MAINT_REQ = 150
prop_maintenance_requests = pd.DataFrame({
    "request_id": new_id(N_MAINT_REQ),
    "property_id": rng.choice(prop_properties["property_id"], size=N_MAINT_REQ),
    "requested_date": (req_dates := random_dates(N_MAINT_REQ)),
    "category": rng.choice(["plumbing","electrical","structural","hvac","general"], size=N_MAINT_REQ),
})
req_status = rng.choice(["open","in_progress","resolved","cancelled"], size=N_MAINT_REQ, p=[0.2, 0.25, 0.5, 0.05])
prop_maintenance_requests["status"] = req_status
prop_maintenance_requests["resolved_date"] = [
    d + datetime.timedelta(int(rng.integers(1, 30))) if s == "resolved" else None
    for d, s in zip(req_dates, req_status)
]
save(prop_maintenance_requests, "prop_maintenance_requests")

N_VALUATIONS = 200
prop_valuations = pd.DataFrame({
    "valuation_id": new_id(N_VALUATIONS),
    "property_id": rng.choice(prop_properties["property_id"], size=N_VALUATIONS),
    "valuation_date": random_dates(N_VALUATIONS, start=datetime.date(2022,1,1), days=1600),
    "assessed_value": np.round(rng.gamma(3.0, 15_000_000, N_VALUATIONS), 2),
})
save(prop_valuations, "prop_valuations")

N_UTILITY = 220
prop_utility_accounts = pd.DataFrame({
    "utility_id": new_id(N_UTILITY),
    "property_id": rng.choice(prop_properties["property_id"], size=N_UTILITY),
    "utility_type": rng.choice(["electricity","water","waste","internet"], size=N_UTILITY),
    "provider_name": rng.choice(["Ikeja Electric","Lagos Water Corp","WasteCo","MTN Business"], size=N_UTILITY),
    "account_number": [fake.bothify("UTL-########") for _ in range(N_UTILITY)],
})
save(prop_utility_accounts, "prop_utility_accounts")

N_ASSETS = 300
prop_facility_assets = pd.DataFrame({
    "asset_id": new_id(N_ASSETS),
    "property_id": rng.choice(prop_properties["property_id"], size=N_ASSETS),
    "asset_type": rng.choice(["generator","hvac_unit","cold_room","fire_system","elevator"], size=N_ASSETS),
    "installed_date": random_dates(N_ASSETS, start=datetime.date(2015,1,1), days=4000),
    "condition_rating": rng.choice(["excellent","good","fair","poor"], size=N_ASSETS, p=[0.25, 0.45, 0.22, 0.08]),
})
save(prop_facility_assets, "prop_facility_assets")

print("\n" + "=" * 70)
total_rows = sum(len(pd.read_csv(f)) for f in OUT.glob("*.csv"))
print(f"DONE. {len(list(OUT.glob('*.csv')))} tables generated, {total_rows:,} total rows.")
print("=" * 70)
