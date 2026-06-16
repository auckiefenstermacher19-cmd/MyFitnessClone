"""
sync_food_library.py
--------------------
Reads food_library.csv and updates the FOODS array inside Food_Log_Entry.html
so the food entry UI always reflects the current food library.

Run automatically by GitHub Actions whenever food_library.csv changes.
Can also be run locally after adding a new food to food_library.csv.

Usage
-----
    python sync_food_library.py

    # override paths if needed
    python sync_food_library.py \\
        --food-library food_library.csv \\
        --html         Food_Log_Entry.html

How it works
------------
The script looks for two sentinel comments inside Food_Log_Entry.html:

    // @@FOODS_START@@
    const FOODS = [ ... ];
    // @@FOODS_END@@

Everything between (and including) those two lines is replaced with a freshly
generated FOODS array built from food_library.csv. The rest of the HTML file
is untouched.
"""

import argparse
import csv
import os
import sys

DEFAULT_FOOD_LIB = "food_library.csv"
DEFAULT_HTML     = "Food_Log_Entry.html"

SENTINEL_START   = "// @@FOODS_START@@"
SENTINEL_END     = "// @@FOODS_END@@"


def load_foods(path):
    """Return list of (food_name, food_id) from food_library.csv, in file order."""
    foods = []
    with open(path, newline="", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            foods.append((row["food_name"], row["food_id"]))
    return foods


def build_foods_block(foods):
    """
    Build the replacement block — sentinel open, FOODS array, sentinel close.
    Aligns the id: values for readability.
    """
    if not foods:
        raise ValueError("food_library.csv contains no food rows")

    max_name_len = max(len(name) for name, _ in foods)

    lines = []
    lines.append("    // @@FOODS_START@@")
    lines.append("    const FOODS = [")
    for name, fid in foods:
        padding = " " * (max_name_len - len(name) + 2)
        lines.append(f'      {{ name: "{name}",{padding}id: "{fid}" }},')
    lines.append("    ];")
    lines.append("    // @@FOODS_END@@")

    return "\n".join(lines)


def update_html(html_path, foods_block):
    """
    Replace the block between @@FOODS_START@@ and @@FOODS_END@@ in the HTML file.
    Returns (updated_content, changed: bool).
    """
    with open(html_path, "r", encoding="utf-8") as f:
        content = f.read()

    if SENTINEL_START not in content:
        raise ValueError(
            f"Sentinel '{SENTINEL_START}' not found in {html_path}.\n"
            "The HTML file must contain the markers:\n"
            "    // @@FOODS_START@@\n"
            "    // @@FOODS_END@@\n"
            "around the FOODS array."
        )
    if SENTINEL_END not in content:
        raise ValueError(
            f"Sentinel '{SENTINEL_END}' not found in {html_path}."
        )

    # Locate the full block (from start sentinel line to end sentinel line inclusive)
    lines        = content.split("\n")
    start_idx    = next(i for i, l in enumerate(lines) if SENTINEL_START in l)
    end_idx      = next(i for i, l in enumerate(lines) if SENTINEL_END in l)

    if end_idx <= start_idx:
        raise ValueError(
            f"@@FOODS_END@@ (line {end_idx+1}) must come after "
            f"@@FOODS_START@@ (line {start_idx+1})"
        )

    old_block = "\n".join(lines[start_idx : end_idx + 1])

    if old_block == foods_block:
        return content, False   # nothing to change

    new_content = content.replace(old_block, foods_block, 1)
    return new_content, True


def parse_args():
    p = argparse.ArgumentParser(
        description="Sync food_library.csv → Food_Log_Entry.html FOODS array"
    )
    p.add_argument("--food-library", default=DEFAULT_FOOD_LIB,
                   help="Path to food_library.csv")
    p.add_argument("--html",         default=DEFAULT_HTML,
                   help="Path to Food_Log_Entry.html")
    return p.parse_args()


def main():
    args = parse_args()

    # Validate inputs
    for label, path in [("food_library", args.food_library), ("html", args.html)]:
        if not os.path.exists(path):
            print(f"ERROR: {label} not found at '{path}'")
            sys.exit(1)

    print(f"Reading food library : {args.food_library}")
    foods = load_foods(args.food_library)
    print(f"  {len(foods)} food(s) found:")
    for name, fid in foods:
        print(f"    {name!r:45s} → {fid!r}")

    print(f"\nBuilding FOODS array...")
    foods_block = build_foods_block(foods)

    print(f"Updating HTML        : {args.html}")
    try:
        new_content, changed = update_html(args.html, foods_block)
    except ValueError as e:
        print(f"ERROR: {e}")
        sys.exit(1)

    if not changed:
        print("No changes needed — FOODS array already matches food_library.csv")
        sys.exit(0)

    with open(args.html, "w", encoding="utf-8") as f:
        f.write(new_content)

    print(f"Updated: {args.html}")
    print(f"FOODS array now contains {len(foods)} food(s)")


if __name__ == "__main__":
    main()
