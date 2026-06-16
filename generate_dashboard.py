"""
generate_dashboard.py
---------------------
Reads meal_log.csv, food_library.csv, and user_goals.csv, computes all
dashboard metrics (matching the DashBoard tab in MyfitnessPal_Clone_-_Final.xlsm),
and writes results to Meal_Data_Dashboard.csv.

Behaviour
---------
- First run (Meal_Data_Dashboard.csv does not exist):
    Computes every date present in meal_log.csv and writes all rows.

- Incremental run (meal_log.csv updated, new dates added):
    Reads existing dashboard dates.
    Only computes and appends net-new dates.
    Existing rows are never modified.

- Goal update run (user_goals.csv updated, --recompute-from DATE passed):
    Recomputes every date >= DATE from scratch using the updated goals.
    Dates before DATE are preserved exactly as-is.
    The full dashboard is rewritten in date order.

Usage
-----
    # Normal incremental run (new meal log entries)
    python scripts/generate_dashboard.py

    # After updating user_goals.csv — recompute from the new goal's effective date
    python scripts/generate_dashboard.py --recompute-from 2026-05-01

    # Override file paths
    python scripts/generate_dashboard.py \\
        --meal-log     data/source/meal_log.csv \\
        --food-library data/source/food_library.csv \\
        --user-goals   data/source/user_goals.csv \\
        --dashboard    data/source/Meal_Data_Dashboard.csv

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


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_MEAL_LOG   = "data/source/meal_log.csv"
DEFAULT_FOOD_LIB   = "data/source/food_library.csv"
DEFAULT_USER_GOALS = "data/source/user_goals.csv"
DEFAULT_DASHBOARD  = "data/source/Meal_Data_Dashboard.csv"

MEALS   = ["Breakfast", "Lunch", "Dinner", "Snack"]
MACRO_3 = ["total_fat", "total_carbs", "protein"]
MICRO_9 = [
    "sodium", "potassium", "dietary_fiber", "sugars",
    "vitamin_a_mcg_rae", "vitamin_c_mg", "vitamin_d_mcg",
    "calcium_mg", "iron_mg",
]


# ---------------------------------------------------------------------------
# Column schema
# ---------------------------------------------------------------------------

def build_column_headers():
    """Return the ordered list of column headers for Meal_Data_Dashboard.csv."""
    h = []

    h += ["date", ""]

    h += ["calories_actual", "calories_goal", "calories_delta", ""]

    h += [f"cal_by_meal_{m.lower()}_actual" for m in MEALS]
    h += ["cal_by_meal_total_actual"]
    h += [f"cal_by_meal_{m.lower()}_goal"  for m in MEALS]
    h += ["cal_by_meal_total_goal"]
    h += [f"cal_by_meal_{m.lower()}_delta" for m in MEALS]
    h += ["cal_by_meal_total_delta", ""]

    h += [f"cal_pct_{m.lower()}" for m in MEALS] + [""]

    h += [f"macro_{f}_actual" for f in MACRO_3] + ["macro_total_actual"]
    h += [f"macro_{f}_goal"   for f in MACRO_3] + ["macro_total_goal"]
    h += [f"macro_{f}_delta"  for f in MACRO_3] + ["macro_total_delta", ""]

    h += [f"macro_{f}_pct_of_goal" for f in MACRO_3] + [""]

    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        h += [f"macro_by_meal_{m}_{f}_actual" for f in MACRO_3]
        h += [f"macro_by_meal_{m}_total_actual"]
        h += [f"macro_by_meal_{m}_{f}_pct" for f in MACRO_3]
    h += [""]

    h += [f"micro_{f}_actual" for f in MICRO_9]
    h += [f"micro_{f}_goal"   for f in MICRO_9]
    h += [f"micro_{f}_delta"  for f in MICRO_9] + [""]

    h += [f"micro_{f}_pct_of_goal" for f in MICRO_9] + [""]

    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        h += [f"micro_by_meal_{m}_{f}" for f in MICRO_9]

    return h


HEADERS = build_column_headers()


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_food_library(path):
    """Return dict of food_id → nutrient dict (numeric values as float)."""
    foods = {}
    skip = {"food_id", "food_name", "food_category", "brand", "serving_unit",
            "serving_size_label", "vitamin_d_needs_label_verification",
            "source_url", "created_at", "updated_at"}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            fid = row["food_id"]
            foods[fid] = {k: float(v) if v != "" else 0.0
                          for k, v in row.items() if k not in skip}
            foods[fid]["_name"] = row["food_name"]
    return foods


def load_meal_log(path):
    """Return list of log entry dicts."""
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
    Return list of goal dicts sorted by effective_date ascending.
    Each row represents the goal set active from that date onward,
    until the next row's effective_date (or indefinitely if last row).
    """
    goals = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            goals.append(row)
    goals.sort(key=lambda r: r["effective_date"])
    return goals


