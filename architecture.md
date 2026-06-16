# Excel-to-GitHub Nutrition Tracking Platform
## Architecture & Data Migration Plan

**Document Classification:** Principal Architecture Specification  
**Source Workbook:** `MyfitnessPal_Clone_-_Final.xlsm`  
**Prepared For:** Repository Developers, AI Coding Agents, Data Engineers, Future Maintainers  
**Status:** Pre-Implementation Discovery Complete

---

## 1. Workbook Executive Summary

The workbook is a functional personal nutrition tracker built entirely in Excel, modeled after MyFitnessPal's core feature set. It implements a complete data pipeline — from food reference data through consumption logging through daily dashboard reporting — across five worksheets with zero external dependencies.

**Architecture in plain terms:** The workbook operates as a 3-layer system:

```
[Reference Layer]          →  Food Library + Reference sheets (static)
[Transaction Layer]        →  Food Entry + Meal Data sheets (append-only log)
[Reporting Layer]          →  DashBoard sheet (derived, date-filtered)
```

**Current state assessment:** The workbook is a well-structured MVP. Its core calculation logic is correct and consistent. However, it has meaningful architectural weaknesses that must be addressed during migration rather than replicated:

- The Dashboard is locked to a **single selected date** — no historical trend views, weekly summaries, or rolling averages exist
- The Food Library header contains a **non-breaking space** character (`\xa0`) appended to "Food" — a data quality defect
- Column naming is **duplicated** in both Food Library and Meal Data (per-serving and per-gram sections share identical headers with no namespace separation)
- Goal values are **hardcoded** in the Dashboard, not stored in a configurable reference table
- Micronutrient units are **inconsistent** in the Reference sheet (vitamins stored as "% DV" in the category column but as absolute units `mcg/IU` in the metrics column)
- The Food Entry sheet is a **single-row input form** — it does not batch-submit to Meal Data; the submission mechanism (likely a VBA macro) is not extractable from this read-only analysis

**Migration verdict:** Migrate the data architecture as designed, but do not replicate its structural limitations. The CSV layer should be clean and normalized. Business logic (calculations, aggregations) belongs in application or query logic, not in CSV files.

---

## 2. Worksheet-by-Worksheet Analysis

### 2.1 Sheet: `DashBoard`

**Purpose:** Single-day nutrition reporting view. Displays actual vs. goal comparisons for calories, macronutrients, and micronutrients, broken down both as daily totals and per meal type.

**User interaction:** The user sets a target date in cell `C2`. All metrics recalculate dynamically against that date. No other user inputs exist on this sheet.

**Data source:** Reads exclusively from `Meal Data` columns X through AO (the "consumed totals" columns — per-gram values multiplied by grams consumed).

**Key structural sections (row map):**

| Section | Excel Rows | Content |
|---|---|---|
| Date selector | Row 2 | User input: target date (`C2`) |
| Calories Total | Rows 5–10 | Daily calorie actual, goal, delta |
| Calories by Meal | Rows 12–16 | Breakfast/Lunch/Dinner/Snack breakdown + % of total |
| Macros Total | Rows 19–24 | Fat, Carbs, Protein: actual/goal/delta/total |
| Macros Index | Rows 26–28 | Actual ÷ Goal ratio for each macro (≥1.0 = met/exceeded goal) |
| Macros by Meal | Rows 34–38 | Macro breakdown per meal type |
| Micros Total | Rows 40–45 | 9 micronutrients: actual/goal/delta |
| Micros % | Rows 47–49 | Actual ÷ Goal ratio per micronutrient |
| Micros by Meal | Rows 54–58 | Micronutrient breakdown per meal type |

**Hardcoded goals (critical — must be externalized):**

| Nutrient | Goal Value | Unit |
|---|---|---|
| Calories | 4,000 | kcal |
| Total Fat | 200 | g |
| Total Carbohydrates | 400 | g |
| Protein | 250 | g |
| Macro Total (Fat+Carbs+Protein) | 850 | g |
| Calories per Meal (3 meals) | 1,333.33 each | kcal |
| Sodium | 4,000 | mg |
| Potassium | 4,700 | mg |
| Dietary Fiber | 45 | g |
| Sugars | 80 | g |
| Vitamin A | 900 | mcg RAE |
| Vitamin C | 500 | mg |
| Vitamin D | 50 | mcg |
| Calcium | 1,200 | mg |
| Iron | 15 | mg |

**Assumption documented:** Calorie goal is split equally across Breakfast/Lunch/Dinner (`C9/3`). Snack has no calorie goal. This is hardcoded logic, not a user setting.

**No historical views exist.** The dashboard cannot show trends, weekly averages, or multi-day comparisons in its current form.

---

### 2.2 Sheet: `Food Entry`

**Purpose:** Data entry form for logging a meal. Provides a structured interface for the user to input Date, Meal type, Food selection (dropdown), and Grams consumed.

**User inputs:**

| Field | Cell | Type | Notes |
|---|---|---|---|
| Date | `E2` | Formula | `=TODAY()` — auto-populates to current date; user can override |
| Meal | `E3` | Dropdown | Validated list: Breakfast / Lunch / Dinner / Snack |
| Food | `E4` | Dropdown | References Food Library column A |
| Grams | `E5` | Numeric | Free-form user entry |

