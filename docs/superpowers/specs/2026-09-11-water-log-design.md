# Water Log — design

Date: 2026-09-11. Status: approved by Auckie in chat (build without waiting).

## Goal

A phone-first page, sibling of `Food_Log_Entry.html`, that logs water intake
with two taps and no typing. One tap on a big blue circle adds 32 fl oz (big
bottle), one tap on a smaller blue circle adds 26 fl oz (small bottle). The
day's running total shows on screen. Rows land in their own CSV in this repo
through the same GitHub contents API the food log uses. Health-Tracker then
shows a blue circle filling toward a goal of one gallon (128 fl oz) per day.

## What has to be true for this to work

1. **Hosting exists already.** MyFitnessClone is public and GitHub Pages serves
   `main` from the repo root, so any new HTML file at the root is live at
   `https://auckiefenstermacher19-cmd.github.io/MyFitnessClone/<file>` within
   about a minute of the push. No new repo, no new Pages setup.
2. **Auth exists already.** The phone browser already holds `gh_token`,
   `gh_owner`, `gh_repo` in localStorage from the food log. The water pages
   reuse those three keys. No new token.
3. **The write path must survive two fast taps.** The food log does GET sha
   then PUT; two taps in a row would 409. The water page serialises taps
   through a promise queue and retries a 409 once with a fresh sha.
4. **Undo must not edit numbers.** Subtracting is deleting the newest row of
   that bottle size for that date, on the editor page. The log stays
   append-only and every row is one physical bottle event.
5. **Health-Tracker must not break.** Its merge is a two-source date-join with
   post-write validation that counts columns. Water joins as a third block
   appended after meals, so every existing column index stays valid. Water is
   warn-only for freshness, like meals.
6. **Actions run on both repos.** Both are public, so the billing hold on
   private repos does not apply (memory: github-actions-billing-hold).

## Repo: MyFitnessClone (Phase 1)

### `water_log.csv` (source of truth, append-only)

Columns: `log_id,user_id,log_date,bottle,fl_oz,created_at`

- `log_id` UUID v4. `user_id` always `default`.
- `log_date` YYYY-MM-DD, the device's local date at tap time (same as food log).
- `bottle` enum `big` | `small`. `fl_oz` integer: 32 for big, 26 for small.
- `created_at` ISO 8601 UTC.
- Schema documented in `water_log.schema.json`, same style as `meal_log.schema.json`.

### `Water_Log.html` (entry page)

- Same CSS tokens and layout as `Food_Log_Entry.html` (dark, 420px card,
  same header, same toast, same Settings panel and localStorage keys).
- Date input at top, preloaded to today.
- Below it, the day's total, big: `64 fl oz` with a thin blue progress bar
  toward 128 and the caption `of 128 fl oz goal`. Loads from
  `water_log.csv` on open and after every tap.
- Two round blue buttons side by side: the left one larger, labelled
  `+32` / `Big bottle`; the right one smaller, labelled `+26` / `Small bottle`.
  Blue accent `#4fa3ff` (Health-Tracker's blue) so it reads as water, not the
  food log's green.
- Tap: button presses in, shows a spinner state, appends the row, commits as
  `water: +32 fl oz 2026-09-11`, toasts `+32 fl oz · 64 today`, refreshes
  the total. Taps queue; never two PUTs in flight.
- Link at the bottom: `Edit Water Log`, and `← Food Log` back link.
- App feel: `apple-mobile-web-app-capable`, `theme-color`, a
  `water.webmanifest` with `display: standalone`, and a 192/512 PNG icon so
  Add to Home Screen opens it full-screen with its own icon.

### `Water_Log_Editor.html` (edit page)

- Same shape as `Meal_Log_Editor.html`: date picker, entries list for that
  date, a red circle-minus per row that removes that single row.
- Two extra buttons above the list: `−32` and `−26`. Each removes the newest
  row of that bottle size on the selected date. Commit message
  `water: remove 32 fl oz 2026-09-11`. Toast shows the new total.
- Shows the day total at the top the same way the entry page does.

### `generate_water_dashboard.py` + `Water_Data_Dashboard.csv` (derived)

- Reads `water_log.csv`, writes one row per date:
  `date,water_fl_oz,water_goal_fl_oz,water_pct_of_goal,water_entries,water_big_count,water_small_count`.
- `WATER_GOAL_FL_OZ = 128` constant at the top. Full rewrite every run (the
  file is tiny), sorted by date ascending.
- Invocation: `python generate_water_dashboard.py --water-log water_log.csv --dashboard Water_Data_Dashboard.csv`.
- Tests in `tests/test_generate_water_dashboard.py` (pytest): totals per
  date, counts, empty log, goal pct rounding.

### `.github/workflows/generate_water_dashboard.yml`

- Triggers on push to `main` touching `water_log.csv`, plus manual.
- Same `concurrency: main-writer` group as the two existing workflows.
- Same discard-and-regenerate push retry as Generate Dashboard.
- Commits `chore: update Water_Data_Dashboard [skip ci]`.
- Posts a `water_updated` repository dispatch to Health-Tracker with the
  existing `HEALTH_TRACKER_DISPATCH_TOKEN` and `GH_USERNAME` secrets.

### Links and docs

- `Food_Log_Entry.html` gains a `Water Log` link next to `Edit Meal Log`.
- `README.md` and `CONTEXT.md` gain a water section (contract, failure signal).

## Repo: Health-Tracker (Phase 2)

- `fetch_sources.py`: third source `Water_Data_Dashboard.csv` from
  MyFitnessClone, env `WATER_REPO` (default `MyFitnessClone`), `WATER_PATH`.
  A missing water file is a warning, not exit 1, so a water outage never
  blocks the WHOOP+meal merge. Writes `raw/Water_Data_Dashboard.csv`.
- `validate_sources.py`: validates the water file when present, snapshot
  `schema/Water_Data_Dashboard_schema.json`.
- `consolidate.py`: layout becomes
  `[whoop][spacer][meal][spacer][water]`. Water's `date` is renamed
  `water_date`. If the raw water file is absent, the water block is omitted
  and the layout is unchanged from today. Staleness adds `water` as warn-only.
  Post-write validation covers water dates.
- `consolidate.yml`: `repository_dispatch` types add `water_updated`;
  `WATER_REPO` var passed like `MEAL_REPO`.
- Tests: `tests/test_consolidate_water.py` covering three-source join,
  water-absent fallback, and column index stability.
- `index.html` + `dashboard.js`: a new `Water` tile in the nutrition row: an
  SVG circle that fills from the bottom with blue liquid to
  `water_fl_oz / water_goal_fl_oz`, number in the middle (`96 fl oz`),
  caption `of 128 · 75%`, turns green with a check when the goal is met.
  Blank day shows an empty circle and `No water logged`. A small 14-day bar
  chart of daily fl oz with a goal line, next to it.
- `README.md` and `CONTEXT.md` updated for the third source.

## Not in scope

- Time of day. One date, one total.
- Custom amounts. Two bottles only.
- Editing a row's number. Only add and delete.
- Any change to `generate_dashboard.py` or the meal workflow.

## Failure signals (visible without opening GitHub)

- A `water:` commit on `main` with no `chore: update Water_Data_Dashboard`
  commit after it.
- Health-Tracker audit shows `water` stale while the water log has today's rows.
