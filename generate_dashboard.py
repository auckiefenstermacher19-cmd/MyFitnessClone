"""
generate_dashboard.py
---------------------
Reads meal_log.csv and user_goals.csv, computes all dashboard metrics
(matching the DashBoard tab in MyfitnessPal_Clone_-_Final.xlsm), and
writes results to Meal_Data_Dashboard.csv.

Behaviour
---------
- First run (Meal_Data_Dashboard.csv does not exist):
    Computes every date present in meal_log.csv and writes all rows.

- Subsequent runs (Meal_Data_Dashboard.csv already exists):
    Reads existing dashboard dates.
    Only computes and appends dates in meal_log.csv that are NOT already
    in Meal_Data_Dashboard.csv.
    Existing rows are never modified.

Usage
-----
    python generate_dashboard.py

    # override file paths if needed:
    python generate_dashboard.py \
        --meal-log path/to/meal_log.csv \
        --food-library path/to/food_library.csv \
        --user-goals path/to/user_goals.csv \
        --dashboard path/to/Meal_Data_Dashboard.csv

Dashboard sections (separated by a blank column each)
------------------------------------------------------
 1  Date
 2  Calories Total          — actual / goal / delta
 3  Calories By Meal        — B/L/D/S actual+total / goal+total / delta+total
 4  Calories By Meal %      — B/L/D/S share of daily total
 5  Macros Total            — fat/carbs/protein actual+total / goal+total / delta+total
 6  Macros % of Goal        — fat/carbs/protein achievement index (actual ÷ goal)
 7  Macros By Meal          — B/L/D: fat/carbs/protein actual+total + % split
 8  Micros Total            — 9 nutrients: actual / goal / delta
 9  Micros % of Goal        — 9 nutrients: actual ÷ goal
10  Micros By Meal          — B/L/D: all 9 nutrients
"""

import argparse
import csv
import os
import sys
from collections import defaultdict
from datetime import date as date_type


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MEAL_LOG   = "data/source/meal_log.csv"
DEFAULT_FOOD_LIB   = "data/source/food_library.csv"
DEFAULT_USER_GOALS = "data/source/user_goals.csv"
DEFAULT_DASHBOARD  = "data/source/Meal_Data_Dashboard.csv"

MEALS       = ["Breakfast", "Lunch", "Dinner", "Snack"]
MACRO_3     = ["total_fat", "total_carbs", "protein"]
MICRO_9     = [
    "sodium", "potassium", "dietary_fiber", "sugars",
    "vitamin_a_mcg_rae", "vitamin_c_mg", "vitamin_d_mcg",
    "calcium_mg", "iron_mg",
]


# ---------------------------------------------------------------------------
# Column schema
# ---------------------------------------------------------------------------
# Defines the exact ordered list of column headers written to the CSV.
# A blank string "" represents a separator column (empty cell) between sections.