**Submission mechanism:** There is no visible formula that appends data to Meal Data. A VBA macro is the strongly implied mechanism (the file is `.xlsm` — macro-enabled). The macro is not extractable from static analysis. This is an **open question** (see Section 11).

**Data flow:** Food Entry → [VBA macro append] → Meal Data row

---

### 2.3 Sheet: `Meal Data`

**Purpose:** The primary transaction log. Each row represents one food item consumed in one meal on one date. This is the source of truth for all Dashboard calculations.

**Total data rows observed:** 35 rows across 3 distinct dates (April 16, April 17, April 29, 2026).

**Meal distribution:** Breakfast (9), Lunch (11), Dinner (11), Snack (3)

**Unique foods logged:** ButcherBox 85/15 Beef, WFM Organic Sweet Potato, 365 White Quinoa, Medium Hass Avocado, Organic Valley Grassmilk Cheddar, Vital Farms Large Eggs, ButcherBox Grass-Fed Ribeye, ButcherBox Chuck Roast, Nature Made D3 Gummies, Garden of Life Vitamin C

**Column architecture — two distinct zones:**

**Zone 1 — Per-Gram Rate Columns (A–V, columns 1–22):**
These are XLOOKUP values from Food Library columns V–AM (per-gram rates). They store the *rate*, not the consumed amount.

| Col | Excel | Field | Source |
|---|---|---|---|
| 1 | A | Date | User input |
| 2 | B | Meal | User input |
| 3 | C | Food | User input (dropdown) |
| 4 | D | Grams | User input |
| 5 | E | Calories_per_gram | XLOOKUP → Food Library V |
| 6 | F | Total_Fat_per_gram | XLOOKUP → Food Library W |
| 7 | G | Total_Carbohydrates_per_gram | XLOOKUP → Food Library X |
| 8 | H | Protein_per_gram | XLOOKUP → Food Library Y |
| 9 | I | Saturated_Fat_per_gram | XLOOKUP → Food Library Z |
| 10 | J | Polyunsaturated_Fat_per_gram | XLOOKUP → Food Library AA |
| 11 | K | Monounsaturated_Fat_per_gram | XLOOKUP → Food Library AB |
| 12 | L | Trans_Fat_per_gram | XLOOKUP → Food Library AC |
| 13 | M | Cholesterol_per_gram | XLOOKUP → Food Library AD |
| 14 | N | Sodium_per_gram | XLOOKUP → Food Library AE |
| 15 | O | Potassium_per_gram | XLOOKUP → Food Library AF |
| 16 | P | Dietary_Fiber_per_gram | XLOOKUP → Food Library AG |
| 17 | Q | Sugars_per_gram | XLOOKUP → Food Library AH |
| 18 | R | Vitamin_A_per_gram | XLOOKUP → Food Library AI |
| 19 | S | Vitamin_C_per_gram | XLOOKUP → Food Library AJ |
| 20 | T | Vitamin_D_per_gram | XLOOKUP → Food Library AK |
| 21 | U | Calcium_per_gram | XLOOKUP → Food Library AL |
| 22 | V | Iron_per_gram | XLOOKUP → Food Library AM |
| 23 | W | *(empty separator column)* | — |

**Zone 2 — Consumed Total Columns (X–AO, columns 24–41):**
These are the actual consumed amounts. Formula: `=$D{row} * {per_gram_col}`. This is what the Dashboard reads.

| Col | Excel | Field | Formula |
|---|---|---|---|
| 24 | X | Calories_consumed | =D * E |
| 25 | Y | Total_Fat_consumed | =D * F |
| 26 | Z | Total_Carbohydrates_consumed | =D * G |
| 27 | AA | Protein_consumed | =D * H |
| 28 | AB | Saturated_Fat_consumed | =D * I |
| 29 | AC | Polyunsaturated_Fat_consumed | =D * J |
| 30 | AD | Monounsaturated_Fat_consumed | =D * K |
| 31 | AE | Trans_Fat_consumed | =D * L |
| 32 | AF | Cholesterol_consumed | =D * M |
| 33 | AG | Sodium_consumed | =D * N |
| 34 | AH | Potassium_consumed | =D * O |
| 35 | AI | Dietary_Fiber_consumed | =D * P |
| 36 | AJ | Sugars_consumed | =D * Q |
| 37 | AK | Vitamin_A_consumed | =D * R |
| 38 | AL | Vitamin_C_consumed | =D * S |
| 39 | AM | Vitamin_D_consumed | =D * T |
| 40 | AN | Calcium_consumed | =D * U |
| 41 | AO | Iron_consumed | =D * V |

---

### 2.4 Sheet: `Food Library`

**Purpose:** Master reference table for all foods. Contains 10 food items. Each row defines a food's nutritional profile at the serving level, then auto-calculates per-gram rates in columns V–AM.

**Food items:**

| # | Food Name | Grams/Serving |
|---|---|---|
| 1 | ButcherBox 85/15 Beef | 112g |
| 2 | WFM Organic Sweet Potato | 130g |
| 3 | 365 White Quinoa | 45g |
| 4 | Medium Hass Avocado | 136g |
| 5 | Organic Valley Grassmilk Cheddar | 28g |
| 6 | Vital Farms Large Eggs | 50g |
| 7 | ButcherBox Grass-Fed Ribeye | 112g |
| 8 | ButcherBox Chuck Roast | 112g |
| 9 | Nature Made D3 Gummies | 5g |
| 10 | Garden of Life Vitamin C | 0.5g |

