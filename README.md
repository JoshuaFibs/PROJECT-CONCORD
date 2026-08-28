# Project Concord

**A unified data platform for Veridian Consolidated Holdings (VCH)**

Reference: VCH-PC-2026-01


## Overview

Veridian Consolidated Holdings operates five divisions — Meridian Retail, Concord Logistics, Veridian Financial Services (VFS), AgriCore, and Veridian Properties — across Nigeria, Ghana, and Kenya. Each division has historically run its own disconnected tech stack, with no shared way to identify the same customer, supplier, product, or location across the group. This fragmentation is estimated to cost the business 4–6% of consolidated annual revenue.

Project Concord is a deliberately-scoped data platform that solves this with a **hub-and-spoke schema**: one shared Core Services Hub of 6 entities, surrounded by 5 divisional modules, feeding an analytical layer built specifically to answer four real stakeholder problems.

Two prior attempts at this (2019, 2022) failed from scope creep. This build was scoped tightly around four concrete scenarios rather than a general-purpose data warehouse.

## The Four Scenarios

| Stakeholder | Division | Problem solved |
|---|---|---|
| **Ngozi** | Meridian Retail | Sees AgriCore supply shortfalls before shelves empty, instead of discovering them when a delivery fails to arrive |
| **Chinedu** | Veridian Financial Services | Sees a farmer's AgriCore supply history (with consent) when assessing credit, instead of only 2 years of banking data |
| **Funmi** | Concord Logistics | Sees accurate warehouse lease status from Properties, instead of discovering double-bookings on arrival |
| **Adaeze** | Group CEO | Sees same-day consolidated revenue across all divisions, instead of waiting on a 21-day manual close |

## Architecture

**OLTP layer — Supabase / PostgreSQL**
- **Core Services Hub** (6 shared tables): `hub_customers`, `hub_employees`, `hub_suppliers`, `hub_locations`, `hub_products`, `hub_financial_account_refs` — the single source of truth every division references, so the same customer, product, or site is never duplicated across systems.
- **5 divisional modules**: Retail (`ret_*`), Logistics (`log_*`), Financial Services (`vfs_*`), AgriCore (`agr_*`), Properties (`prop_*`) — each division's own operational tables, joined back to the hub via foreign keys.
- Row-Level Security (RLS) enforced across roles, so cross-division visibility is permissioned, not open by default.

**OLAP layer — BigQuery**
- A scheduled ELT pipeline curates 5 analytical fact tables from the OLTP layer: `fact_supply_signal`, `fact_farmer_credit_summary`, `fact_warehouse_lease_status`, `fact_daily_revenue_by_division`, `fact_retail_sales`.
- These fact tables — not the raw OLTP hub/module tables — are what the dashboards connect to.

**Dashboards — Power BI**
- One page per scenario (4) plus a Divisional Sales overview and a General Overview landing page.
- Standard layout: KPI cards + 2 supporting charts per page, DAX-driven, with methodology disclosures shown directly on the page rather than hidden.

## Key Design Decisions Worth Knowing

- **A farmer is modeled as a specialised kind of supplier** (`agr_farmers.supplier_id` → `hub_suppliers`), which is what makes it possible to trace a specific harvest through to a specific store's incoming delivery.
- **`hub_financial_account_refs` is a pointer only** — account type/status, never real balances — so other divisions can know a customer has a VFS relationship without VFS's actual financial data ever leaving VFS.
- **`agr_farmer_loans_reference`** exists as a deliberately thin, permissioned view of the AgriCore–VFS loan relationship (`visible_summary_status` only), rather than exposing raw loan tables directly.
- **One deliberate denormalisation**: `prop_leases.is_current` is stored directly rather than computed live, because PostgreSQL partial indexes can't reference `CURRENT_DATE`.
- **Logistics revenue is a modelled proxy** (shipment-leg count × placeholder rate), not real freight billing data — disclosed directly on the relevant dashboard, not just in this document.

## Repository Structure

```
project-concord/
├── database/           # Schema, ERD, data dictionary
├── elt-pipeline/        # ELT scripts, BigQuery view definitions
├── dashboards/           # Power BI (.pbix) and supporting assets
├── docs/                 # Project report, KPI/DAX reference, methodology notes
└── README.md
```

*(Adjust the above to match your actual folder layout.)*

## Team — The Concord Six

- Fiberesima Ibidabo Joshua (Lead)
- Godsfavour James
- Victor Umanah
- Ola Aulewon
- Kamsy Krystal
- Kachi

## Status

All four scenarios are live and demonstrated against real synthetic data, with dashboards built in Power BI. See `/docs` for the full project report, KPI/DAX reference, and methodology disclosures.