def build_column_headers():
    """Return the ordered list of column headers for Meal_Data_Dashboard.csv."""
    h = []

    # Section 1 — Date
    h += ["date"]
    h += [""]  # separator

    # Section 2 — Calories Total
    h += ["calories_actual", "calories_goal", "calories_delta"]
    h += [""]

    # Section 3 — Calories By Meal
    h += [f"cal_by_meal_{m.lower()}_actual" for m in MEALS]
    h += ["cal_by_meal_total_actual"]
    h += [f"cal_by_meal_{m.lower()}_goal"   for m in MEALS]
    h += ["cal_by_meal_total_goal"]
    h += [f"cal_by_meal_{m.lower()}_delta"  for m in MEALS]
    h += ["cal_by_meal_total_delta"]
    h += [""]

    # Section 4 — Calories By Meal %
    h += [f"cal_pct_{m.lower()}" for m in MEALS]
    h += [""]

    # Section 5 — Macros Total
    h += [f"macro_{f}_actual"  for f in MACRO_3] + ["macro_total_actual"]
    h += [f"macro_{f}_goal"    for f in MACRO_3] + ["macro_total_goal"]
    h += [f"macro_{f}_delta"   for f in MACRO_3] + ["macro_total_delta"]
    h += [""]

    # Section 6 — Macros % of Goal
    h += [f"macro_{f}_pct_of_goal" for f in MACRO_3]
    h += [""]

    # Section 7 — Macros By Meal (Breakfast / Lunch / Dinner only — matches workbook)
    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        h += [f"macro_by_meal_{m}_{f}_actual" for f in MACRO_3]
        h += [f"macro_by_meal_{m}_total_actual"]
        h += [f"macro_by_meal_{m}_{f}_pct"    for f in MACRO_3]
    h += [""]

    # Section 8 — Micros Total
    h += [f"micro_{f}_actual" for f in MICRO_9]
    h += [f"micro_{f}_goal"   for f in MICRO_9]
    h += [f"micro_{f}_delta"  for f in MICRO_9]
    h += [""]

    # Section 9 — Micros % of Goal
    h += [f"micro_{f}_pct_of_goal" for f in MICRO_9]
    h += [""]

    # Section 10 — Micros By Meal (Breakfast / Lunch / Dinner only)
    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        h += [f"micro_by_meal_{m}_{f}" for f in MICRO_9]

    return h


HEADERS = build_column_headers()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_food_library(path):
    """Return dict of food_id → nutrient dict (all values as float)."""
    foods = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            food_id = row["food_id"]
            foods[food_id] = {k: float(v) if v != "" else 0.0
                              for k, v in row.items()
                              if k not in ("food_id", "food_name", "food_category",
                                           "brand", "serving_unit", "serving_size_label",
                                           "vitamin_d_needs_label_verification",
                                           "source_url", "created_at", "updated_at")}
            # keep string fields too for reference
            foods[food_id]["_name"] = row["food_name"]
    return foods


def load_meal_log(path):
    """Return list of log entry dicts with grams as float."""
    entries = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            entries.append({
                "log_date":  row["log_date"],
                "meal_type": row["meal_type"],
                "food_id":   row["food_id"],
                "grams":     float(row["grams"]),
            })
    return entries


def load_goals(path):
    """
    Return a list of goal dicts sorted by effective_date ascending.
    Each row is a versioned goal set.  To find the active goal for a given
    log_date, take the row with the highest effective_date that is <= log_date.
    """
    goals = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            goals.append(row)
    goals.sort(key=lambda r: r["effective_date"])
    return goals


def resolve_goals(goals, log_date_str):
    """
    Return the goal row that was active on log_date_str (YYYY-MM-DD).
    Raises ValueError if no goal covers the given date.
    """
    active = None
    for g in goals:
        if g["effective_date"] <= log_date_str:
            active = g
        else:
            break
    if active is None:
        raise ValueError(
            f"No goal row covers date {log_date_str}. "
            f"Earliest effective_date is {goals[0]['effective_date']}."
        )
    return active