**Column architecture — two zones:**

**Zone 1 — Per-Serving Values (Columns A–T):**

| Col | Field | Unit |
|---|---|---|
| A | Food_Name | Text |
| B | Grams_per_Serving | g |
| C | Calories | kcal |
| D | Total_Fat | g |
| E | Total_Carbohydrates | g |
| F | Protein | g |
| G | Saturated_Fat | g |
| H | Polyunsaturated_Fat | g |
| I | Monounsaturated_Fat | g |
| J | Trans_Fat | g |
| K | Cholesterol | mg |
| L | Sodium | mg |
| M | Potassium | mg |
| N | Dietary_Fiber | g |
| O | Sugars | g |
| P | Vitamin_A | mcg RAE / IU |
| Q | Vitamin_C | mg |
| R | Vitamin_D | mcg / IU |
| S | Calcium | mg |
| T | Iron | mg |
| U | *(empty separator)* | — |

**Zone 2 — Per-Gram Rates (Columns V–AM):**
Formula: `={per_serving_col} / $B{row}`

| Col | Field | Formula Pattern |
|---|---|---|
| V | Calories_per_gram | =C/B |
| W | Total_Fat_per_gram | =D/B |
| X | Total_Carbohydrates_per_gram | =E/B |
| Y | Protein_per_gram | =F/B |
| Z | Saturated_Fat_per_gram | =G/B |
| AA | Polyunsaturated_Fat_per_gram | =H/B |
| AB | Monounsaturated_Fat_per_gram | =I/B |
| AC | Trans_Fat_per_gram | =J/B |
| AD | Cholesterol_per_gram | =K/B |
| AE | Sodium_per_gram | =L/B |
| AF | Potassium_per_gram | =M/B |
| AG | Dietary_Fiber_per_gram | =N/B |
| AH | Sugars_per_gram | =O/B |
| AI | Vitamin_A_per_gram | =P/B |
| AJ | Vitamin_C_per_gram | =Q/B |
| AK | Vitamin_D_per_gram | =R/B |
| AL | Calcium_per_gram | =S/B |
| AM | Iron_per_gram | =T/B |

**Data quality issues identified:**
- Column A header has a trailing non-breaking space (`\xa0`) — a silent defect that would break string matching in code
- `Garden of Life Vitamin C` has a double space in the name ("Life  Vitamin") — inconsistent naming
- `Vitamin A` for `WFM Organic Sweet Potato` = 920 IU; for `Organic Valley Grassmilk Cheddar` = 84 mcg RAE — units are **mixed** across foods with no flag

---

### 2.5 Sheet: `Reference`

**Purpose:** Documentation/metadata sheet. Contains three sub-tables describing the data schema:

**Sub-table 1 — Column Catalog (columns A–C):** Lists every column name and its category (Identity, Macros, Fat Details, Other Macros, Micros) with unit of measure.

**Sub-table 2 — Metric Definitions (columns G–H):** Lists every metric and its unit of measure. Used as a lookup/legend.

**Sub-table 3 — Goal Targets (columns J–L):** Lists optimum daily intake per nutrient. These values match what is hardcoded in the Dashboard.

**Critical finding:** The Reference sheet goal table and the Dashboard hardcoded values are **redundant and unsynchronized**. If a goal changes in Reference, the Dashboard does not update. This is a bug waiting to happen.

---

## 3. Data Relationship Mapping

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WORKBOOK DATA FLOW                           │
└─────────────────────────────────────────────────────────────────────┘

[Reference Sheet]
  └── Goal Targets (static metadata)
  └── Column Catalog (documentation only)
          │
          │  (no live formula linkage — documentation only)
          ▼
[Food Library Sheet]
  ├── Columns A–T: Per-serving nutritional data (user-entered)
  └── Columns V–AM: Per-gram rates (=per_serving / grams_per_serving)
          │
          │  XLOOKUP (Meal Data cols E–V)
          ▼
[Food Entry Sheet]   ──[VBA macro]──►  [Meal Data Sheet]
  ├── Date (=TODAY())                    ├── Cols A–D: User inputs
  ├── Meal (dropdown)                    ├── Cols E–V: Per-gram rates (XLOOKUP from Food Library)
  ├── Food (dropdown)                    ├── Col W: Empty separator
  └── Grams (numeric)                   └── Cols X–AO: Consumed totals (=Grams × per_gram_rate)
                                                  │
                                                  │  SUMIFS (filtered by Date + optional Meal)
                                                  ▼
                                         [DashBoard Sheet]
                                           ├── Daily Calorie KPIs
                                           ├── Calories by Meal
                                           ├── Macro Totals + by Meal
                                           └── Micro Totals + by Meal
