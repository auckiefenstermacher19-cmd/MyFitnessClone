"""
generate_water_dashboard.py
----------------------------
Reads water_log.csv and writes Water_Data_Dashboard.csv, one row per date.

Behaviour
---------
Full rewrite every run — the water log is tiny, so there is no incremental
mode like generate_dashboard.py has. Every date present in water_log.csv gets
one row, sorted by date ascending. A row with a malformed fl_oz value is
skipped (with a warning printed) rather than crashing the run.

Usage
-----
    python generate_water_dashboard.py \\
        --water-log water_log.csv \\
        --dashboard Water_Data_Dashboard.csv
"""

import argparse
import csv
import sys
from collections import defaultdict


# ---------------------------------------------------------------------------
# Configuration
# ---------------------------------------------------------------------------

DEFAULT_WATER_LOG = "water_log.csv"
DEFAULT_DASHBOARD = "Water_Data_Dashboard.csv"

WATER_GOAL_FL_OZ = 128

HEADERS = [
    "date",
    "water_fl_oz",
    "water_goal_fl_oz",
    "water_pct_of_goal",
    "water_entries",
    "water_big_count",
    "water_small_count",
]


# ---------------------------------------------------------------------------
# Data loading
# ---------------------------------------------------------------------------

def load_water_log(path):
    """Return list of raw row dicts as read from water_log.csv."""
    with open(path, newline="", encoding="utf-8") as f:
        return list(csv.DictReader(f))


# ---------------------------------------------------------------------------
# Computation
# ---------------------------------------------------------------------------

def summarize(rows):
    """
    Compute one dashboard row per date from raw water_log rows.

    Pure function: takes the list of row dicts (as produced by
    csv.DictReader over water_log.csv), returns a list of dashboard row
    dicts sorted by date ascending. A row whose fl_oz is not a valid integer
    is skipped, with a warning printed, rather than raising.
    """
    totals = defaultdict(lambda: {"fl_oz": 0, "entries": 0, "big": 0, "small": 0})

    for row in rows:
        date = row.get("log_date", "")
        bottle = row.get("bottle", "")
        raw_fl_oz = row.get("fl_oz", "")
        try:
            fl_oz = int(raw_fl_oz)
        except (TypeError, ValueError):
            print(
                f"WARNING: skipping row with malformed fl_oz "
                f"(log_id={row.get('log_id', '?')!r}, "
                f"log_date={date!r}, fl_oz={raw_fl_oz!r})"
            )
            continue

        day = totals[date]
        day["fl_oz"] += fl_oz
        day["entries"] += 1
        if bottle == "big":
            day["big"] += 1
        elif bottle == "small":
            day["small"] += 1

    result = []
    for date in sorted(totals.keys()):
        day = totals[date]
        pct = round(day["fl_oz"] / WATER_GOAL_FL_OZ * 100, 1)
        result.append({
            "date": date,
            "water_fl_oz": day["fl_oz"],
            "water_goal_fl_oz": WATER_GOAL_FL_OZ,
            "water_pct_of_goal": pct,
            "water_entries": day["entries"],
            "water_big_count": day["big"],
            "water_small_count": day["small"],
        })

    return result


# ---------------------------------------------------------------------------
# Write
# ---------------------------------------------------------------------------

def write_dashboard(path, dashboard_rows):
    """Write all rows to the dashboard CSV, full rewrite."""
    with open(path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=HEADERS)
        writer.writeheader()
        for row in dashboard_rows:
            writer.writerow(row)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

def parse_args(argv):
    p = argparse.ArgumentParser(
        description="Generate Water_Data_Dashboard.csv from water_log.csv"
    )
    p.add_argument("--water-log", default=DEFAULT_WATER_LOG,
                   help="Path to water_log.csv")
    p.add_argument("--dashboard", default=DEFAULT_DASHBOARD,
                   help="Path to Water_Data_Dashboard.csv")
    return p.parse_args(argv)


def main(argv=None):
    args = parse_args(argv)

    print(f"Loading water log : {args.water_log}")
    rows = load_water_log(args.water_log)

    dashboard_rows = summarize(rows)

    write_dashboard(args.dashboard, dashboard_rows)

    print(f"\nWrote: {args.dashboard}")
    print(f"Rows  : {len(dashboard_rows)}")


if __name__ == "__main__":
    main(sys.argv[1:])