def load_existing_dashboard_dates(path):
    """Return set of date strings already in Meal_Data_Dashboard.csv, or empty set."""
    if not os.path.exists(path):
        return set()
    dates = set()
    with open(path, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if row.get("date"):
                dates.add(row["date"])
    return dates


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def consumed(food, grams, field):
    """Compute grams * (nutrient_per_serving / grams_per_serving)."""
    gpg = food["grams_per_serving"]
    if gpg == 0:
        return 0.0
    return grams * food[field] / gpg


def compute_daily(date_str, entries, foods, goals_list):
    """
    Given all log entries for a single date, compute every dashboard metric.
    Returns an ordered dict matching HEADERS.
    """
    goal = resolve_goals(goals_list, date_str)

    # Numeric goal values
    cal_goal      = float(goal["calories"])
    macro_goals   = {f: float(goal[f]) for f in MACRO_3}
    micro_goals   = {f: float(goal[f]) for f in MICRO_9}
    meal_split    = goal["calorie_meal_split"]  # "equal_three" or "custom"

    # Per-meal calorie goal
    if meal_split == "equal_three":
        meal_cal_goal = {
            "Breakfast": cal_goal / 3,
            "Lunch":     cal_goal / 3,
            "Dinner":    cal_goal / 3,
            "Snack":     None,              # no goal for snack
        }
    else:
        # Future: read per-meal targets from goal row
        meal_cal_goal = {m: None for m in MEALS}

    # Aggregate consumed values: totals[meal][field]
    totals = {m: defaultdict(float) for m in MEALS + ["ALL"]}

    for entry in entries:
        meal  = entry["meal_type"]
        food  = foods[entry["food_id"]]
        grams = entry["grams"]
        for field in ["calories"] + MACRO_3 + MICRO_9:
            val = consumed(food, grams, field)
            totals[meal][field]  += val
            totals["ALL"][field] += val

    # Helper: safe division (returns "" if denominator is 0)
    def pct(num, denom):
        return round(num / denom, 6) if denom else ""

    def r(val):
        return round(val, 4)

    # Build row in HEADERS order
    row = {}

    # Section 1
    row["date"] = date_str

    # Section 2 — Calories Total
    cal_actual = totals["ALL"]["calories"]
    row["calories_actual"] = r(cal_actual)
    row["calories_goal"]   = cal_goal
    row["calories_delta"]  = r(cal_goal - cal_actual)

    # Section 3 — Calories By Meal
    for meal in MEALS:
        row[f"cal_by_meal_{meal.lower()}_actual"] = r(totals[meal]["calories"])
    row["cal_by_meal_total_actual"] = r(cal_actual)

    for meal in MEALS:
        g = meal_cal_goal[meal]
        row[f"cal_by_meal_{meal.lower()}_goal"] = r(g) if g is not None else ""
    row["cal_by_meal_total_goal"] = cal_goal

    for meal in MEALS:
        g = meal_cal_goal[meal] or 0
        row[f"cal_by_meal_{meal.lower()}_delta"] = r(g - totals[meal]["calories"])
    row["cal_by_meal_total_delta"] = r(cal_goal - cal_actual)

    # Section 4 — Calories By Meal %
    for meal in MEALS:
        row[f"cal_pct_{meal.lower()}"] = pct(totals[meal]["calories"], cal_actual)

    # Section 5 — Macros Total
    macro_actual_total = sum(totals["ALL"][f] for f in MACRO_3)
    macro_goal_total   = sum(macro_goals[f]   for f in MACRO_3)

    for f in MACRO_3:
        row[f"macro_{f}_actual"] = r(totals["ALL"][f])
    row["macro_total_actual"] = r(macro_actual_total)

    for f in MACRO_3:
        row[f"macro_{f}_goal"] = macro_goals[f]
    row["macro_total_goal"] = macro_goal_total

    for f in MACRO_3:
        row[f"macro_{f}_delta"] = r(macro_goals[f] - totals["ALL"][f])
    row["macro_total_delta"] = r(macro_goal_total - macro_actual_total)

    # Section 6 — Macros % of Goal
    for f in MACRO_3:
        row[f"macro_{f}_pct_of_goal"] = pct(totals["ALL"][f], macro_goals[f])

    # Section 7 — Macros By Meal
    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        meal_macro_total = sum(totals[meal][f] for f in MACRO_3)
        for f in MACRO_3:
            row[f"macro_by_meal_{m}_{f}_actual"] = r(totals[meal][f])
        row[f"macro_by_meal_{m}_total_actual"] = r(meal_macro_total)
        for f in MACRO_3:
            row[f"macro_by_meal_{m}_{f}_pct"] = pct(totals[meal][f], meal_macro_total)

    # Section 8 — Micros Total
    for f in MICRO_9:
        row[f"micro_{f}_actual"] = r(totals["ALL"][f])
    for f in MICRO_9:
        row[f"micro_{f}_goal"]   = micro_goals[f]
    for f in MICRO_9:
        row[f"micro_{f}_delta"]  = r(micro_goals[f] - totals["ALL"][f])

    # Section 9 — Micros % of Goal
    for f in MICRO_9:
        row[f"micro_{f}_pct_of_goal"] = pct(totals["ALL"][f], micro_goals[f])

    # Section 10 — Micros By Meal
    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        for f in MICRO_9:
            row[f"micro_by_meal_{m}_{f}"] = r(totals[meal][f])

    return row


# ---------------------------------------------------------------------------
# Write helpers
# ---------------------------------------------------------------------------

def write_rows(path, rows, mode="w"):
    """Write (or append) rows to the dashboard CSV."""
    write_header = (mode == "w") or (not os.path.exists(path))
    with open(path, mode, newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
        if write_header:
            writer.writeheader()
        for row in rows:
            # Fill separator columns with empty string
            out_row = {h: row.get(h, "") for h in HEADERS}
            writer.writerow(out_row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate / incrementally update Meal_Data_Dashboard.csv"
    )
    p.add_argument("--meal-log",      default=DEFAULT_MEAL_LOG,   help="Path to meal_log.csv")
    p.add_argument("--food-library",  default=DEFAULT_FOOD_LIB,   help="Path to food_library.csv")
    p.add_argument("--user-goals",    default=DEFAULT_USER_GOALS, help="Path to user_goals.csv")
    p.add_argument("--dashboard",     default=DEFAULT_DASHBOARD,  help="Path to Meal_Data_Dashboard.csv")
    return p.parse_args()


def main():
    args = parse_args()

    # ── Validate inputs exist ─────────────────────────────────
    for label, path in [
        ("meal_log",    args.meal_log),
        ("food_library",args.food_library),
        ("user_goals",  args.user_goals),
    ]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found at '{path}'")
            sys.exit(1)

    # ── Load source data ──────────────────────────────────────
    print(f"Loading food library  : {args.food_library}")
    foods = load_food_library(args.food_library)

    print(f"Loading meal log      : {args.meal_log}")
    log_entries = load_meal_log(args.meal_log)

    print(f"Loading user goals    : {args.user_goals}")
    goals_list = load_goals(args.user_goals)

    # ── Determine which dates to process ─────────────────────
    existing_dates = load_existing_dashboard_dates(args.dashboard)
    first_run      = not os.path.exists(args.dashboard)

    all_log_dates = sorted(set(e["log_date"] for e in log_entries))
    new_dates     = [d for d in all_log_dates if d not in existing_dates]

    if first_run:
        print(f"\nFirst run — dashboard file not found.")
        print(f"Processing all {len(all_log_dates)} date(s) in meal log.")
        dates_to_process = all_log_dates
        write_mode = "w"
    elif not new_dates:
        print(f"\nDashboard is up to date — no new dates found in meal log.")
        print(f"Existing dates: {sorted(existing_dates)}")
        sys.exit(0)
    else:
        print(f"\nIncremental run — {len(existing_dates)} date(s) already in dashboard.")
        print(f"New date(s) to process: {new_dates}")
        dates_to_process = new_dates
        write_mode = "a"

    # ── Group log entries by date ─────────────────────────────
    by_date = defaultdict(list)
    for entry in log_entries:
        by_date[entry["log_date"]].append(entry)

    # ── Compute and write ─────────────────────────────────────
    computed_rows = []
    for date_str in dates_to_process:
        entries = by_date[date_str]
        print(f"  Computing {date_str}  ({len(entries)} log entries)")
        try:
            row = compute_daily(date_str, entries, foods, goals_list)
            computed_rows.append(row)
        except ValueError as e:
            print(f"  SKIPPED {date_str}: {e}")

    if not computed_rows:
        print("No rows to write.")
        sys.exit(0)

    write_rows(args.dashboard, computed_rows, mode=write_mode)

    print(f"\n{'Created' if first_run else 'Updated'}: {args.dashboard}")
    print(f"Rows written : {len(computed_rows)}")
    print(f"Dates written: {[r['date'] for r in computed_rows]}")
    if not first_run:
        all_dates = sorted(existing_dates | set(r["date"] for r in computed_rows))
        print(f"Total dates in dashboard: {len(all_dates)}")


if __name__ == "__main__":
    main()