```

**Dependency chain:**
`Reference (goals)` → Dashboard goals (hardcoded, not linked)
`Food Library (per-gram rates)` → `Meal Data (XLOOKUP)` → `Dashboard (SUMIFS)`

---

## 4. CSV Architecture Recommendation

The workbook maps cleanly to **four CSV files**. The per-gram calculation layer (currently embedded in both Food Library and Meal Data) should **not** be stored in CSVs — it is computable and belongs in application logic.

### Recommended CSV Files

| File | Contents | Rows (current) | Primary Key |
|---|---|---|---|
| `reference.csv` | Units, nutrient goals, categories | ~20 | `nutrient_name` |
| `food_library.csv` | Food items, per-serving nutrition | 10 | `food_id` |
| `meal_log.csv` | Daily consumption records | 35 | `log_id` |
| `user_goals.csv` | Daily nutrition targets per user | 1 | `user_id` |

**Architectural decision — why four, not three:**
The original workbook conflates two conceptually distinct things: (1) reference/lookup data (`reference.csv`) and (2) user-specific goal configuration (`user_goals.csv`). Separating them enables multi-user support and goal history without touching reference data.

**What gets eliminated in migration:**
- Per-gram columns in Food Library (V–AM) → computed at query time
- Consumed total columns in Meal Data (X–AO) → computed at query time
- Dashboard hardcoded goal values → read from `user_goals.csv`

---

## 5. Food Library Analysis

### Current Data (Complete)

| Food | Serving (g) | Cal | Fat(g) | Carbs(g) | Prot(g) | SatFat | PUFA | MUFA | Trans | Chol(mg) | Na(mg) | K(mg) | Fiber | Sugar | VitA | VitC | VitD | Ca(mg) | Fe(mg) |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| ButcherBox 85/15 Beef | 112 | 240 | 17 | 0 | 22 | 7 | 0.5 | 7.4 | 1 | 70 | 55 | 330 | 0 | 0 | 0 | 0 | 0.1 | 0 | 1.8 |
| WFM Organic Sweet Potato | 130 | 112 | 0.1 | 26 | 2 | 0 | 0.02 | 0.01 | 0 | 0 | 72 | 438 | 4 | 5 | 920 | 3 | 0.1 | 39 | 0.8 |
| 365 White Quinoa | 45 | 160 | 2.5 | 31 | 6 | 0 | 1.3 | 0.6 | 0 | 0 | 0 | 250 | 3 | 1 | 0 | 0 | 0 | 0 | 1.8 |
| Medium Hass Avocado | 136 | 227 | 21 | 12 | 3 | 3 | 2.7 | 13.3 | 0 | 0 | 10 | 660 | 9 | 1 | 10 | 12 | 0 | 16 | 1 |
| Organic Valley Grassmilk Cheddar | 28 | 110 | 9 | 1 | 6 | 5 | 0.4 | 3 | 0 | 30 | 180 | 20 | 0 | 0 | 84 | 0 | 0 | 200 | 0 |
| Vital Farms Large Eggs | 50 | 70 | 5 | 0 | 6 | 1.5 | 1 | 2 | 0 | 185 | 70 | 70 | 0 | 0 | 80 | 0 | 1 | 30 | 0.9 |
| ButcherBox Grass-Fed Ribeye | 112 | 240 | 17 | 0 | 22 | 8 | 0.5 | 11 | 1 | 60 | 70 | 260 | 0 | 0 | 0 | 0 | 0.1 | 10 | 1.9 |
| ButcherBox Chuck Roast | 112 | 210 | 14 | 0 | 21 | 6 | 0.4 | 7 | 1 | 75 | 86 | 385 | 0 | 0 | 0 | 0 | 0.1 | 20 | 2.4 |
| Nature Made D3 Gummies | 5 | 15 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 | 5 | 0 | 0 | 2 | 0 | 0 | 50 | 0 | 0 |
| Garden of Life Vitamin C | 0.5 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 500 | 0 | 0 | 0 |

### Per-Gram Calculation Verification

The formula is: `per_gram_value = per_serving_value ÷ grams_per_serving`

Verified for ButcherBox 85/15 Beef (112g serving):
- Calories: 240 ÷ 112 = **2.1429 kcal/g** ✓
- Protein: 22 ÷ 112 = **0.1964 g/g** ✓
- Sodium: 55 ÷ 112 = **0.4911 mg/g** ✓

The formula is applied identically to all 18 nutritional fields across all 10 foods.

### Data Quality Issues

**Issue 1 — Header trailing non-breaking space:** Column A header is `"Food\xa0"` not `"Food"`. Will cause silent failures in any code doing header-based column access.

**Issue 2 — Double space in food name:** `"Garden of Life  Vitamin C"` contains two consecutive spaces between "Life" and "Vitamin". Must be normalized.

**Issue 3 — Mixed Vitamin A units:** The workbook does not distinguish between mcg RAE and IU. Sweet potato at 920 and cheese at 84 are almost certainly in different units (IU vs mcg RAE). This requires data stewardship before migration — do not carry the ambiguity into the CSV.

**Issue 4 — Supplement vs. food conflation:** Nature Made D3 Gummies and Garden of Life Vitamin C are supplements tracked alongside whole foods. The current schema has no `food_type` or `category` field. A `food_category` column should be added.

**Issue 5 — No food ID:** The food name is the only identifier. Renaming a food breaks the XLOOKUP relationship. A synthetic primary key is required.

### Recommended `food_library.csv` Schema

```
food_id           TEXT (UUID or slug, e.g. "butcherbox-8515-beef")
food_name         TEXT (cleaned, no trailing spaces, no double spaces)
food_category     TEXT (whole_food | supplement | ingredient | packaged)
brand             TEXT (nullable)
grams_per_serving DECIMAL(8,3)
serving_unit      TEXT (g | oz | piece | etc.)
serving_size_label TEXT (e.g. "4 oz", "1 medium", "2 gummies")
calories          DECIMAL(8,2) [kcal]
total_fat         DECIMAL(8,3) [g]
total_carbs       DECIMAL(8,3) [g]
protein           DECIMAL(8,3) [g]
saturated_fat     DECIMAL(8,3) [g]
polyunsaturated_fat DECIMAL(8,3) [g]
monounsaturated_fat DECIMAL(8,3) [g]
trans_fat         DECIMAL(8,3) [g]
cholesterol       DECIMAL(8,2) [mg]
sodium            DECIMAL(8,2) [mg]
potassium         DECIMAL(8,2) [mg]
dietary_fiber     DECIMAL(8,3) [g]
sugars            DECIMAL(8,3) [g]
vitamin_a         DECIMAL(10,3) [mcg RAE — standardize to mcg RAE, convert IU entries]
vitamin_a_unit    TEXT (mcg_rae | IU — transitional column, drop after normalization)
vitamin_c         DECIMAL(8,2) [mg]
vitamin_d         DECIMAL(8,3) [mcg — standardize to mcg, convert IU entries]
vitamin_d_unit    TEXT (mcg | IU — transitional column)
calcium           DECIMAL(8,2) [mg]
iron              DECIMAL(8,3) [mg]
source_url        TEXT (nullable — link to USDA or brand nutrition page)
created_at        ISO8601 datetime
updated_at        ISO8601 datetime
```

**Note on per-gram values:** Do NOT store per-gram values in the CSV. They are derived (`per_gram = per_serving / grams_per_serving`) and storing them creates a synchronization risk. Compute them at query time or in an application model.

---

## 6. Meal Data Analysis

### User Workflow

1. User opens `Food Entry` sheet
2. Date auto-populates to today (overridable)
3. User selects Meal type from dropdown
4. User selects Food from dropdown (sourced from Food Library column A)
5. User enters Grams consumed
6. User triggers VBA macro (button not visible in static analysis) → row appended to `Meal Data`

### Meal Data Calculation Logic (Verified)

**Step 1 — Rate lookup (Meal Data cols E–V):**
```
per_gram_rate = XLOOKUP(food_name, FoodLibrary.A:A, FoodLibrary.V:AM)
```

**Step 2 — Consumed total (Meal Data cols X–AO):**
```
nutrient_consumed = grams_entered × per_gram_rate
```

**Example verification (Vital Farms Large Eggs, 285g, Breakfast 2026-04-29):**
- Protein per gram: 6 ÷ 50 = 0.12 g/g
- Protein consumed: 0.12 × 285 = **34.2g** ✓ (matches workbook value 34.1999...)

### Recommended `meal_log.csv` Schema

```
log_id        TEXT (UUID — surrogate key)
user_id       TEXT (FK → users table; use "default" for single-user MVP)
log_date      DATE (YYYY-MM-DD)
meal_type     TEXT (Breakfast | Lunch | Dinner | Snack)
food_id       TEXT (FK → food_library.food_id)
food_name     TEXT (denormalized snapshot — preserves historical name at time of logging)
grams         DECIMAL(8,2)
created_at    ISO8601 datetime
```

**Critical architectural decision — no calculated columns in the log:**

The Excel `Meal Data` sheet stores per-gram rates and consumed totals in 36 computed columns. In the new architecture, these are eliminated from the CSV. All nutrition calculations are performed by the application layer or SQL queries:

```sql
-- Example: compute consumed protein for a log entry
SELECT
  ml.log_id,
  ml.log_date,
  ml.meal_type,
  ml.food_name,
  ml.grams,
  ml.grams * fl.protein / fl.grams_per_serving AS protein_consumed_g
