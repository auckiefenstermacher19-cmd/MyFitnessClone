# MyFitnessClone — CONTEXT

If the task is not the meal log or food library, go back to `..\ROUTER.md`.

Building-wide rules: `..\AGENTS.md`.

This is a **room**: local meal logging, not the health merge. Merge and habits live at `..\Health-Tracker\CONTEXT.md`; WHOOP at `..\whoop-data\CONTEXT.md`.

## What this is

Auckie's MyFitnessPal clone. Food library + meal log CSVs, edited through the HTML pages in this folder. Health-Tracker reads the meal export; it does not own these files.

Downstream: after each dashboard rebuild, the Generate Dashboard workflow here posts a `meal_updated` repository dispatch to the Health-Tracker repo, which consolidates meals with WHOOP data. Break that dispatch and Health-Tracker falls back to its 13:30 UTC schedule.

## Read next

`README.md`, then the CSVs and HTML editors in this folder.

Do not merge WHOOP here. Do not write habit rows here.
