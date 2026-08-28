# Project Concord — Making Your Looker Studio Dashboard Look Professional

This takes your dashboard from functional to polished, in two parts:
**Part A** — global theme setup (do this once, it affects every page).
**Part B** — specific KPI additions and styling for each of your 5 pages.

The color scheme recommended below (navy `#1C2B4A` + purple `#5B3A7A`, with
division-specific accents) matches the ERD diagram and Word reports already
built for this project — using it here means your dashboard, your report,
and your diagrams all look like they came from one coherent team, not five
different tools with no shared visual identity.

---

## PART A — Global Theme Setup (do this first, once)

### A1. Set the report-wide theme

1. In Looker Studio, click **Theme and Layout** in the right-hand panel
   (if you don't see it, click anywhere on an empty part of the canvas first
   to deselect any chart)
2. Under **Theme**, scroll through the presets — pick one close to a dark
   navy or slate theme as your starting point (e.g. "Midnight" or "Slate"
   if available)
3. Click **Customize** (usually below the theme presets)
4. Set these colors specifically:
   - **Primary color**: `#1C2B4A` (dark navy — matches your ERD/reports)
   - **Secondary color**: `#5B3A7A` (purple accent)
   - **Background color**: `#FFFFFF` or a very light grey `#F7F7F9`
   - **Text color**: `#2C2C2A` (near-black, easier to read than pure black)

### A2. Set a consistent font

1. Still in **Theme and Layout**, find **Font**
2. Pick one clean, professional font family — **Roboto** or **Google Sans**
   are safe, modern defaults already available in Looker Studio
3. This applies the same font everywhere, which alone makes a huge
   difference — mismatched fonts are one of the biggest reasons dashboards
   look amateur

### A3. Add a proper report header

1. Go to your first page (Scenario 1)
2. **Insert → Text Box**, draw a wide bar across the very top of the page
3. Type: `PROJECT CONCORD — Executive Dashboard`
4. Select the text, set font size large (24–28pt), bold, color white
5. Select the text box itself (click its edge, not the text) → in the right
   panel find **Fill color** → set it to your navy `#1C2B4A`
6. **Copy this header box** (Ctrl+C) and **paste it (Ctrl+V) onto every
   other page**, editing just the title text on each (e.g. "Scenario 1 —
   AgriCore Supply Risk") — this single repeated element is what makes a
   multi-page report feel like one product instead of five separate charts

### A4. Add page navigation

1. On any page, **Insert → Page Navigation Control** (sometimes called
   "Page Navigation")
2. Draw it near your header — Looker Studio auto-generates buttons or a
   dropdown linking to all your pages
3. This is a genuinely important upgrade: it lets someone browse your
   whole dashboard without you clicking through it for them live

---

## PART B — Per-Scenario Upgrades

For each scenario below: new KPIs to add, and specific styling steps.

---

### Scenario 1 — Ngozi (AgriCore Supply Risk)

**New KPIs to add** (beyond your existing at-risk count):

1. **Total harvested volume (30 days)** — Scorecard, Metric: `harvested_volume_kg`,
   aggregation **Sum**, with a **Date Range** filter control set to last 30 days
2. **Average days until expected delivery** — this needs a calculated field:
   - Click **Add a field** (bottom of the data panel, or **Resource → Manage
     added data sources → Edit → Add a Field**)
   - Name it `days_until_delivery`
   - Formula: `DATE_DIFF(delivery_expected_date, CURRENT_DATE())`
   - Use this as a Scorecard metric, aggregation **Average**
3. **At-risk percentage** — a calculated field:
   - Name: `at_risk_pct`
   - Formula: `SUM(CASE WHEN is_at_risk THEN 1 ELSE 0 END) / COUNT(harvest_id)`
   - Format this field: click it in the field list → **Type** → **Percent**

**Styling steps:**
1. Select your existing scorecard → right panel → **Style** tab
2. Under **Background**, set a light tint of your accent color (for
   AgriCore, use olive green `#3F6B2B` at low opacity — click the color
   swatch, drag the opacity slider down to ~10%)
3. Under **Comparison metric** (if shown), you can optionally compare
   against a prior period — leave off if you don't have historical
   comparison data
4. For your detail table: select it → **Style** tab → turn on **Alternate
   row colors** (usually a toggle) — this alone makes tables far easier
   to scan
5. Add **conditional formatting** on the `delivery_status` column: Style
   tab → **Conditional formatting** → **Add** → apply to `delivery_status`
   → set rule: text is `delayed` → background color red-tint, text is
   `received` → background color green-tint

---

### Scenario 2 — Chinedu (Farmer Credit Summary)

**New KPIs to add:**

1. **Total active loan book value** — Scorecard, Metric: `principal_amount`,
   filter: `loan_status = active`, aggregation **Sum**
2. **Average loan size** — same filter, aggregation **Average**
3. **Average farmer tenure** — calculated field:
   - Name: `years_supplying`
   - Formula: `DATE_DIFF(CURRENT_DATE(), first_harvest_date, YEAR)`
   - Scorecard, aggregation **Average**
4. **Loan status breakdown** — add a **Donut chart**: Dimension `loan_status`,
   Metric: Record Count — gives an at-a-glance view of pending vs active vs
   repaid vs defaulted, which a loan officer would actually want to see

**Styling steps:**
1. Use red/burgundy accent tint for this page's scorecards (`#8C2F39` at
   low opacity) — matches the VFS module color from your ERD
