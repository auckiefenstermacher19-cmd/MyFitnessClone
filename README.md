# MyFitnessClone

Auckie's MyFitnessPal replacement. A meal is logged from an HTML page in a
browser; the page commits the row straight to `main` in this repo through the
GitHub contents API; two GitHub Actions workflows then regenerate the derived
files and tell Health-Tracker there is new food data.

Floor map and routing: `CONTEXT.md`. Building law: `..\AGENTS.md`.

## The loop, end to end

1. Open the entry page. Locally that is `Food_Log_Entry.html`; published it is
   https://auckiefenstermacher19-cmd.github.io/MyFitnessClone/ (`index.html` is
   a redirect to `Food_Log_Entry.html`, served by GitHub Pages from `main`).
2. Pick a food, a date, a meal, and grams, and submit. The page appends one row
   to `meal_log.csv` and commits it to `main` with the message
   `log: <food name> <grams>g <date> <meal>`.
3. That push fires the Generate Dashboard workflow, which recomputes
   `Meal_Data_Dashboard.csv` and commits it as
   `chore: update Meal_Data_Dashboard [skip ci]`.
4. On success the same workflow posts a `meal_updated` repository dispatch to
   the Health-Tracker repo, which consolidates meals with WHOOP data there.
5. To remove a row, open `Meal_Log_Editor.html` (linked from the entry page).
   It loads one date and deletes single entries, committing
   `log: remove entry <id prefix> (<food> <date>)`. It does not edit values.

## Water log