FROM meal_log ml
JOIN food_library fl ON ml.food_id = fl.food_id
WHERE ml.log_date = '2026-04-29';
```

This is superior to the Excel approach because:
- No redundant data storage
- No synchronization risk if food library values are corrected
- Grams is the only write-once, human-entered value — everything else is computable

### Validation Rules

| Field | Rule |
|---|---|
| log_date | Must be a valid date, not in future by more than 1 day |
| meal_type | Must be one of: Breakfast, Lunch, Dinner, Snack |
| food_id | Must exist in food_library.csv |
| grams | Must be > 0, <= 5000 (reasonable upper bound) |

---

## 7. Dashboard Reverse Engineering

### Formula Architecture

All Dashboard metrics are `SUMIFS` aggregations over `Meal Data` columns X–AO, filtered by:
- **Always:** `Meal Data.Date = Dashboard.C2` (selected date)
- **Optionally:** `Meal Data.Meal = [meal type label]`

### Complete KPI Inventory

#### KPI Group 1: Daily Calorie Summary

| KPI | Formula | Source Column | Description |
|---|---|---|---|
| Calories Actual | `SUMIFS(MealData.X, Date=C2)` | Meal Data col X | Sum of all calories consumed on selected date |
| Calories Goal | Hardcoded `4000` | — | Daily calorie target |
| Calories Delta | `Goal - Actual` | — | Remaining/overage |

**Rebuild query:**
```sql
SELECT
  SUM(ml.grams * fl.calories / fl.grams_per_serving) AS calories_actual
