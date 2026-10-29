# MyFitnessClone — CONTEXT

If the task is not the meal log, water log, or food library, go back to `..\ROUTER.md`.

Building-wide rules: `..\AGENTS.md`.

This is a **room**: local meal logging, not the health merge. Merge and habits live at `..\Health-Tracker\CONTEXT.md`; WHOOP at `..\whoop-data\CONTEXT.md`.

## What this is

Auckie's MyFitnessPal clone. Food library + meal log CSVs, edited through the HTML pages in this folder. Health-Tracker reads the meal export; it does not own these files. The water log (`Water_Log.html`, `Water_Log_Editor.html`, `water_log.csv`, `Water_Data_Dashboard.csv`) lives here too, and Health-Tracker reads `Water_Data_Dashboard.csv` as a third source.

Downstream: after each dashboard rebuild, the Generate Dashboard workflow here posts a `meal_updated` repository dispatch to the Health-Tracker repo, which consolidates meals with WHOOP data. Break that dispatch and Health-Tracker falls back to its 13:30 UTC schedule.

Water has its own path: the Generate Water Dashboard workflow posts a `water_updated` dispatch, and Health-Tracker treats water as warn-only.

## Local folder is a mirror

Source of truth is GitHub `main`. The pages commit there directly and nothing pulls this clone, so the local CSVs fall behind (local `main` sat at 2026-09-11 while origin had meals and water through 2026-10-06). Read `origin/main` after a fetch, or raw.githubusercontent.com, before trusting any CSV here. This is its own git repo, not tracked by the building repo.

## Read next

`README.md`, then the CSVs and HTML editors in this folder.

Do not merge WHOOP here. Do not write habit rows here.