A sibling of the meal log, two taps and no typing. `Water_Log.html` (live at
https://auckiefenstermacher19-cmd.github.io/MyFitnessClone/Water_Log.html) shows
the day's running total and two blue buttons: `+32` (big bottle) and `+26`
(small bottle). Each tap appends one row to `water_log.csv` and commits it as
`water: +32 fl oz <date>`. `Water_Log_Editor.html` undoes a bottle (`−32` /
`−26`, removing the newest row of that size for the date) or deletes a single
row, committing `water: remove ...`. Both pages reuse the same `gh_token`,
`gh_owner`, and `gh_repo` localStorage keys as the food log pages — no
separate Settings step.

## The GitHub token

Both pages write to GitHub from the browser, so they need a fine-grained
personal access token with Contents: Read and Write on this repo. Enter it once
in the Settings panel of `Food_Log_Entry.html` along with the GitHub username
and repository name. The three values are kept in that browser's `localStorage`
under `gh_token`, `gh_owner`, and `gh_repo`; nothing is stored in the repo.
`Meal_Log_Editor.html` reuses the same three keys and shows "No GitHub token
found. Configure settings in Food Log Entry first." if the entry page was never
configured. A new browser, a new profile, or cleared site data means re-entering
the token.

There is no staging step and no review. Every submit is a direct commit to
`main`.

## Which files are what

Source of truth, edited by a human or by the entry pages:

- `meal_log.csv` — every logged entry. Columns: `log_id`, `user_id`,
  `log_date`, `meal_type`, `food_id`, `food_name_snapshot`, `grams`,
  `created_at`.
- `food_library.csv` — the foods that can be logged, with per-serving and
  per-gram nutrients.
- `user_goals.csv` — daily targets, one row per `effective_date`. Add a row,
  never rewrite an old one; dates before a new `effective_date` keep the goals
  that were in force then.
- `water_log.csv` — every logged bottle. Columns: `log_id`, `user_id`,
  `log_date`, `bottle`, `fl_oz`, `created_at`. Append-only, same shape as
  `meal_log.csv` but with no editable numeric value.

Generated, never hand-edited:

- `Meal_Data_Dashboard.csv` — written by `generate_dashboard.py`.
- `Water_Data_Dashboard.csv` — written by `generate_water_dashboard.py`.
- The `FOODS` array inside `Food_Log_Entry.html`, between the
  `// @@FOODS_START@@` and `// @@FOODS_END@@` sentinels — written by
  `sync_food_library.py`. The rest of that file is hand-written.

Reference, read-only:

- `food_library.schema.json`, `meal_log.schema.json`, `user_goals.schema.json`,
  `water_log.schema.json`, `reference.schema.json` — column definitions and
  units.
- `reference.csv` — nutrient metadata.
- `_archive\architecture.md` — the superseded pre-implementation spec from the
  original Excel workbook. Kept for the formula derivations; it describes a
  folder layout that was never adopted.

Everything sits flat at the repo root on purpose. The workflows hard-code root
paths, so do not move data files into subfolders.

## Contract: Generate Dashboard

- Entry point: `.github\workflows\generate_dashboard.yml`. Triggers on a push
  to `main` touching `meal_log.csv` or `user_goals.csv`, or on manual
  `workflow_dispatch` with an optional `recompute_from` date.
- Interpreter: `ubuntu-latest`, Python 3.11 via `actions/setup-python@v5`.
- Inputs: `meal_log.csv`, `food_library.csv`, `user_goals.csv`, and the existing
  `Meal_Data_Dashboard.csv`.
- Process: runs

      python generate_dashboard.py --meal-log meal_log.csv --food-library food_library.csv --user-goals user_goals.csv --dashboard Meal_Data_Dashboard.csv

  adding `--recompute-from <date>` when `user_goals.csv` gained a new
  `effective_date` (the workflow detects this itself by diffing the previous
  commit) or when the date was passed manually. On a rejected push it discards
  its own commit, takes `origin/main`, and regenerates on top, up to three
  attempts; it never rebases, because two independently generated CSVs conflict
  line by line.
- Outputs: an updated `Meal_Data_Dashboard.csv` committed as
  `chore: update Meal_Data_Dashboard [skip ci]`, and a `meal_updated` repository
  dispatch to the Health-Tracker repo using the repo secrets
  `HEALTH_TRACKER_DISPATCH_TOKEN` and `GH_USERNAME`.
- Done when: `Meal_Data_Dashboard.csv` has a row for every date in
  `meal_log.csv`, and its last date equals the last `log_date` in
  `meal_log.csv`.
- Failure signal, visible without opening GitHub: a `log:` commit on `main` with
  no `chore: update Meal_Data_Dashboard` commit after it, or the last date in
  `Meal_Data_Dashboard.csv` lagging the last `log_date` in `meal_log.csv`. A
  dispatch that fails only prints a warning and does not fail the job; that is
  deliberate, because Health-Tracker also consolidates on a 13:30 UTC schedule.

A run that finds nothing to change exits with "No changes to commit" and
produces no commit. That is a success, not a failure. It is what happened on
2026-07-29, when a new goal row took effect after the last logged meal.

## Contract: Sync Food Library to UI

- Entry point: `.github\workflows\sync_food_library.yml`. Triggers on a push to
  `main` touching `food_library.csv`, or on manual `workflow_dispatch`.
- Interpreter: `ubuntu-latest`, Python 3.11 via `actions/setup-python@v5`.
- Inputs: `food_library.csv` and the current `Food_Log_Entry.html`.
- Process: runs
  `python sync_food_library.py --food-library food_library.csv --html Food_Log_Entry.html`,
  which replaces the block between the `@@FOODS_START@@` and `@@FOODS_END@@`
  sentinels. Same discard-and-regenerate recovery on a rejected push.
- Outputs: an updated `Food_Log_Entry.html` committed as
  `chore: sync food list in Food_Log_Entry.html [skip ci]`.
- Done when: every food in `food_library.csv` appears in the `FOODS` array in
  `Food_Log_Entry.html`.
- Failure signal: a food added to `food_library.csv` does not show up in the
  entry page's search box, or there is no `chore: sync food list` commit after
  the commit that changed `food_library.csv`.

## Contract: Generate Water Dashboard

- Entry point: `.github\workflows\generate_water_dashboard.yml`. Triggers on a
  push to `main` touching `water_log.csv`, or on manual `workflow_dispatch`.
- Interpreter: `ubuntu-latest`, Python 3.11 via `actions/setup-python@v5`.
- Inputs: `water_log.csv` and the existing `Water_Data_Dashboard.csv`.
- Process: runs

      python generate_water_dashboard.py --water-log water_log.csv --dashboard Water_Data_Dashboard.csv

  a full rewrite every run, sorted by date ascending, against the constant
  `WATER_GOAL_FL_OZ = 128`. On a rejected push it discards its own commit,
  takes `origin/main`, and regenerates on top, up to three attempts, same
  recovery as Generate Dashboard.
- Outputs: an updated `Water_Data_Dashboard.csv` with columns `date`,
  `water_fl_oz`, `water_goal_fl_oz`, `water_pct_of_goal`, `water_entries`,
  `water_big_count`, `water_small_count`, committed as
  `chore: update Water_Data_Dashboard [skip ci]`, and a `water_updated`
  repository dispatch to the Health-Tracker repo using the same
  `HEALTH_TRACKER_DISPATCH_TOKEN` and `GH_USERNAME` secrets as the meal
  dispatch. Health-Tracker treats water as a warn-only third source, so a
  failed dispatch does not block the WHOOP+meal merge.
- Done when: `Water_Data_Dashboard.csv` has a row for every date in
  `water_log.csv`, and its last date equals the last `log_date` in
  `water_log.csv`.
- Failure signal, visible without opening GitHub: a `water:` commit on `main`
  with no `chore: update Water_Data_Dashboard` commit after it.

`generate_dashboard.yml` and `sync_food_library.yml` share the concurrency group
`main-writer` so they never push at the same time. The water workflow is
deliberately in its own group, `water-writer`: in the shared group a meal push
could cancel a still-pending water run and the water dashboard would silently
never regenerate. It can push independently because its commit step retries — on
a rejected push it takes `origin/main` and regenerates on top of it.

## Running the scripts by hand

Run either script from the repo root and pass the paths explicitly. The
`DEFAULT_*` constants at the top of `generate_dashboard.py` still point at a
`data/source/` layout that does not exist here, so running that script with no
flags fails. That is a known code defect, not a doc gap; the invocation in the
contract above is the working one. `sync_food_library.py`'s defaults are correct
and it can be run with no flags.

## Are the workflows actually running

Yes. As of 2026-09-10 the newest Actions runs are from 2026-08-26, when both
workflows were triggered manually and both succeeded. The last push-triggered
Generate Dashboard run was 2026-07-29 and it succeeded. There have been no runs
since 2026-08-26 for the simple reason that nothing has been pushed to `main`
since; the last meal was logged 2026-07-25. Failed runs do appear in the history
on 2026-07-23 and 2026-07-25 — those are the rebase conflicts that commit
5e40e17 fixed. Actions being blocked elsewhere on this account does not apply to
this repo.