def resolve_goals(goals, log_date_str):
    """
    Return the goal row active on log_date_str.
    Uses the most recent effective_date that is <= log_date_str.
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


def load_existing_dashboard(path):
    """
    Return (dates_set, rows_dict) where rows_dict is date → full row dict.
    Returns (empty set, empty dict) if file does not exist.
    """
    if not os.path.exists(path):
        return set(), {}
    dates = set()
    rows  = {}
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            d = row.get("date", "")
            if d:
                dates.add(d)
                rows[d] = row
    return dates, rows


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def consumed(food, grams, field):
    """Return grams * (nutrient_per_serving / grams_per_serving)."""
    gpg = food.get("grams_per_serving", 0)
    return (grams * food[field] / gpg) if gpg else 0.0


def compute_daily(date_str, entries, foods, goals_list):
    """Compute all dashboard metrics for one date. Returns a row dict."""
    goal       = resolve_goals(goals_list, date_str)
    cal_goal   = float(goal["calories"])
    macro_goals = {f: float(goal[f]) for f in MACRO_3}
    micro_goals = {f: float(goal[f]) for f in MICRO_9}
    meal_split  = goal["calorie_meal_split"]

    if meal_split == "equal_three":
        meal_cal_goal = {
            "Breakfast": cal_goal / 3,
            "Lunch":     cal_goal / 3,
            "Dinner":    cal_goal / 3,
            "Snack":     None,
        }
    else:
        meal_cal_goal = {m: None for m in MEALS}

    totals = {m: defaultdict(float) for m in MEALS + ["ALL"]}
    for entry in entries:
        meal  = entry["meal_type"]
        food  = foods[entry["food_id"]]
        grams = entry["grams"]
        for field in ["calories"] + MACRO_3 + MICRO_9:
            val = consumed(food, grams, field)
            totals[meal][field]  += val
            totals["ALL"][field] += val

    def pct(num, denom):
        return round(num / denom, 6) if denom else ""

    def r(val):
        return round(val, 4)

    row = {"date": date_str}

    cal_actual = totals["ALL"]["calories"]
    row["calories_actual"] = r(cal_actual)
    row["calories_goal"]   = cal_goal
    row["calories_delta"]  = r(cal_goal - cal_actual)

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

    for meal in MEALS:
        row[f"cal_pct_{meal.lower()}"] = pct(totals[meal]["calories"], cal_actual)

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

    for f in MACRO_3:
        row[f"macro_{f}_pct_of_goal"] = pct(totals["ALL"][f], macro_goals[f])

    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        meal_macro_total = sum(totals[meal][f] for f in MACRO_3)
        for f in MACRO_3:
            row[f"macro_by_meal_{m}_{f}_actual"] = r(totals[meal][f])
        row[f"macro_by_meal_{m}_total_actual"] = r(meal_macro_total)
        for f in MACRO_3:
            row[f"macro_by_meal_{m}_{f}_pct"] = pct(totals[meal][f], meal_macro_total)

    for f in MICRO_9:
        row[f"micro_{f}_actual"] = r(totals["ALL"][f])
    for f in MICRO_9:
        row[f"micro_{f}_goal"] = micro_goals[f]
    for f in MICRO_9:
        row[f"micro_{f}_delta"] = r(micro_goals[f] - totals["ALL"][f])

    for f in MICRO_9:
        row[f"micro_{f}_pct_of_goal"] = pct(totals["ALL"][f], micro_goals[f])

    for meal in ["Breakfast", "Lunch", "Dinner"]:
        m = meal.lower()
        for f in MICRO_9:
            row[f"micro_by_meal_{m}_{f}"] = r(totals[meal][f])

    return row


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_dashboard(path, rows_by_date):
    """Write all rows to the dashboard CSV, sorted by date ascending."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS, extrasaction="ignore")
        writer.writeheader()
        for date_str in sorted(rows_by_date.keys()):
            out_row = {h: rows_by_date[date_str].get(h, "") for h in HEADERS}
            writer.writerow(out_row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args():
    p = argparse.ArgumentParser(
        description="Generate / incrementally update Meal_Data_Dashboard.csv"
    )
    p.add_argument("--meal-log",        default=DEFAULT_MEAL_LOG,
                   help="Path to meal_log.csv")
    p.add_argument("--food-library",    default=DEFAULT_FOOD_LIB,
                   help="Path to food_library.csv")
    p.add_argument("--user-goals",      default=DEFAULT_USER_GOALS,
                   help="Path to user_goals.csv")
    p.add_argument("--dashboard",       default=DEFAULT_DASHBOARD,
                   help="Path to Meal_Data_Dashboard.csv")
    p.add_argument("--recompute-from",  default=None, metavar="DATE",
                   help=(
                       "YYYY-MM-DD. Recompute all dashboard rows on or after "
                       "this date using current goals. Use after adding a new "
                       "row to user_goals.csv. Rows before this date are "
                       "preserved unchanged."
                   ))
    return p.parse_args()


def main():
    args = parse_args()

    # ── Validate inputs ───────────────────────────────────────
    for label, path in [
        ("meal_log",     args.meal_log),
        ("food_library", args.food_library),
        ("user_goals",   args.user_goals),
    ]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found at '{path}'")
            sys.exit(1)

    if args.recompute_from:
        try:
            # validate date format
            from datetime import datetime
            datetime.strptime(args.recompute_from, "%Y-%m-%d")
        except ValueError:
            print(f"ERROR: --recompute-from must be YYYY-MM-DD, got '{args.recompute_from}'")
            sys.exit(1)

    # ── Load source data ──────────────────────────────────────
    print(f"Loading food library  : {args.food_library}")
    foods = load_food_library(args.food_library)

    print(f"Loading meal log      : {args.meal_log}")
    log_entries = load_meal_log(args.meal_log)

    print(f"Loading user goals    : {args.user_goals}")
    goals_list = load_goals(args.user_goals)

    # Group log entries by date
    by_date = defaultdict(list)
    for entry in log_entries:
        by_date[entry["log_date"]].append(entry)

    all_log_dates = sorted(by_date.keys())

    # ── Load existing dashboard ───────────────────────────────
    existing_dates, existing_rows = load_existing_dashboard(args.dashboard)
    first_run = not os.path.exists(args.dashboard)

    # ── Determine mode and dates to process ──────────────────
    if first_run:
        print(f"\nFirst run — dashboard file not found.")
        print(f"Computing all {len(all_log_dates)} date(s) in meal log.")
        dates_to_compute = all_log_dates
        preserved_rows   = {}

    elif args.recompute_from:
        cutoff = args.recompute_from
        dates_to_compute = [d for d in all_log_dates if d >= cutoff]
        preserved_rows   = {d: r for d, r in existing_rows.items() if d < cutoff}
        print(f"\nGoal update run — recomputing from {cutoff}.")
        print(f"Preserving {len(preserved_rows)} row(s) before {cutoff}.")
        print(f"Recomputing {len(dates_to_compute)} date(s): {dates_to_compute}")

    else:
        new_dates = [d for d in all_log_dates if d not in existing_dates]
        if not new_dates:
            print(f"\nDashboard is up to date — no new dates found.")
            print(f"Existing dates: {sorted(existing_dates)}")
            sys.exit(0)
        print(f"\nIncremental run — {len(existing_dates)} date(s) already present.")
        print(f"New date(s) to compute: {new_dates}")
        dates_to_compute = new_dates
        preserved_rows   = existing_rows  # keep all existing rows

    # ── Compute ───────────────────────────────────────────────
    newly_computed = {}
    for date_str in dates_to_compute:
        entries = by_date.get(date_str, [])
        if not entries:
            print(f"  SKIPPED {date_str} — no log entries found")
            continue
        print(f"  Computing {date_str}  ({len(entries)} log entries)")
        try:
            newly_computed[date_str] = compute_daily(date_str, entries, foods, goals_list)
        except ValueError as e:
            print(f"  SKIPPED {date_str}: {e}")

    if not newly_computed:
        print("No rows computed — dashboard unchanged.")
        sys.exit(0)

    # ── Merge and write ───────────────────────────────────────
    final_rows = {**preserved_rows, **newly_computed}
    write_dashboard(args.dashboard, final_rows)

    action = "Created" if first_run else "Updated"
    print(f"\n{action}: {args.dashboard}")
    print(f"Rows computed : {len(newly_computed)}")
    print(f"Rows preserved: {len(preserved_rows)}")
    print(f"Total rows    : {len(final_rows)}")


if __name__ == "__main__":
    main()
