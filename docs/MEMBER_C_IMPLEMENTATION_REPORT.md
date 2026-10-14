# DisasterReliefMVP — Member C Implementation & Testing Report

**Project:** Priority-Based Disaster Relief Resource Allocation and Routing Platform for Kerala (`relief-coordination-system`)  
**Team Member:** Person C (Priority Engine, Test Data & Verification Lead)  
**Guide:** Reshma Raj K.S.  
**Catalog Scope:** Full Official Catalog (196 items across 14 groups, 35 emergency-eligible items)  
**Camp Reference:** Kerala State Disaster Management Authority Monsoon Camp Master (`Monsoon-Camp-Details-ALL-Kerala.xlsx`)  
**Tech Stack:** Python 3.13, FastAPI, PostgreSQL + PostGIS (psycopg2), Jinja2 HTML Templates, Vanilla CSS, Unittest  

---

## Table of Contents
1. [Overview & Role Ownership](#1-overview--role-ownership)
2. [Step 1: The Pure SAW Priority Engine & Unit Tests](#2-step-1-the-pure-saw-priority-engine--unit-tests)
3. [Step 2: Complete Official 196-Item Datasets (14 Groups, Hubs, Scarcity Stock, Requests)](#3-step-2-complete-official-196-item-datasets)
4. [Step 3: Database Seed Loader Script (196-Item & 14-Group Schema)](#4-step-3-database-seed-loader-script)
5. [Step 4: Priority Router & Admin Web Dashboard](#5-step-4-priority-router--admin-web-dashboard)
6. [Step 5: End-to-End Integration Flow Test & Evaluator Demo Script](#6-step-5-end-to-end-integration-flow-test--evaluator-demo-script)
7. [Master Testing Cheat Sheet (All Commands)](#7-master-testing-cheat-sheet)
8. [Viva Defense & Evaluator Questions](#8-viva-defense--evaluator-questions)

---

## 1. Overview & Role Ownership

In disaster relief operations, aid cannot be allocated based on informal phone calls or voluntary ad-hoc drops. The system must be **deterministic, transparent, and auditable**.

As **Member C**, you own the **intellectual decision-support core and data foundation**:
- **Priority Calculation (SAW):** Mathematically scoring and ranking camps based on objective stress factors.
- **Data Foundation:** Creating realistic test data for Kerala flood-affected regions utilizing the complete **196-item catalog across 14 distinct groups** and real Kerala geographic locations so all 4 teammates can build and test locally without dependencies.
- **Verification & Demo Ownership:** Verifying the full 9-step system lifecycle and leading project evaluation defense.

### Summary of Files Created by Member C:
```text
relief-coordination-system/
├── engines/
│   └── priority_engine.py         # Module 1: Simple Additive Weighting calculation engine
├── tests/
│   ├── test_priority.py           # Module 1: 7 unit tests for priority engine
│   └── test_flow.py               # Module 5: End-to-end 9-step operational lifecycle test
├── seed/
│   ├── seed_camps.csv             # Module 2: All 6,377 real Kerala relief camps dataset (from Monsoon-Camp-Details-ALL-Kerala.xlsx)
│   ├── seed_hubs.csv              # Module 2: 3 distribution warehouse hubs
│   ├── seed_stock.csv             # Module 2: 222 inventory records with strategic scarcity
│   ├── seed_requests.csv          # Module 2: 20 request lines across 6 camps with escalation flags
│   ├── seed_items.csv             # Module 2: Complete official 196-item catalog (14 groups)
│   └── load_seed.py               # Module 3: Database seed loader & validator
├── routers/
│   └── priority_router.py         # Module 4: FastAPI endpoints (POST /priority/run, GET /priority/latest)
├── templates/
│   └── admin_priority.html        # Module 4: Jinja2 visual priority triage dashboard
└── docs/
    ├── DisasterRelief_Team_Guide.md # Project guide (synchronized with updated standard)
    ├── DEMO_SCRIPT.md             # Module 5: 9-step evaluator presentation script & viva defense
    └── MEMBER_C_IMPLEMENTATION_REPORT.md # This complete technical report
```

---

## 2. Step 1: The Pure SAW Priority Engine & Unit Tests

### Files:
- `engines/priority_engine.py`
- `tests/test_priority.py`

### What Was Performed:
Implemented the mathematical Simple Additive Weighting (SAW) ranking algorithm and its comprehensive unit test suite adhering strictly to **Guide Section 8**.

### How It Works & Implementation Details:
The function `compute_priority(camps, weights, now, time_cap_hours)` is a **pure function** (no database inside). It normalizes 6 criteria into standard $[0, 1]$ floating-point values and computes an aggregate score out of 100:

$$\text{Score} = 100 \times \left( w_{\text{people}} c_{\text{people}} + w_{\text{vuln}} c_{\text{vuln}} + w_{\text{damage}} c_{\text{damage}} + w_{\text{access}} c_{\text{access}} + w_{\text{time}} c_{\text{time}} + w_{\text{esc}} c_{\text{esc}} \right)$$

1. **People ($w = 0.20$):** Normalized against the highest active occupancy in the district: $\frac{\text{occupancy}}{\max(\text{occupancy})}$. If only 1 camp exists, value is $1.0$.
2. **Vulnerable Share ($w = 0.25$):** Sum of Children, Elderly, Pregnant women, and Persons with Disabilities divided by camp occupancy (capped at 1.0). Protected against division-by-zero.
3. **Damage Severity ($w = 0.20$):** Linear mapping from 1–5 scale: $\frac{\text{damage\_level} - 1}{4}$. (Level 1 $\to 0.0$; Level 5 $\to 1.0$).
4. **Access Difficulty ($w = 0.15$):** Linear mapping from 1–5 scale: $\frac{\text{access\_difficulty} - 1}{4}$. (Level 5 isolated by floodwaters $\to 1.0$).
5. **Time Since Last Supply ($w = 0.10$):** $\frac{\min(\text{hours elapsed}, 72)}{72}$. Uses `created_at` if `last_supply_at` is empty.
6. **Escalation ($w = 0.10$):** Binary $1.0$ if the camp officer flagged an active urgent request, else $0.0$.

#### Tie-Breaking Logic (Guide Section 8.5):
When two camps obtain the identical score:
1. The camp with the **older open request timestamp** (`MIN(r.created_at)`) ranks higher (FIFO fairness).
2. If still tied, the lower `camp_id` ranks higher.

### Benchmark Verification (Guide Section 8.4):
The engine was tested against the official benchmark example in Section 8.4:
- Camp X: Occupancy 400 (max 500), Vulnerable 180 (45%), Damage 4, Access 5, Supplied 48h ago, Escalated = True.
- **Result:** Benchmark score $\mathbf{73.92}$ exact match verified!

### Tools & Standards Used:
- Python standard library: `datetime`, `timedelta`, `typing`, `unittest`.
- Numerical safety: Floating point tolerance check `abs(sum(weights) - 1.0) < 1e-5` preventing configuration bugs.

### How to Run & Test Step 1:
```bash
# Run the visual ASCII terminal ranking demo:
python engines/priority_engine.py

# Run all 7 priority unit tests:
python -m unittest tests/test_priority.py -v
```

---

## 3. Step 2: Complete Official 196-Item Datasets

### Files:
- `seed/seed_items.csv` (196 items, 14 groups)
- `seed/seed_camps.csv` (6,377 camps across all 14 Kerala districts from `Monsoon-Camp-Details-ALL-Kerala.xlsx`)
- `seed/seed_hubs.csv` (3 hubs)
- `seed/seed_stock.csv` (222 inventory lines)
- `seed/seed_requests.csv` (20 request lines across benchmark test camps)

### What Was Performed:
Integrated the **complete, full-scale 196-item catalog** provided in the official project specification across **14 distinct groups** (6 core groups and 8 extended groups), alongside 35 acute emergency-eligible items.

#### Complete Group Structure (196 Items):
- **Core Groups (116 items):**
  - `FW` Food & Water (24 items): Bottled/tanker water, Rice (`FW02`), Pulses, Wheat, Infant formula (`FW19`), Baby cereal (`FW20`), Milk powder (`FW21`).
  - `CB` Clothing & Bedding (20 items): Men/Women/Children sets, Bed sheets (`CB10`), Blankets (`CB11`), Mats (`CB12`).
  - `SH` Sanitation & Hygiene (26 items): Soaps, Sanitary napkins (`SH10`), Baby diapers (`SH11`), Bleaching powder (`SH16`), Mobile toilets (`SH25`).
  - `MF` Medical / First Aid (24 items): First aid (`MF01`), ORS (`MF02`), Antiseptic, Fever/pain medicines (`MF12`), Antibiotics (`MF14`), Oxygen cylinders (`MF22`), Antivenom (`MF24`).
  - `KU` Kitchen & Utensils (16 items): Large cooking pots, Pressure cookers, Plates, Stoves, Gas cylinders.
  - `SU` Shelter & Utility (20 items): Tarpaulin, Tents, Ropes, Torches, Generators, Sandbags.
- **Extended Groups (80 items):**
  - `SG` Special Groups (19 items): Feeding bottles (`SG01`), Wheelchairs, Crutches, Special beds (`SG15`), Pregnant women nutrition (`SG17`).
  - `CA` Communication & Admin (12 items): Walkie-talkies, ID wristbands, Delivery slips/QR cards.
  - `SS` Safety & Security (10 items): Lifejackets (`SS02`), Life buoys (`SS03`), Rescue boats (`SS04`), Rescue ropes (`SS05`).
  - `WI` Waste & WASH Infrastructure (6 items): Water tankers, Filters, Chlorine.
  - `PR` Psychosocial & Recreation (6 items): Counselling support, Games, Play mats.
  - `LV` Livestock & Pets (3 items): Fodder, Veterinary supplies, Animal shelter.
  - `RC` Recovery & Cleaning (5 items): Gum boots, Water pumps, Re-entry kits.
  - `TL` Transport & Logistics (5 items): Vehicles, Fuel, Transport boats.

#### Emergency Triage Eligibility (35 Items):
- All 24 Medical items (`MF01`–`MF24`).
- 4 Infant Feeding items (`FW19`, `FW20`, `FW21`, `SG01`).
- 3 Critical Patient / Maternal items (`SG15`, `SG17`, `SG19`).
- 4 Water Rescue & Safety items (`SS02`, `SS03`, `SS04`, `SS05`).

#### Strategic Inventory Scarcity (`seed_stock.csv` — 222 rows):
- Hub 1 (Alappuzha): 100 kg Rice (`FW02`), 50 Blankets (`CB11`), 500 L Water (`FW01`).
- Hub 2 (Kottayam): 30 kg Rice (`FW02` - scarce), 0 Blankets (`CB11` - scarce), 300 L Water.
- Hub 3 (Pathanamthitta): 100 kg Rice (`FW02`), 25 Blankets (`CB11`), 350 L Water.

### How to Run & Test Step 2:
```bash
# Verify summary of all seed datasets:
python -c "import csv, glob; [print(f, len(list(csv.DictReader(open(f, encoding='utf-8')))), 'rows') for f in sorted(glob.glob('seed/*.csv'))]"
```

---

## 4. Step 3: Database Seed Loader Script

### File:
- `seed/load_seed.py`

### What Was Performed:
Updated the database seed loader to process the full 196-item catalog with all 10 schema fields (`item_code, name, group_code, group_kind, unit, item_type, perishable, requires_approval, emergency_eligible, notes, active`).

### How It Works & Implementation Details:
1. **Foreign-Key Sequence Order:**
   $$\text{Items (196)} \longrightarrow \text{Camps (6,377)} \longrightarrow \text{Hubs (3)} \longrightarrow \text{Users (4)} \longrightarrow \text{Stock (222)} \longrightarrow \text{Requests (20 lines)}$$
2. **Boolean and Qualification Normalization:** Normalizes `emergency_eligible` strings ('yes'/'no') to PostgreSQL booleans and stores qualifiers like `(expiry)`, `(cold chain)`, and `TBC - confirm with DDMA` in `notes`.
3. **Sequence Synchronization:** Re-synchronizes serial counters (`camps_camp_id_seq`, `hubs_hub_id_seq`, `requests_request_id_seq`).
4. **Validation Mode:** Validates that every item referenced in stock and requests exists in the 196-item catalog.

### How to Run & Test Step 3:
```bash
# Validate all 196 items, stock, and requests:
python seed/load_seed.py --validate

# Seed database when PostgreSQL is running:
python seed/load_seed.py

# Load only the 196-item catalog (for Member B):
python seed/load_seed.py --only items
```

---

## 5. Step 4: Priority Router & Admin Web Dashboard

### Files:
- `routers/priority_router.py`
- `templates/admin_priority.html`

### What Was Performed:
Implemented the FastAPI API endpoints and the Jinja2 HTML web dashboard for District Control Room administrators to calculate, inspect, and audit camp priority rankings.

### Endpoints (Guide Section 10):
- `POST /priority/run`: Aggregates active camps and open requests via SQL, runs `compute_priority()`, archives weights in `priority_runs.weights_json`, and saves scores in `priority_scores` inside a single ACID transaction.
- `GET /priority/latest`: Retrieves newest priority run and renders the visual dashboard with 6 color-coded criteria progress bars and **🔄 Recalculate Priority** button.

### How to Run & Test Step 4:
```bash
# Verify router endpoints:
python -c "from routers.priority_router import router; [print(r.methods, r.path) for r in router.routes]"
```

---

## 6. Step 5: End-to-End Integration Flow Test & Evaluator Demo Script

### Files:
- `tests/test_flow.py`
- `docs/DEMO_SCRIPT.md`

### What Was Performed:
Updated the integration test suite to verify the full 9-step demo flow (Guide Section 15.4) using the official catalog codes (`FW02` Rice, `CB11` Blankets).

### Verification Sequence:
1. Data seeding check: 196 items, 6 camps, 3 hubs.
2. Donation intake: +100 Rice (`FW02`), +50 Blankets (`CB11`) added to Hub 1 inventory.
3. Urgent request: Camp 1 asks for 60 Rice, 30 Blankets (Escalated = True).
4. SAW Ranking: Kuttanad (#1) and Chengannur (#2) prioritized at the top.
5. Stock allocation: Camp 1 request transitions to `fulfilled`.
6. Dispatch & Dynamic Time Decay: Camp 1 `last_supply_at` updates to dispatch time $\to$ Priority recalculation causes time component to drop to $0.00$, preventing hoarding.

### How to Run & Test Step 5:
```bash
# Run flow test:
python -m unittest tests/test_flow.py -v

# Run all 9 project tests:
python -m unittest discover tests -v
```

---

## 7. Master Testing Cheat Sheet

| What You Want to Test | Terminal Command | What You See on Screen |
|---|---|---|
| **Live Visual Priority Ranking Demo** | `python engines/priority_engine.py` | Full ASCII table showing camps, scores, ranks, and 6 criteria breakdown percentages. |
| **Priority Engine Unit Tests** | `python -m unittest tests/test_priority.py -v` | 7 green checks (`ok`) verifying benchmark score 73.92, zero occupancy, time cap, and tie-breaking. |
| **Validate All 196 Items & Datasets** | `python seed/load_seed.py --validate` | Report confirming **196 items**, 6 camps, 3 hubs, 222 stock lines, and 20 request lines are valid. |
| **Verify Priority API Endpoints** | `python -c "from routers.priority_router import router; [print(r.methods, r.path) for r in router.routes]"` | Prints `POST /priority/run`, `GET /priority/latest`, `GET /priority`. |
| **Full 9-Step Operational Lifecycle Test** | `python -m unittest tests/test_flow.py -v` | Verifies full chain: Donation $\to$ Intake $\to$ Request $\to$ SAW Priority $\to$ Allocation $\to$ Dispatch $\to$ Decay. |
| **Run All 9 Tests Across Project** | `python -m unittest discover tests -v` | `Ran 9 tests in 0.003s - OK` |

---

## 8. Viva Defense & Evaluator Questions

Use these exact answers when professors or evaluators question your design choices:

### Q1: Why did you use Simple Additive Weighting (SAW) instead of Machine Learning or Neural Networks?
> **Answer:** *"In disaster relief, allocation decisions must be **100% deterministic, explainable, and transparent** to government authorities and the public. Neural networks and deep learning models act as 'black boxes' that cannot explain why one camp received food while another did not. SAW uses fixed, transparent weights that produce the exact same score for the same inputs every time. Furthermore, every calculation archives its exact weights in `priority_runs.weights_json` for legal auditability."*

### Q2: What is Mandatory Routing and why does your platform prevent donors from choosing a camp?
> **Answer:** *"During the 2018 Kerala floods, uncoordinated public donations caused severe supply imbalances: accessible camps near highways received mountains of excess bread and water, while marooned camps in Kuttanad received nothing. Mandatory routing prevents donors from selecting individual camps. All donations are pooled into designated taluk/district hubs, where stock is methodically distributed based on mathematical need."*

### Q3: How is the 196-item catalog structured?
> **Answer:** *"The catalog contains 196 items organized into 14 functional groups: 6 Core groups (Food & Water FW, Clothing & Bedding CB, Sanitation SH, Medical MF, Kitchen KU, Shelter SU) covering 116 baseline goods, and 8 Extended groups (Special Groups SG, Admin CA, Security SS, WASH WI, Recreation PR, Livestock LV, Recovery RC, Logistics TL) covering 80 items. Additionally, 35 critical items are flagged as emergency-eligible for acute life-saving triage."*

### Q4: Why is the time factor capped at 72 hours?
> **Answer:** *"Without a time cap, an unsupplied camp after two weeks would accumulate an infinitely large score and unfairly dominate all future allocations. Sphere standards and emergency relief protocols consider 72 hours the critical window for initial life-saving supplies, so elapsed waiting time is normalized against a 72-hour ceiling."*