FROM meal_log ml
JOIN food_library fl ON ml.food_id = fl.food_id
WHERE ml.log_date = :selected_date;
```

#### KPI Group 2: Calories by Meal

| KPI | Formula | Description |
|---|---|---|
| Breakfast Calories | `SUMIFS(X, Date=C2, Meal="Breakfast")` | Breakfast total |
| Lunch Calories | `SUMIFS(X, Date=C2, Meal="Lunch")` | Lunch total |
| Dinner Calories | `SUMIFS(X, Date=C2, Meal="Dinner")` | Dinner total |
| Snack Calories | `SUMIFS(X, Date=C2, Meal="Snack")` | Snack total |
| Meal % of Daily | `meal_calories / total_calories` | Proportional share |
| Meal Goal | `total_calorie_goal / 3` (Breakfast/Lunch/Dinner only) | Equal split of goal |
| Meal Delta | `Meal Goal - Meal Actual` | Per-meal variance |

#### KPI Group 3: Macronutrient Totals

| KPI | Meal Data Column | Description |
|---|---|---|
| Total Fat Actual | Col Y | Daily fat consumed |
| Total Carbs Actual | Col Z | Daily carbs consumed |
| Protein Actual | Col AA | Daily protein consumed |
| Macro Total (sum) | Y+Z+AA | Combined macro grams |
| Macro % (each) | nutrient / macro_total | Share of macro total |
| Macro Index | actual / goal | Achievement ratio (1.0 = goal met) |

**Goals:** Fat=200g, Carbs=400g, Protein=250g (all hardcoded)

#### KPI Group 4: Macros by Meal

Identical to KPI Group 3 but with additional `Meal =` filter. Produces 3 rows (Breakfast, Lunch, Dinner) × 3 columns (Fat, Carbs, Protein) plus totals and percentages.

#### KPI Group 5: Micronutrient Totals

| Micronutrient | Meal Data Column | Goal | Unit |
|---|---|---|---|
| Sodium | AG | 4,000 | mg |
| Potassium | AH | 4,700 | mg |
| Dietary Fiber | AI | 45 | g |
| Sugars | AJ | 80 | g |
| Vitamin A | AK | 900 | mcg RAE |
| Vitamin C | AL | 500 | mg |
| Vitamin D | AM | 50 | mcg |
| Calcium | AN | 1,200 | mg |
| Iron | AO | 15 | mg |

For each: `Actual = SUMIFS(col, Date=C2)`, `Delta = Goal - Actual`, `% = Actual / Goal`

#### KPI Group 6: Micros by Meal

Same as Group 5 with meal-type filter. Produces 3 rows × 9 columns.

### Missing Dashboard Features (Gap — Future State)

The current dashboard has **no** historical views. The following are not implemented and represent product expansion opportunities:

- 7-day rolling average for any nutrient
- Weekly summary (SUM by week)
- Monthly summary (SUM by month)
- Streak tracking (consecutive days hitting calorie/protein goal)
- Trend charts (line charts across dates)
- Worst-performing day detection
- Food frequency analysis ("you ate avocado 6 times this month")

All of these are computable from `meal_log.csv` + `food_library.csv` with date-range queries.

---

## 8. Data Model & Entity Relationships

### Entity Relationship Diagram (Text)

```
┌──────────────────┐         ┌───────────────────┐
│   user_goals     │         │   food_library    │
│──────────────────│         │───────────────────│
│ PK goal_id       │         │ PK food_id        │
│ FK user_id       │         │    food_name      │
│    goal_date     │         │    food_category  │
│    calories      │         │    brand          │
│    total_fat     │         │    grams_per_     │
│    total_carbs   │         │      serving      │
│    protein       │         │    serving_unit   │
│    sodium        │         │    calories       │
│    potassium     │         │    total_fat      │
│    ...micros...  │         │    total_carbs    │
└──────────────────┘         │    protein        │
         │                   │    ...micros...   │
         │ FK                └───────────────────┘
         │                            │
         ▼                            │ FK (food_id)
┌──────────────────┐                  │
│   users          │         ┌────────▼──────────┐
│──────────────────│         │    meal_log       │
│ PK user_id       │◄────────│───────────────────│
│    display_name  │    FK   │ PK log_id         │
│    created_at    │         │ FK user_id        │
└──────────────────┘         │ FK food_id        │
                             │    food_name_snap │
                             │    log_date       │
                             │    meal_type      │
                             │    grams          │
                             │    created_at     │
                             └───────────────────┘
                                       │
                              (computed at query time)
                                       │
                                       ▼
                             ┌───────────────────┐
                             │  [derived view]   │
                             │  daily_nutrition  │
                             │───────────────────│
                             │  log_date         │
                             │  meal_type        │
                             │  calories_consumed│
                             │  protein_consumed │
                             │  fat_consumed     │
                             │  ...etc...        │
                             └───────────────────┘

┌──────────────────┐
│   reference      │
│──────────────────│
│ PK nutrient_name │
│    category      │
│    unit          │
│    display_order │
└──────────────────┘
```

### Computation Rules (Application Layer — Not Stored in CSV)

```
# Per-gram rate (derived from food_library)
calories_per_gram = calories / grams_per_serving

# Consumed nutrient (derived from meal_log JOIN food_library)
calories_consumed = grams_logged * (calories / grams_per_serving)

# Daily total (aggregation)
daily_calories = SUM(calories_consumed) WHERE log_date = target_date

# Goal achievement
goal_pct = actual / goal_value

