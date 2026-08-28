# Project Concord — Complete Submission Package
Prepared by: The Concord Six

This folder contains only FINAL, correct versions of every project file.
Earlier draft or superseded versions of files that were revised during
the project have been deliberately left out of this package so there is
no ambiguity about which file is the right one.

## Folder-by-folder contents

### 01_Database_Schema/
- project_concord_full_database.sql — the complete, final schema (40
  tables) + Row Level Security (44 policies), consolidated into one
  file. This supersedes any earlier separate 001_schema.sql /
  002_roles_and_rls.sql files you may still have lying around — those
  are now merged into this single file and should be treated as
  outdated if found elsewhere.
- 000_clear_seed_data.sql — utility script to reset the database.
- 004_seed_10_rows.sql — the 10-row proof-of-concept seed used to
  verify the schema before loading full data.

### 02_Synthetic_Data/
- synthetic_data_500k.zip — THE ACTUAL DATASET USED in the final,
  deployed project (~506,775 rows across all 40 tables). If you find
  an older file called synthetic_data.zip (much larger, ~117MB)
  anywhere on your PC, that was an earlier ~2.37 million row attempt
  abandoned after a Supabase infrastructure timeout — do not submit
  that one.
- 003_load_synthetic_data.sql — the script that loads the CSVs above.
- generate_synthetic_data.py — the reproducible generation method.
  Note: this script's volume constants target the original larger
  dataset; the actual deployed data was generated from a
  proportionally scaled-down version of this same script (documented
  in Project_Concord_Complete_Report.docx, Section 5) after a real
  infrastructure constraint was hit. The methodology is identical;
  only the row-count targets differ.

### 03_ELT_Pipeline/
- 005_elt_curated_views.sql — FINAL version. Includes all 5 divisions
  (an earlier version only had 3 — Retail, VFS, Logistics — and was
  corrected to add Properties and AgriCore).
- elt_pipeline.py — FINAL, working version. Two real bugs were found
  and fixed during testing (a dry-run mode that wasn't truly dry, and
  a UUID-to-BigQuery type conversion error) — this version has both
  fixes and is confirmed working via a live 5/5 successful run.
- ELT_SETUP_GUIDE.md — setup walkthrough.

### 04_ERD_Diagrams/
- project_concord_erd.pdf / .svg — the reverse-engineered ERD,
  generated directly from the schema file (not hand-drawn).
- generate_erd_dot.py — the generator script.

### 05_PowerBI_Dashboard/
- Project_Concord_Theme.json — importable Power BI theme.
- PowerBI_Final_Build_Reference.docx — the complete KPI/DAX build
  reference (46 measures, 5 pages), including two real formula bugs
  found and corrected during live testing (a TODAY()-anchoring issue,
  and a DirectQuery folding limitation).
- DASHBOARD_STYLING_GUIDE.md — Looker Studio styling reference (the
  team's first dashboard pass, before switching to Power BI).

### 06_Documentation_Reports/
- Project_Concord_Complete_Report.docx — the main, full project report
  (business understanding, data dictionary, normalisation, security,
  ELT, dashboards, performance review, deliverables status).
- Scenario_Resolution_Report.docx — problem-to-solution mapping for
  all 4 required stakeholder scenarios.
- Query_Performance_Review.docx — real EXPLAIN ANALYZE findings.
- HOW_TO_LOAD_AND_USE.md — Supabase/pgAdmin setup guide.
- Concord_Six_Full_Project_Guide_Detailed.docx — the detailed,
  plain-language, phase-by-phase team contribution record. This
  supersedes an earlier, shorter version of the same document
  (Concord_Six_Full_Project_Guide_Phase1to3.docx) — use this one.

### 07_Weekly_Progress_Reports/
- Week 1, 2, and 3 progress reports.

### 08_Presentation/
- Presentation_Guide.docx — slide structure, talking points, and
  anticipated Q&A for the live defense.

## Files deliberately NOT included, and why

- Any file named synthetic_data.zip (without "_500k") — superseded,
  much larger, abandoned dataset.
- 001_schema.sql and 002_roles_and_rls.sql on their own — merged into
  project_concord_full_database.sql.
- Any earlier version of 005_elt_curated_views.sql with only 3
  divisions in the revenue query — superseded.
- Any earlier version of elt_pipeline.py that predates the UUID fix —
  superseded, would fail if run.
- Concord_Six_Full_Project_Guide_Phase1to3.docx — superseded by the
  Detailed version.

## If your supervisor asks "how do I know this is complete"

Every file above corresponds to a specific, real, tested step of the
project — nothing here is a placeholder or a draft. The database
schema was executed against a live server with zero errors, the
synthetic data was loaded and verified with direct row counts, the
ELT pipeline was run live with a confirmed 5/5 success, and the
dashboard measures were logic-tested against real data before being
documented here.
