"""Tests for generate_water_dashboard.py."""

import csv
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import generate_water_dashboard as gwd


def make_row(log_id, log_date, bottle, fl_oz, created_at="2026-09-11T12:00:00Z",
             user_id="default"):
    return {
        "log_id": log_id,
        "user_id": user_id,
        "log_date": log_date,
        "bottle": bottle,
        "fl_oz": fl_oz,
        "created_at": created_at,
    }


# ---------------------------------------------------------------------------
# summarize()
# ---------------------------------------------------------------------------

def test_two_dates_mixed_bottles_sum_correctly():
    rows = [
        make_row("1", "2026-09-10", "big", "32"),
        make_row("2", "2026-09-10", "small", "26"),
        make_row("3", "2026-09-11", "big", "32"),
        make_row("4", "2026-09-11", "big", "32"),
    ]
    result = gwd.summarize(rows)

    by_date = {r["date"]: r for r in result}
    assert by_date["2026-09-10"]["water_fl_oz"] == 58
    assert by_date["2026-09-11"]["water_fl_oz"] == 64


def test_counts_per_bottle():
    rows = [
        make_row("1", "2026-09-10", "big", "32"),
        make_row("2", "2026-09-10", "big", "32"),
        make_row("3", "2026-09-10", "small", "26"),
    ]
    result = gwd.summarize(rows)

    row = result[0]
    assert row["water_entries"] == 3
    assert row["water_big_count"] == 2
    assert row["water_small_count"] == 1


def test_water_pct_of_goal_rounds_to_one_decimal():
    rows = [
        make_row("1", "2026-09-10", "big", "32"),
        make_row("2", "2026-09-10", "small", "26"),
    ]
    result = gwd.summarize(rows)

    row = result[0]
    # 58 / 128 * 100 = 45.3125 -> 45.3
    assert row["water_fl_oz"] == 58
    assert row["water_goal_fl_oz"] == gwd.WATER_GOAL_FL_OZ
    assert row["water_pct_of_goal"] == round(58 / 128 * 100, 1)


def test_summarize_empty_list_returns_empty_list():
    assert gwd.summarize([]) == []


def test_summarize_sorted_by_date_ascending():
    rows = [
        make_row("1", "2026-09-12", "big", "32"),
        make_row("2", "2026-09-10", "big", "32"),
        make_row("3", "2026-09-11", "big", "32"),
    ]
    result = gwd.summarize(rows)

    assert [r["date"] for r in result] == ["2026-09-10", "2026-09-11", "2026-09-12"]


def test_malformed_fl_oz_row_is_skipped_with_warning(capsys):
    rows = [
        make_row("1", "2026-09-10", "big", "not-a-number"),
        make_row("2", "2026-09-10", "small", "26"),
    ]
    result = gwd.summarize(rows)

    captured = capsys.readouterr()
    assert "WARNING" in captured.out or "WARNING" in captured.err

    row = result[0]
    assert row["water_fl_oz"] == 26
    assert row["water_entries"] == 1
    assert row["water_big_count"] == 0
    assert row["water_small_count"] == 1


def test_malformed_row_does_not_crash():
    rows = [make_row("1", "2026-09-10", "big", "")]
    # Should not raise.
    result = gwd.summarize(rows)
    assert result == []


# ---------------------------------------------------------------------------
# main()
# ---------------------------------------------------------------------------

def test_main_empty_log_writes_header_only(tmp_path):
    water_log = tmp_path / "water_log.csv"
    dashboard = tmp_path / "Water_Data_Dashboard.csv"

    with open(water_log, "w", newline="", encoding="utf-8") as f:
        f.write("log_id,user_id,log_date,bottle,fl_oz,created_at\n")

    gwd.main(["--water-log", str(water_log), "--dashboard", str(dashboard)])

    with open(dashboard, newline="", encoding="utf-8") as f:
        reader = csv.reader(f)
        rows = list(reader)

    assert rows == [
        ["date", "water_fl_oz", "water_goal_fl_oz", "water_pct_of_goal",
         "water_entries", "water_big_count", "water_small_count"]
    ]


def test_main_writes_expected_rows(tmp_path):
    water_log = tmp_path / "water_log.csv"
    dashboard = tmp_path / "Water_Data_Dashboard.csv"

    with open(water_log, "w", newline="", encoding="utf-8") as f:
        f.write("log_id,user_id,log_date,bottle,fl_oz,created_at\n")
        f.write("1,default,2026-09-10,big,32,2026-09-10T12:00:00Z\n")
        f.write("2,default,2026-09-10,small,26,2026-09-10T12:05:00Z\n")

    gwd.main(["--water-log", str(water_log), "--dashboard", str(dashboard)])

    with open(dashboard, newline="", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        rows = list(reader)

    assert len(rows) == 1
    assert rows[0]["date"] == "2026-09-10"
    assert rows[0]["water_fl_oz"] == "58"
    assert rows[0]["water_goal_fl_oz"] == "128"
    assert rows[0]["water_entries"] == "2"
    assert rows[0]["water_big_count"] == "1"
    assert rows[0]["water_small_count"] == "1"