2. On the farmer table, apply a **data bar** style to `total_volume_kg` if
   available (Style tab → look for "Show as bar" or similar under the
   column's format options) — this turns the raw number into a small
   in-cell bar chart, an easy way to make a plain table feel more like a
   BI tool
3. Format `principal_amount` as currency: click the field → **Type** →
   **Currency (NGN)** — right now it likely just shows a plain number,
   which reads as unfinished

---

### Scenario 3 — Funmi (Warehouse & Lease Status)

**New KPIs to add:**

1. **Occupancy rate** — calculated field:
   - Name: `occupancy_pct`
   - Formula: `SUM(CASE WHEN is_current THEN 1 ELSE 0 END) / COUNT(warehouse_id)`
   - Format as **Percent**
2. **Leases expiring within 30 days** — Scorecard with a filter:
   - Create a filter: `end_date` **Date is in the next** `30` **days**
   - Apply to a Scorecard counting `lease_id`
3. **Average monthly rent** — if `monthly_rent` is available in this view
   (check your `fact_warehouse_lease_status` columns) — Scorecard, Average

**Styling steps:**
1. Purple accent tint (`#5B3A7A`) for this page, matching Properties'
   ERD color
2. You already have conditional formatting flagging leases expiring soon
   from before — extend it: add a second rule, `end_date` **in the past**
   → red background, meaning an already-expired lease still showing as
   active gets visually flagged as a data-quality alert
3. Add a **Geo map** if you have city-level data available: **Add a
   chart → Map (Geo chart)**, Dimension: `city`, Metric: Record Count —
   gives a genuinely different, more visual way to show warehouse spread
   across your operating regions

---

### Scenario 4 — Adaeze (Consolidated Revenue)

**New KPIs to add:**

1. **Revenue growth vs prior period** — on your existing revenue scorecard,
   right panel → look for **Comparison date range** → set it to compare
   against the previous period. Looker Studio will automatically show a
   small up/down arrow with percentage change — this single feature is
   the most "executive dashboard" looking thing you can add
2. **Best-performing division (this period)** — Scorecard, Metric:
   `revenue`, but change **Aggregation** isn't enough alone — instead use
   a Table sorted by revenue descending with just 1 row shown (Style tab
   → **Rows per page** → 1), Dimension `division_id`
3. **Total transactions (all divisions)** — Scorecard, Metric:
   `transaction_count`, Sum

**Styling steps:**
1. This is your "headline" page — make the top row of scorecards larger
   and bolder than other pages (Style tab → increase font size on the
   number, ~36–40pt)
2. On your stacked time series chart: Style tab → check **Show data
   labels** for cleaner readability, and set a distinct color per division
   in **Series colors** — use your established palette: Retail teal
   `#1F5F7A`, Logistics green `#2F6D5C`, VFS red `#8C2F39`
3. Keep your existing disclosure text box on the logistics proxy — but
   style it distinctly: light grey background, small italic font, so it
   reads clearly as a footnote rather than competing visually with the
   real numbers

---

### Bonus Page — Divisional Sales Overview

**New KPIs to add:**

1. **Total units sold** — Scorecard, Metric: `quantity`, Sum
2. **Average basket size (revenue per transaction)** — calculated field:
   - Name: `avg_basket_value`
   - Formula: `SUM(line_revenue) / COUNT(DISTINCT transaction_id)`
   - Format as Currency
3. **Top product category** — same single-row-table trick as Scenario 4's
   "best division" KPI, sorted by `line_revenue` descending

**Styling steps:**
1. Teal accent (`#1F5F7A`) matching Retail's ERD color
2. On your bar chart (revenue by category): Style tab → **Sort** should
   already be descending — additionally turn on **Show data labels** so
   exact values are visible without hovering
3. On your pie chart (store format split): Style tab → check **Show
   percentage** so each slice displays its share directly, not just color

---

## Quick checklist once you're done

- [ ] Same header bar, same colors, on every page
- [ ] Every currency number formatted as currency, not a raw number
- [ ] Every percentage formatted as a percent, not a decimal
- [ ] At least one comparison/trend indicator (Scenario 4's growth arrow)
- [ ] Conditional formatting on at least Scenario 1 and Scenario 3
- [ ] Page navigation control so the report is browsable without you
      clicking through it live

This is genuinely a few hours of work across 5 pages, not a five-minute
job — but it's the difference between "we connected some charts to BigQuery"
and "we built an executive product," which is exactly the impression worth
leaving with Adaeze and Tobenna in your presentation.