# Meal share
meal_pct = meal_total / daily_total
```

---

## 9. GitHub Repository Structure

```
nutrition-tracker/
│
├── README.md                          # Project overview, setup, data dictionary
├── LICENSE
├── .gitignore
├── CHANGELOG.md
│
├── data/
│   ├── README.md                      # Data schema documentation
│   ├── source/                        # Raw CSV exports — source of truth
│   │   ├── food_library.csv           # Master food/nutrient reference
│   │   ├── meal_log.csv               # All meal consumption records
│   │   ├── user_goals.csv             # Daily nutrition targets per user
│   │   └── reference.csv             # Nutrient metadata, units, categories
│   │
│   ├── processed/                     # Derived datasets (gitignored or generated)
│   │   └── .gitkeep
│   │
│   └── archive/
│       └── MyfitnessPal_Clone_-_Final.xlsm   # Original workbook (read-only reference)
│
├── schemas/
│   ├── food_library.schema.json       # JSON Schema for validation
│   ├── meal_log.schema.json
│   ├── user_goals.schema.json
│   └── reference.schema.json
│
├── scripts/
│   ├── migrate/
│   │   ├── export_food_library.py     # Extracts + cleans food library from xlsm
│   │   ├── export_meal_log.py         # Extracts meal log rows from xlsm
│   │   └── validate_migration.py      # Verifies CSV totals match workbook Dashboard
│   │
│   ├── validate/
│   │   ├── check_food_library.py      # Schema + data quality checks
│   │   ├── check_meal_log.py          # Referential integrity, range checks
│   │   └── check_all.sh              # Run all validations
│   │
│   └── analytics/
│       ├── daily_summary.py           # Reproduce Dashboard KPIs from CSV
│       ├── weekly_summary.py          # 7-day rollup (not in Excel — new)
│       └── food_frequency.py          # How often each food appears
│
├── queries/
│   ├── daily_nutrition.sql            # Core daily KPI query
│   ├── calories_by_meal.sql           # Meal-type breakdown
│   ├── macro_totals.sql               # Fat/Carbs/Protein aggregation
│   ├── micro_totals.sql               # Micronutrient aggregation
│   └── weekly_trend.sql              # 7-day rolling window
│
├── api/                               # Future: REST API layer
│   ├── README.md
│   └── .gitkeep
│
├── dashboard/                         # Future: reporting/visualization
│   ├── README.md
│   └── .gitkeep
│
├── docs/
│   ├── architecture.md               # This document
│   ├── data_dictionary.md            # Field-level definitions
│   ├── calculation_reference.md      # All formulas documented
│   ├── migration_log.md              # Migration decisions and rationale
│   └── dashboard_kpis.md            # KPI catalog for dashboard rebuild
│
└── tests/
    ├── test_calculations.py           # Unit tests: per-gram calcs, consumed totals
    ├── test_dashboard_parity.py       # Verify CSV analytics match Excel outputs
    └── fixtures/
        └── sample_meal_log.csv        # Small fixture for testing
```

### Branch Strategy

```
main          ← production-ready data and schemas only
dev           ← active development
feature/*     ← feature branches
migration/*   ← one-time migration scripts (can be deleted post-migration)
```

### `.gitignore` Essentials

```
data/processed/
*.pyc
__pycache__/
.env
*.log
.DS_Store
```

---

## 10. Migration Risks & Recommendations

### Risk 1 — VBA Macro Not Recoverable (HIGH)
**Issue:** The Food Entry submission mechanism is a VBA macro that appends rows to Meal Data. Static analysis cannot extract VBA code from `.xlsm` files. The exact append logic (column mapping, timestamp behavior, validation) is unknown.  
**Recommendation:** Open the workbook in Excel and review the VBA editor (Alt+F11) before migration. Document the macro logic. The replacement in the new system will be an API endpoint or script that validates and appends to `meal_log.csv`.

### Risk 2 — Vitamin A & D Unit Inconsistency (HIGH)
**Issue:** The food library mixes IU and mcg RAE for Vitamin A (and possibly IU and mcg for Vitamin D) without flagging which unit a given food uses. Sweet potato's 920 Vitamin A is plausibly IU; cheese's 84 is plausibly mcg RAE. If both are treated the same, micronutrient totals are meaningless.  
**Recommendation:** Verify each food's source label. Standardize to mcg RAE (Vitamin A) and mcg (Vitamin D) in the CSV. Add a transitional `vitamin_a_unit` column during migration and remove after normalization.

### Risk 3 — No Surrogate Keys (MEDIUM)
**Issue:** Food names are the only identifier. Any food name correction (e.g. fixing the double space in "Garden of Life  Vitamin C") breaks the join between `meal_log` and `food_library` unless `food_name_snap` is preserved in the log.  
**Recommendation:** Generate UUIDs or slugs for `food_id` during migration. Store `food_name` as a snapshot in `meal_log` at time of entry. Use `food_id` as the FK, not the name.

### Risk 4 — Goal Values Not Version-Controlled (MEDIUM)
**Issue:** Dashboard goals are hardcoded. If the user changes their goals, there is no history of what goals were active on which dates.  
**Recommendation:** `user_goals.csv` should include `effective_date` so historical goal achievement can be computed correctly against the goal that was active at the time.

### Risk 5 — Dashboard Date Is Serial Number (LOW)
**Issue:** The Dashboard date (`C2`) extracted as `46141` — this is an Excel date serial number (days since 1900-01-01). Equals 2026-04-29 when converted correctly. The `Meal Data` dates also came through as Python `datetime` objects, so openpyxl handles this.  
**Recommendation:** During CSV export, ensure all dates are converted to ISO 8601 format (`YYYY-MM-DD`). Do not store Excel serials.

### Risk 6 — Duplicate Column Headers (LOW)
**Issue:** Both Food Library and Meal Data have two sets of columns with identical names ("Calories", "Total Fat", etc.) — one set for per-serving values and one for per-gram values (Food Library) or consumed values (Meal Data). Any code that accesses columns by header name will hit the first match and miss the second.  
**Recommendation:** In the CSV architecture, this problem disappears because per-gram rates are not stored. During migration scripts, access columns by index position, not header name, to avoid this bug in the extraction step.

### Risk 7 — Supplement vs Food Conflation (LOW)
**Issue:** Nature Made D3 Gummies and Garden of Life Vitamin C are tracked alongside whole foods with no categorical distinction. Supplement tracking may need different logic (e.g., tracking by pill/capsule count, not grams).  
**Recommendation:** Add `food_category` to `food_library.csv`. Consider a separate `supplement_log.csv` in a v2 if supplement tracking needs diverge from food tracking.

---

## 11. Open Questions / Clarifications Needed

| # | Question | Impact | Priority |
|---|---|---|---|
| 1 | What does the VBA macro in Food Entry do exactly? Does it validate inputs, handle duplicate submissions, or do any transformation before appending? | Blocks building the data entry replacement | HIGH |
| 2 | Are Vitamin A values in IU or mcg RAE — and is this consistent across all foods? | Determines whether micronutrient totals are meaningful | HIGH |
| 3 | Is there a serving unit for each food (oz, piece, etc.) that's tracked separately from grams? The current schema only has `grams_per_serving` with no label. | Affects food entry UX and user mental model | MEDIUM |
| 4 | Are goals intended to be per-user and potentially time-varying? Or always fixed for a single user? | Determines schema complexity for `user_goals.csv` | MEDIUM |
| 5 | Is `Snack` excluded from the calorie goal split intentionally? The Excel formula divides goal by 3 (not 4). | Affects goal calculation logic | MEDIUM |
| 6 | Are there any other sheets, named ranges, or charts in the workbook not captured by the text extraction? (Charts are not extractable via openpyxl in read-only mode.) | May reveal additional KPIs or visualizations | MEDIUM |
| 7 | Is "365 White Quinoa" a Whole Foods 365 brand product? If so, should `brand` be "Whole Foods 365" and `food_name` be "White Quinoa"? | Affects Food Library normalization | LOW |
| 8 | What is the intended multi-user model? Single user forever, or multi-user from day one? | Determines whether `user_id` FK is needed in v1 | LOW |
| 9 | Should the `meal_log.csv` support logging fractional days (e.g., tracking a half-portion of an already-logged entry)? | Affects grams validation rules | LOW |
| 10 | Are there any external data sources (USDA FoodData Central API, Cronometer API) intended for future Food Library enrichment? | Influences `source_url` and `food_id` strategy | LOW |

---

## Appendix A: Nutrient Field Reference (Canonical Names for CSV)

| Category | CSV Field Name | Unit | Excel Per-Serving Col | Excel Per-Gram Col (Library) | Excel Consumed Col (Meal Data) |
|---|---|---|---|---|---|
| Identity | food_name | — | A | — | C |
| Identity | grams_per_serving | g | B | — | — |
| Macro | calories | kcal | C | V | X |
| Macro | total_fat | g | D | W | Y |
| Macro | total_carbs | g | E | X | Z |
| Macro | protein | g | F | Y | AA |
| Fat Detail | saturated_fat | g | G | Z | AB |
| Fat Detail | polyunsaturated_fat | g | H | AA | AC |
| Fat Detail | monounsaturated_fat | g | I | AB | AD |
| Fat Detail | trans_fat | g | J | AC | AE |
| Other Macro | cholesterol | mg | K | AD | AF |
| Other Macro | sodium | mg | L | AE | AG |
| Other Macro | potassium | mg | M | AF | AH |
| Other Macro | dietary_fiber | g | N | AG | AI |
| Other Macro | sugars | g | O | AH | AJ |
| Micro | vitamin_a | mcg RAE | P | AI | AK |
| Micro | vitamin_c | mg | Q | AJ | AL |
| Micro | vitamin_d | mcg | R | AK | AM |
| Micro | calcium | mg | S | AL | AN |
| Micro | iron | mg | T | AM | AO |

---

## Appendix B: Dashboard Formula → SQL Translation

| Dashboard Cell | Excel Formula | SQL Equivalent |
|---|---|---|
| C8 (Calories Actual) | `SUMIFS(MealData.X, Date=C2)` | `SELECT SUM(grams * cal_per_g) FROM meal_log JOIN food_library WHERE log_date = :date` |
| C22 (Fat Actual) | `SUMIFS(MealData.Y, Date=C2)` | `SELECT SUM(grams * fat_per_g) FROM ...` |
| C14 (Breakfast Calories) | `SUMIFS(X, Date=C2, Meal="Breakfast")` | `... WHERE log_date = :date AND meal_type = 'Breakfast'` |
| C28 (Fat Index) | `=C22/C23` | `actual_fat / goal_fat` |
| C49 (Sodium %) | `=C43/C44` | `actual_sodium / goal_sodium` |

---

*End of Architecture & Migration Plan*  
*Document version: 1.0 — based on full static analysis of MyfitnessPal_Clone_-_Final.xlsm*
