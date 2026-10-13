# DisasterReliefMVP — Team Guide (The Standard Document)

**Project (working title):** Priority-Based Disaster Relief Resource Allocation and Routing Platform for Kerala
**Team:** Group 07 · Guide: Reshma Raj K.S.
**Version:** 1.0 · Written for Week 1 (first 50% of the build)

> **If you read only one thing:** Everyone reads Sections 0, 1 and 2. After that, read your own member section in Section 11, and use Section 12 (the Antigravity rules) every single time you open Antigravity.

---

## Table of contents

0. How to use this guide
1. The project in plain words
2. Team and ownership
3. The 4-part roadmap (25 / 50 / 75 / 100)
4. One-time setup on your laptop
5. Folder structure and file owners
6. The database (all tables)
7. The data we need (catalog, camps, hubs, norms)
8. The priority engine (SAW) — exact rules
9. The allocation engine — exact rules
10. API list and permissions
11. Member task sheets (A, B, C, D)
12. Antigravity rules and ready-made prompts
13. Git and GitHub cheat sheet
14. How we follow up (daily routine, tracker, handoffs)
15. Integration plan (how the pieces join)
16. Week 1 calendar
17. When something breaks (troubleshooting)
18. Open questions for DDMA
19. How to explain the project to evaluators
20. Glossary
21. After Week 1 (Parts 3 and 4)
22. Change log

---

## 0. How to use this guide

You do not need to be a programmer to follow this guide. Antigravity (the AI coding tool) writes most of the code. **Your job is to give it clear instructions, check that what it produced actually works, and keep to the shared rules so that four people's work fits together.**

### The 8 golden rules

1. **Work only in your own files.** Section 5 says who owns what. If you need a change in someone else's file, ask them in the group chat.
2. **Never change a table, a function name or an API name on your own.** These are "contracts" (Sections 6, 8, 9, 10). Everyone depends on them. Ask first, then record it in the Change Log (Section 22).
3. **Small steps.** Ask Antigravity for one small thing at a time, run it, check it, then ask for the next thing.
4. **Test before you push.** Code that has not been run is not finished.
5. **Commit and push at least once a day**, even if the work is not perfect (on your own branch — Section 13).
6. **Use only free tools.** No paid services, no paid API keys.
7. **Never invent facts or data and pretend they are real.** All sample data is *fake test data* and must be labelled as such. If a number is not confirmed (for example the final weights), the guide says "placeholder".
8. **If you are stuck for more than 30 minutes, say so in the group chat.** Getting stuck is normal. Staying silent is the only real mistake.

### How to read the boxes

- ✅ **Check:** something you must verify before moving on.
- ⚠️ **Careful:** a common mistake.
- 📌 **Contract:** a shared rule that must not be changed alone.

---

## 1. The project in plain words

### 1.1 The problem
During floods in Kerala (for example 2018), relief camps ask for help in informal ways: phone calls, messages, people dropping things off. The result: some camps get too much of one thing (duplicate donations), other camps get nothing, and nobody has one clear picture of who needs what.

### 1.2 Our solution
A **government-operated web platform** where:

- **Camp officers** enter what their camp needs.
- **Donors** offer items, but they **cannot pick a camp**. Their donation is **routed** to a **hub** (a storage and distribution point). This is called **mandatory routing** and it is the main difference from existing NGO donation websites, where listings are voluntary and unverified.
- The system **ranks camps by priority** using a fixed, transparent scoring method (SAW).
- The system **allocates available stock** from hubs to camps, highest priority first.
- Everything is **recorded** so that authorities can see what happened.

### 1.3 Who uses it (roles)

| Role | Who they are | What they do in the system |
|---|---|---|
| `camp_officer` | Government officer in charge of one camp | Updates camp details, submits item requests, sees what is allocated |
| `hub_coordinator` | Person running one hub | Sees stock, receives donations (adds stock), marks allocations as dispatched |
| `admin` | DDMA / district control room staff | Creates users and camps, runs priority ranking and allocation, sees everything |
| `donor` | Individual / NGO / supplier | Offers items from the accepted-items list |

### 1.4 Important ideas to remember (evaluators will ask)

- **Decision-support, not decision-maker.** The system *helps* officers decide. Humans stay in charge.
- **Mandatory routing.** All donations go through the system to a hub. Donors do not choose a camp.
- **The priority ranking is deterministic.** It is a calculation from entered data (SAW). It is **not** a prediction. Same inputs always give the same ranking.
- **Forecasting comes later** (Part 3) and will give **ranges**, not guarantees.
- **No sentiment analysis.** We decided against scoring the free-text comment with NLP. Urgency comes from a simple **escalate button** plus a plain comment box that is **not scored**.
- **Free tools only.**

### 1.5 What we build in Week 1 (the first 50%)

| Built this week | NOT built this week (later) |
|---|---|
| Database, login and roles | Demand forecasting (QRF) |
| Item catalog | Anomaly-aware triage |
| Camp registration and updates | Hub-to-hub reallocation (PuLP) |
| Request entry (with escalate button) | QR delivery confirmation (jsQR) |
| SAW priority ranking | Monitoring dashboards (charts) |
| Donor module (donation → hub) | Offline resilience |
| Hubs and stock | |
| Allocation (stock → camps in priority order) | |

**Done = the demo flow in Section 15.4 works from start to end.**

---

## 2. Team and ownership

Write the real names next to each letter on Day 1.

| Letter | Name | Area | Owns (short) |
|---|---|---|---|
| **A** | __________ | **Foundation:** database, login, roles, donors | `schema.sql`, `database.py`, `config.py`, `deps.py`, `main.py`, auth and donor pages |
| **B** | __________ | **Camps, catalog and requests** | item catalog, camp pages, request form |
| **C** | __________ | **Priority engine, test data and testing** | SAW engine, ranking page, seed data, end-to-end test |
| **D** | __________ | **Hubs, stock and allocation** | hubs, stock, receiving donations, allocation engine |

**Who depends on whom**

- Everybody depends on **A** (database and login). So A's first job on Day 1 is to push the database design.
- **C** depends on **B's** camp and request data (but works with seed data until B is ready).
- **D** depends on **C's** ranking (but starts with a fake ranking) and on **A's** donations.

📌 **Contract — nobody is blocked:** A gives a *fake login* switch (Section 11, A2) and C gives *seed data* (C1) on Day 1–2, so no one has to wait for another person's finished work.

---

## 3. The 4-part roadmap (25 / 50 / 75 / 100)

| Part | Progress | What is done | Time |
|---|---|---|---|
| **1** | 25% | Foundation: database, login/roles, catalog, camps, requests, **priority ranking** | Week 1 (first half) |
| **2** | 50% | Supply side: donors, hubs, stock, **allocation**, simple hub assignment | Week 1 (second half) |
| **3** | 75% | Intelligence: demand forecasting (QRF), anomaly-aware triage, hub-to-hub reallocation (PuLP) | Later |
| **4** | 100% | QR delivery confirmation, dashboards, offline resilience, testing, documentation | Later |

This guide covers **Parts 1 and 2** in detail. Section 21 gives a short outline of Parts 3 and 4.

---

## 4. One-time setup on your laptop

Everyone does this on Day 1, **before** starting any task. Allow 1–2 hours. These steps are for Windows.

### 4.1 Install these (all free)

| Tool | Where | Notes |
|---|---|---|
| **Python 3** | python.org | During install, **tick "Add Python to PATH"** |
| **Git** | git-scm.com | Accept the default options |
| **PostgreSQL** | postgresql.org (Windows installer) | **Write down the password** you set for the `postgres` user |
| **PostGIS** | From the **Stack Builder** program that comes with PostgreSQL → *Spatial Extensions* | Needed for distance calculations |
| **pgAdmin** | Comes with PostgreSQL | Used to look at the database |
| **VS Code** (optional) | code.visualstudio.com | A simple editor to read files |
| **Antigravity** | As your team already uses | Primary coding agent. Claude Code is the backup if Antigravity is unavailable. |

⚠️ **Careful:** Installer screens change over time. If a step does not match what you see, take a screenshot and ask in the group chat.

### 4.2 Get the code and prepare it

Open **Command Prompt** (or the terminal in VS Code) and run these one at a time:

```
git clone <PASTE-THE-REPO-LINK-HERE>
cd DisasterReliefMVP
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
```

(`venv` is a private box for this project's Python libraries. You must run `venv\Scripts\activate` **every time** you open a new terminal for the project. You will see `(venv)` at the start of the line when it is active.)

Now open the new `.env` file and write your own PostgreSQL password in `DATABASE_URL`.

### 4.3 Create the database

1. Open **pgAdmin** → right-click **Databases** → **Create → Database** → name it `relief_db`.
2. Click `relief_db` → **Tools → Query Tool** → run:
   ```sql
   CREATE EXTENSION IF NOT EXISTS postgis;
   SELECT PostGIS_Version();
   ```
3. ✅ **Check:** the second line shows a version number. If it shows an error, PostGIS is not installed — go back to Stack Builder.
4. Create the tables: in Query Tool, open `schema.sql` (File → Open) and run it. (Or run `python reset_db.py` once A has pushed it — it does the same thing.)
5. Fill the sample data: `python seed/load_seed.py` (available after C1 is pushed).

### 4.4 Run the app

```
uvicorn main:app --reload
```

Open a browser at `http://127.0.0.1:8000`. Open `http://127.0.0.1:8000/docs` to see an automatic list of all API endpoints (FastAPI creates this page by itself). Stop the app with **Ctrl + C**.

✅ **Check:** `http://127.0.0.1:8000/health` shows `{"status":"ok"}`.

### 4.5 Why everyone runs their own local database

You are in four different places. Each person runs the **same** `schema.sql` and the **same** seed script, so everyone has identical test data on their own laptop. Nobody needs to share a live database in Week 1. (A shared online database can be considered later; free tiers change, so check current limits before relying on one.)

---

## 5. Folder structure and file owners

📌 **Contract — do not move or rename files without asking.**

```
DisasterReliefMVP/
├── main.py                  [A]  starts the app; adds one line per router
├── config.py                [A]  settings + SAW weights
├── database.py              [A]  connects to PostgreSQL
├── deps.py                  [A]  login helpers: get_current_user, require_role
├── schema.sql               [A]  ALL table definitions
├── reset_db.py              [A]  re-creates the tables from schema.sql
├── requirements.txt         [A]  list of Python libraries (everyone may add via A)
├── .env.example             [A]  template for settings (real .env is NEVER pushed)
│
├── routers/
│   ├── auth_router.py       [A]  login, logout, register donor, admin creates users
│   ├── donors_router.py     [A]  donations (offer, list, assign hub)
│   ├── items_router.py      [B]  item catalog
│   ├── camps_router.py      [B]  camps
│   ├── requests_router.py   [B]  requests
│   ├── priority_router.py   [C]  run + view ranking
│   ├── hubs_router.py       [D]  hubs
│   ├── stock_router.py      [D]  stock, receive donations, adjust
│   └── allocation_router.py [D]  run allocation, view, mark dispatched
│
├── engines/
│   ├── priority_engine.py   [C]  SAW calculation (pure function)
│   └── allocation_engine.py [D]  allocation logic
│
├── templates/               (web pages)
│   ├── base.html            [A]  common layout + menu
│   ├── login.html, donor_*.html            [A]
│   ├── items.html, camp_*.html, request_*.html   [B]
│   ├── admin_priority.html  [C]
│   └── hub_*.html, allocation_*.html       [D]
│
├── static/style.css         [A]  one shared simple stylesheet
│
├── seed/
│   ├── seed_items.csv       [B]
│   ├── seed_camps.csv, seed_hubs.csv, seed_stock.csv, seed_requests.csv  [C]
│   ├── seed_users.py        [A]
│   └── load_seed.py         [C]  loads everything in the right order
│
├── tests/
│   ├── test_priority.py     [C]
│   ├── test_allocation.py   [D]
│   ├── test_auth.py         [A]
│   ├── test_requests.py     [B]
│   └── test_flow.py         [C]  end-to-end test
│
└── docs/
    └── DisasterRelief_Team_Guide.md   (this file)
```

⚠️ **Careful:** `main.py` is touched by many people (each router adds one line). **Only A edits `main.py`.** Others tell A which line to add, or A adds all router lines on Day 1 in advance (recommended — see A1).

**The existing prototype** (files like `priority_engine.py`, `database.py`, `main.py`, `templates/index.html`, `test_system.py`) is **reference only**. You may read it for ideas, but do not trust it blindly. Always check it against this guide.


---

## 6. The database (all tables)

📌 **Contract.** Owner: **A**. Nobody else edits `schema.sql`. If you need a new column, ask A, and write it in the Change Log.

### 6.1 Plain-words picture

- **camps** = places where people stay
- **hubs** = storage places that send supplies out
- **items** = the catalog of things that can be requested or donated
- **requests / request_items** = what a camp asks for (one request has many item lines)
- **stock** = how many of each item each hub has right now
- **donations / donation_items** = what donors offer
- **priority_runs / priority_scores** = each time the ranking is calculated, and the score of every camp
- **allocation_runs / allocations** = each time stock is allocated, and who got what from which hub
- **stock_movements** = a logbook of every stock change (who, when, why)
- **users** = people who can log in

### 6.2 The SQL (A pastes this into `schema.sql`)

```sql
-- schema.sql  (Owner: A)  Running this file DELETES and re-creates everything.
CREATE EXTENSION IF NOT EXISTS postgis;

DROP TABLE IF EXISTS stock_movements, allocations, allocation_runs,
  priority_scores, priority_runs, donation_items, donations, stock,
  request_items, requests, items, users, hubs, camps CASCADE;

CREATE TABLE camps (
  camp_id            SERIAL PRIMARY KEY,
  name               TEXT NOT NULL,
  district           TEXT NOT NULL,
  address            TEXT,
  latitude           NUMERIC(9,6) NOT NULL,
  longitude          NUMERIC(9,6) NOT NULL,
  capacity           INT CHECK (capacity >= 0),
  occupancy          INT NOT NULL DEFAULT 0 CHECK (occupancy >= 0),
  children_count     INT NOT NULL DEFAULT 0 CHECK (children_count >= 0),
  elderly_count      INT NOT NULL DEFAULT 0 CHECK (elderly_count >= 0),
  pregnant_count     INT NOT NULL DEFAULT 0 CHECK (pregnant_count >= 0),
  disabled_count     INT NOT NULL DEFAULT 0 CHECK (disabled_count >= 0),
  damage_level       INT NOT NULL DEFAULT 1 CHECK (damage_level BETWEEN 1 AND 5),
  access_difficulty  INT NOT NULL DEFAULT 1 CHECK (access_difficulty BETWEEN 1 AND 5),
  status             TEXT NOT NULL DEFAULT 'active' CHECK (status IN ('active','closed')),
  last_supply_at     TIMESTAMPTZ,
  created_at         TIMESTAMPTZ NOT NULL DEFAULT now(),
  updated_at         TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE hubs (
  hub_id      SERIAL PRIMARY KEY,
  name        TEXT NOT NULL,
  district    TEXT NOT NULL,
  address     TEXT,
  latitude    NUMERIC(9,6) NOT NULL,
  longitude   NUMERIC(9,6) NOT NULL,
  active      BOOLEAN NOT NULL DEFAULT TRUE,
  created_at  TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE users (
  user_id        SERIAL PRIMARY KEY,
  username       TEXT NOT NULL UNIQUE,
  full_name      TEXT NOT NULL,
  password_hash  TEXT NOT NULL,
  role           TEXT NOT NULL CHECK (role IN ('admin','camp_officer','hub_coordinator','donor')),
  camp_id        INT REFERENCES camps(camp_id),
  hub_id         INT REFERENCES hubs(hub_id),
  district       TEXT,                 -- used for donors (their district)
  active         BOOLEAN NOT NULL DEFAULT TRUE,
  created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE items (
  item_id            SERIAL PRIMARY KEY,
  item_code          TEXT NOT NULL UNIQUE,
  name               TEXT NOT NULL,
  category           TEXT NOT NULL CHECK (category IN ('FW','CB','SH','MF','KU','SU','SG')),
  unit               TEXT NOT NULL,
  perishable         BOOLEAN NOT NULL DEFAULT FALSE,
  requires_approval  BOOLEAN NOT NULL DEFAULT FALSE,
  emergency_eligible BOOLEAN,          -- NULL = to be confirmed with DDMA
  acceptance_rule    TEXT,             -- e.g. 'No bread'
  norm_note          TEXT,             -- only when we have a cited source
  active             BOOLEAN NOT NULL DEFAULT TRUE
);

CREATE TABLE requests (
  request_id    SERIAL PRIMARY KEY,
  camp_id       INT NOT NULL REFERENCES camps(camp_id),
  submitted_by  INT NOT NULL REFERENCES users(user_id),
  status        TEXT NOT NULL DEFAULT 'pending'
                CHECK (status IN ('pending','partially_allocated','fulfilled','cancelled')),
  escalated     BOOLEAN NOT NULL DEFAULT FALSE,
  comment       TEXT,                  -- plain text, NOT scored
  created_at    TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE request_items (
  request_item_id  SERIAL PRIMARY KEY,
  request_id       INT NOT NULL REFERENCES requests(request_id) ON DELETE CASCADE,
  item_id          INT NOT NULL REFERENCES items(item_id),
  qty_requested    INT NOT NULL CHECK (qty_requested > 0),
  qty_allocated    INT NOT NULL DEFAULT 0 CHECK (qty_allocated >= 0),
  UNIQUE (request_id, item_id)
);

CREATE TABLE stock (
  hub_id         INT NOT NULL REFERENCES hubs(hub_id),
  item_id        INT NOT NULL REFERENCES items(item_id),
  qty_available  INT NOT NULL DEFAULT 0 CHECK (qty_available >= 0),
  updated_at     TIMESTAMPTZ NOT NULL DEFAULT now(),
  PRIMARY KEY (hub_id, item_id)
);

CREATE TABLE donations (
  donation_id      SERIAL PRIMARY KEY,
  donor_id         INT NOT NULL REFERENCES users(user_id),
  status           TEXT NOT NULL DEFAULT 'offered'
                   CHECK (status IN ('offered','hub_assigned','received','rejected')),
  assigned_hub_id  INT REFERENCES hubs(hub_id),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now(),
  received_at      TIMESTAMPTZ
);

CREATE TABLE donation_items (
  donation_item_id  SERIAL PRIMARY KEY,
  donation_id       INT NOT NULL REFERENCES donations(donation_id) ON DELETE CASCADE,
  item_id           INT NOT NULL REFERENCES items(item_id),
  qty               INT NOT NULL CHECK (qty > 0)
);

CREATE TABLE priority_runs (
  run_id        SERIAL PRIMARY KEY,
  run_at        TIMESTAMPTZ NOT NULL DEFAULT now(),
  run_by        INT REFERENCES users(user_id),
  weights_json  JSONB NOT NULL          -- the exact weights used (so results can be explained later)
);

CREATE TABLE priority_scores (
  score_id   SERIAL PRIMARY KEY,
  run_id     INT NOT NULL REFERENCES priority_runs(run_id) ON DELETE CASCADE,
  camp_id    INT NOT NULL REFERENCES camps(camp_id),
  score      NUMERIC(6,2) NOT NULL,
  rank       INT NOT NULL,
  breakdown  JSONB NOT NULL
);

CREATE TABLE allocation_runs (
  run_id           SERIAL PRIMARY KEY,
  priority_run_id  INT REFERENCES priority_runs(run_id),
  run_at           TIMESTAMPTZ NOT NULL DEFAULT now(),
  run_by           INT REFERENCES users(user_id),
  note             TEXT
);

CREATE TABLE allocations (
  allocation_id    SERIAL PRIMARY KEY,
  run_id           INT NOT NULL REFERENCES allocation_runs(run_id) ON DELETE CASCADE,
  camp_id          INT NOT NULL REFERENCES camps(camp_id),
  hub_id           INT NOT NULL REFERENCES hubs(hub_id),
  item_id          INT NOT NULL REFERENCES items(item_id),
  request_item_id  INT REFERENCES request_items(request_item_id),
  qty              INT NOT NULL CHECK (qty > 0),
  status           TEXT NOT NULL DEFAULT 'planned'
                   CHECK (status IN ('planned','dispatched','delivered','cancelled')),
  created_at       TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE TABLE stock_movements (
  movement_id  SERIAL PRIMARY KEY,
  hub_id       INT NOT NULL REFERENCES hubs(hub_id),
  item_id      INT NOT NULL REFERENCES items(item_id),
  change_qty   INT NOT NULL,            -- + adds stock, - removes stock
  reason       TEXT NOT NULL CHECK (reason IN ('donation_received','allocation','manual_adjustment')),
  ref_id       INT,                     -- donation_id or allocation_id
  created_by   INT REFERENCES users(user_id),
  created_at   TIMESTAMPTZ NOT NULL DEFAULT now()
);

CREATE INDEX idx_requests_camp   ON requests(camp_id, status);
CREATE INDEX idx_alloc_camp      ON allocations(camp_id);
CREATE INDEX idx_alloc_hub       ON allocations(hub_id);
CREATE INDEX idx_scores_run      ON priority_scores(run_id, rank);
```

### 6.3 Status words (use exactly these)

| Thing | Allowed values |
|---|---|
| Request status | `pending`, `partially_allocated`, `fulfilled`, `cancelled` |
| Donation status | `offered`, `hub_assigned`, `received`, `rejected` |
| Allocation status | `planned`, `dispatched`, `delivered` (Part 4), `cancelled` |
| Roles | `admin`, `camp_officer`, `hub_coordinator`, `donor` |
| Item categories | `FW` Food & Water · `CB` Clothing & Bedding · `SH` Sanitation & Hygiene · `MF` Medical/First Aid · `KU` Kitchen & Utensils · `SU` Shelter & Utility · `SG` School Kit / special groups |

### 6.4 Stock rules (very important)

1. **Stock only changes through `stock_movements`.** Every change writes a movement row (who, why, how much) *and* updates the `stock` row, **inside one transaction** (all-or-nothing). This is the ACID rule our report relies on.
2. Stock can **never go below zero** (the database refuses it).
3. Receiving a donation **adds** stock (`donation_received`).
4. Running an allocation **removes** stock straight away (`allocation`) — the stock is "reserved" for the camp.
5. Undoing allocations is **not** part of Week 1.

---

## 7. The data we need

### 7.1 Overview

| Data | File | Owner | Real or fake? |
|---|---|---|---|
| Item catalog | `seed/seed_items.csv` | B | Real list from the team's accepted-items sheet (Section 7.2) |
| Camps | `seed/seed_camps.csv` | C | **Fake test data** |
| Hubs | `seed/seed_hubs.csv` | C | **Fake test data** |
| Starting stock | `seed/seed_stock.csv` | C | **Fake test data** |
| Sample requests | `seed/seed_requests.csv` | C | **Fake test data** |
| Users (one per role) | `seed/seed_users.py` | A | **Fake test accounts**; passwords are for testing only |

⚠️ **Careful:** Never put real people's names, phone numbers or addresses in the seed data. Camp and hub names are made up.

### 7.2 Item catalog (from the accepted-items list)

This comes from the team's accepted-items sheet (screenshots). The grouping into categories is **our** proposal. Items marked ⓘ need a decision.

**Rules written on the sheet (put them in `acceptance_rule`):**
- Rusk: **no bread**
- Biscuits: **no cream biscuits**
- Water: **only 20-litre cans**

**Seed items (`seed_items.csv` columns:** `item_code,name,category,unit,perishable,requires_approval,emergency_eligible,acceptance_rule,norm_note`**)**

| Code | Name | Cat | Unit | Rule / note |
|---|---|---|---|---|
| FW01 | Rice | FW | kg | |
| FW02 | Sugar | FW | kg | |
| FW03 | Salt | FW | kg | |
| FW04 | Vegetables | FW | kg | perishable |
| FW05 | Food grains (other than rice) ⓘ | FW | kg | "Food grains" is vague on the sheet; ask DDMA to name them |
| FW06 | Cooking oil | FW | litre | |
| FW07 | Rusk | FW | packet | **No bread** |
| FW08 | Biscuits | FW | packet | **No cream biscuits** |
| FW09 | Drinking water | FW | can (20 L) | **Only 20-litre cans** |
| FW10 | Tea / coffee powder | FW | packet | |
| FW11 | Pulses | FW | kg | |
| CB01 | Bed sheets | CB | piece | listed twice on the sheet; one item |
| CB02 | Bathing towel (thorthu) | CB | piece | |
| CB03 | Sleeping mats | CB | piece | |
| CB04 | Blankets | CB | piece | |
| CB05 | Pillow | CB | piece | |
| CB06 | Adult clothes (maxi, mundu, pants, shirt, inner garments) | CB | set | ⓘ maybe split into separate items later |
| CB07 | Children's clothes | CB | set | |
| CB08 | Kids' clothes ⓘ | CB | set | appears separately on the sheet; may be the same as CB07 or for infants. Ask DDMA. |
| SG01 | School bag | SG | piece | School kit |
| SG02 | Notebooks | SG | piece | School kit |
| SG03 | Pencil box | SG | piece | School kit |
| SG04 | Pens | SG | piece | School kit |
| SH01 | Bleaching powder | SH | kg | Cleaning |
| SH02 | Mop | SH | piece | Cleaning |
| SH03 | Phenol / Dettol | SH | bottle | Cleaning |
| SH04 | Brush | SH | piece | Cleaning |
| SH05 | Cleaning liquids | SH | bottle | Cleaning |
| SH06 | Baby diapers | SH | packet | |
| SH07 | Adult diapers | SH | packet | |
| SH08 | Sanitary napkins | SH | packet | |
| SH09 | Toothpaste | SH | tube | |
| SH10 | Tooth brushes | SH | piece | |
| SH11 | Body soap | SH | piece | |
| SH12 | Washing soap | SH | piece | |
| MF01 | ORS packets / electrolytes | MF | packet | |
| MF02 | Mosquito repellents / Odomos | MF | piece | |
| MF03 | Antiseptic lotion | MF | bottle | |
| MF04 | Anti-fungal powder | MF | piece | |
| SU01 | Candles | SU | packet | |
| KU01 | Match box | KU | packet | |

**Medicines:** the sheet has a "Medicines" heading but **no items under it** in the screenshot. Leave medicines out of the seed until the team gets the full list. When added, set `requires_approval = TRUE`.

**Defaults for the seed file:** `perishable` = TRUE only for vegetables; `requires_approval` = FALSE for all current items; `emergency_eligible` = leave **empty** (means "to be confirmed with DDMA").

### 7.3 Water and toilet norms (for the report and later features)

These come from two tables in the team's screenshots (they look like Sphere-style standards; **confirm the exact source, edition and page before citing**). They are **not** used in the Week 1 calculations. Keep them in the report and use them in later stages.

| Use | Amount (from the table) |
|---|---|
| Survival (drinking + food) | 2.5–3 litres per person per day |
| Basic hygiene | 2–6 litres per person per day |
| Basic cooking | 3–6 litres per person per day |
| Reception / transit centres | 15 L per person per day if stay is over one day; 3 L if day-time only |
| Health centres | 5 L per outpatient; 40–60 L per in-patient per day |
| Livestock | 20–30 L per large/medium animal per day; 5 L per small animal |

| Toilets (from table) | Short term | Medium / long term |
|---|---|---|
| Community | 1 toilet per 50 persons | 1 per 20 persons (or 1 per 5 persons / 1 per family) |
| Reception / transit centres | 1 per 50 individuals; 3:1 female to male | — |

Simple idea for later: because drinking needs are about 2.5–3 L/person/day, one 20 L can covers roughly 7 people's drinking water for one day (20 ÷ 3 ≈ 6.7).

### 7.4 Fake camps (for `seed_camps.csv`) — C creates ~6 rows

Make the camps different from each other so the ranking is interesting. Coordinates should be real places in the region (use Google Maps to right-click a point and copy the numbers). These approximate values are only a starting point:

| Camp (fake name) | Near | Approx. lat, long | Occupancy | Children / Elderly / Pregnant / Disabled | Damage | Access |
|---|---|---|---|---|---|---|
| Test Camp 1 | Chengannur | 9.32, 76.61 | 400 | 90 / 60 / 10 / 5 | 4 | 5 |
| Test Camp 2 | Kuttanad (Kainakary area) | 9.46, 76.40 | 500 | 120 / 80 / 15 / 10 | 5 | 5 |
| Test Camp 3 | Thiruvalla | 9.38, 76.57 | 150 | 30 / 20 / 2 / 1 | 2 | 2 |
| Test Camp 4 | Pathanamthitta | 9.26, 76.78 | 220 | 50 / 40 / 5 / 3 | 3 | 3 |
| Test Camp 5 | Alappuzha | 9.49, 76.33 | 300 | 70 / 45 / 8 / 4 | 3 | 4 |
| Test Camp 6 | Changanassery | 9.44, 76.54 | 80 | 15 / 12 / 1 / 0 | 1 | 1 |

(Set `damage_level` and `access_difficulty` between 1 and 5. `last_supply_at` can be empty for some and a few hours/days ago for others.)

### 7.5 Fake hubs (for `seed_hubs.csv`) — 3 rows

| Hub (fake name) | Near | Approx. lat, long |
|---|---|---|
| Test Hub Alappuzha | Alappuzha | 9.49, 76.33 |
| Test Hub Kottayam | Kottayam | 9.59, 76.52 |
| Test Hub Pathanamthitta | Pathanamthitta | 9.26, 76.78 |

### 7.6 Starting stock (for `seed_stock.csv`)

Give each hub stock of **most items**, but make some items **scarce on purpose** (for example only 50 kg of rice at one hub, or 0 blankets) so the allocation has something to decide. Also write down the expected result of one tricky case (see Section 9.4) so D can test against it.

### 7.7 Sample requests (for `seed_requests.csv`)

Create 5–8 requests from different camps. Mix: some escalated, some not, some asking for items that hubs are short of, one request with many items, one old request (to test the time effect).

---

## 8. The priority engine (SAW) — exact rules

📌 **Contract.** Owner: **C**. SAW = *Simple Additive Weighting*. It gives each camp a score from 0 to 100. A higher score means a higher priority.

### 8.1 The six criteria

| # | Criterion | Where the number comes from | Turned into 0–1 by |
|---|---|---|---|
| 1 | **People** | `camps.occupancy` | `occupancy ÷ highest occupancy among active camps` |
| 2 | **Vulnerable share** | children + elderly + pregnant + disabled | `min(1, (children + elderly + pregnant + disabled) ÷ occupancy)` (if occupancy is 0, use 0). The groups may overlap, so we cap at 1. |
| 3 | **Damage** | `camps.damage_level` (1–5) | `(damage_level − 1) ÷ 4` |
| 4 | **Access difficulty** | `camps.access_difficulty` (1–5) | `(access_difficulty − 1) ÷ 4` |
| 5 | **Time since last supply** | `now − last_supply_at` (if empty, use `created_at`) | `min(hours, CAP) ÷ CAP`, with `CAP = 72` hours (placeholder) |
| 6 | **Escalation** | 1 if the camp has at least one open request with `escalated = TRUE`, else 0 | the value itself (0 or 1) |

"Open request" means status is `pending` or `partially_allocated`. Only camps with `status = 'active'` are ranked.

### 8.2 The weights (placeholders!)

```python
# in config.py  (A creates it; C may adjust ONLY the numbers, after the team agrees)
SAW_WEIGHTS = {
    "people": 0.20,
    "vulnerable": 0.25,
    "damage": 0.20,
    "access": 0.15,
    "time": 0.10,
    "escalation": 0.10,
}   # must add up to 1.00
TIME_CAP_HOURS = 72
```

⚠️ **These weights are placeholders chosen by this guide.** They are **not** official. DDMA will decide the real weights, the time-factor cap, and how damage should be weighted (Part A vs Part B). When they confirm, only the numbers in `config.py` change. The code does not change. Each ranking run stores the weights it used (`priority_runs.weights_json`), so any result can be explained later.

### 8.3 The formula

```
score = 100 × ( w_people×people + w_vulnerable×vulnerable + w_damage×damage
              + w_access×access + w_time×time + w_escalation×escalation )
```

### 8.4 Worked example (use it as a test)

Camp X: occupancy 400, the highest occupancy among camps is 500; children 90, elderly 60, pregnant 10, disabled 20 (total 180); damage 4; access 5; last supply 48 hours ago; one escalated open request.

| Criterion | 0–1 value | Weight | Contribution |
|---|---|---|---|
| People | 400 ÷ 500 = 0.80 | 0.20 | 0.1600 |
| Vulnerable | 180 ÷ 400 = 0.45 | 0.25 | 0.1125 |
| Damage | (4−1) ÷ 4 = 0.75 | 0.20 | 0.1500 |
| Access | (5−1) ÷ 4 = 1.00 | 0.15 | 0.1500 |
| Time | 48 ÷ 72 = 0.6667 | 0.10 | 0.0667 |
| Escalation | 1 | 0.10 | 0.1000 |
| **Total** | | | **0.7392 → score ≈ 73.92** |

✅ **Check:** `tests/test_priority.py` must contain this exact example and expect ≈ 73.92 (allow a tiny rounding difference).

### 8.5 Ties and edge cases

- Same score: the camp with the **older oldest open request** ranks higher; if still tied, lower `camp_id`.
- Camps with **no open requests** still get a score (so the admin can see the whole picture), but the allocation step ignores them because they have no needs.
- If only one camp exists, people = 1.0 if occupancy > 0.
- Never divide by zero. Handle it and return 0.

### 8.6 The function (C's contract with D and the web page)

```python
# engines/priority_engine.py
def compute_priority(camps: list[dict], weights: dict, now, time_cap_hours: float = 72) -> list[dict]:
    """
    camps: each dict has keys:
        camp_id, occupancy, children_count, elderly_count, pregnant_count,
        disabled_count, damage_level, access_difficulty,
        last_supply_at (datetime or None), created_at (datetime),
        has_escalation (True/False), oldest_open_request_at (datetime or None)
    returns: list sorted from highest to lowest priority, each item:
        {"camp_id": 3, "score": 73.92, "rank": 1,
         "breakdown": {"people": 0.80, "vulnerable": 0.45, "damage": 0.75,
                       "access": 1.0, "time": 0.6667, "escalation": 1}}
    """
```

This is a **pure function**: no database inside, so it is easy to test. The router (`priority_router.py`) loads the camps from the database, calls this function, and saves the result in `priority_runs` and `priority_scores`.

---

## 9. The allocation engine — exact rules

📌 **Contract.** Owner: **D**.

### 9.1 What allocation means
Take the camps in priority order. For each camp, for each item it still needs, take stock from the **nearest hub that has it**, then the next nearest, until the need is met or no hub has stock left.

### 9.2 Step by step

1. Get the **latest ranking** (`priority_scores` of the newest `priority_runs`).
2. For each camp, work out its **open needs**: for every item, `sum(qty_requested − qty_allocated)` over its open requests. Ignore items with nothing left to need.
3. Load current **stock** for all active hubs.
4. Work out the **distance** from each camp to each hub, in metres, with PostGIS:
   ```sql
   SELECT ST_Distance(
     ST_SetSRID(ST_MakePoint(h.longitude, h.latitude), 4326)::geography,
     ST_SetSRID(ST_MakePoint(c.longitude, c.latitude), 4326)::geography
   ) AS metres
   FROM camps c, hubs h WHERE c.camp_id = %s AND h.hub_id = %s;
   ```
   ⚠️ This is **straight-line** distance, not road distance. Say so honestly in the report: real road or boat routes are a later improvement.
5. Go through camps from rank 1 downwards. For each of its needed items, go through hubs from nearest to farthest. Take `min(still needed, hub stock)`. Reduce the hub stock and the remaining need. Stop when the need is zero.
6. Save the plan: one `allocations` row for each (camp, hub, item) with `qty > 0`, status `planned`.
7. **In the same transaction:** reduce `stock`, write `stock_movements` (reason `allocation`), and add the quantities to `request_items.qty_allocated`. Share the allocated amount among the camp's open requests, **oldest request first**. Update each request's status: `fulfilled` if all its lines are fully allocated, `partially_allocated` if some quantity is allocated, otherwise unchanged.
8. If anything fails, **roll back everything**. No half-finished allocation.

### 9.3 Fairness note
This simple rule serves the highest-priority camp **fully** before the next. If stock is short, lower-ranked camps may get nothing for that item. This is the Week 1 rule because it is easy to understand and test. A fairer "share proportionally" option can be discussed with DDMA later and is listed in Section 18.

### 9.4 Worked example (use it as a test)

Hub H1 has 100 kg rice. Ranking: Camp 1 first, Camp 2 second, Camp 3 third. They need 60, 50 and 40 kg of rice. All hubs are equally near (only one hub).

| Order | Camp | Needs | Gets | Hub rice left |
|---|---|---|---|---|
| 1 | Camp 1 | 60 | 60 | 40 |
| 2 | Camp 2 | 50 | 40 | 0 |
| 3 | Camp 3 | 40 | 0 | 0 |

Camp 2's request becomes `partially_allocated` (10 kg short). Camp 3's stays `pending`. Camp 1's becomes `fulfilled`.

Second test: if the rice stock at the nearest hub is 30 and another hub has 100, a camp needing 60 should get 30 from the nearest and 30 from the next.

### 9.5 Functions (D's contract)

```python
# engines/allocation_engine.py

def plan_allocation(ranked_camp_ids, open_needs, hub_stock, distances):
    """
    PURE function (no database), easy to test.
    ranked_camp_ids: [camp_id, ...] from highest priority to lowest
    open_needs:  {camp_id: {item_id: qty_needed}}
    hub_stock:   {hub_id: {item_id: qty_available}}
    distances:   {(camp_id, hub_id): metres}
    returns: [{"camp_id":1, "hub_id":2, "item_id":5, "qty":60}, ...]
    """

def run_allocation(conn, priority_run_id, user_id):
    """
    Loads data from the database, calls plan_allocation, then writes everything
    in ONE transaction (allocations, stock, stock_movements, request_items,
    requests). Returns a short summary dict. Rolls back on any error.
    """
```

### 9.6 Marking dispatched
Hub coordinators press **Mark dispatched** on a planned allocation. This sets the allocation status to `dispatched` and sets `camps.last_supply_at = now()`. (The **delivered** status and QR confirmation come in Part 4.)

---

## 10. API list and permissions

📌 **Contract.** Endpoint names must match exactly. Pages (HTML) call these. "Any" = any logged-in user.

| Method and path | Who | What it does | Owner |
|---|---|---|---|
| GET `/health` | public | `{"status":"ok"}` | A |
| POST `/auth/login` | public | Log in, start a session | A |
| POST `/auth/logout` | any | Log out | A |
| GET `/auth/me` | any | Who am I (username, role, camp_id, hub_id) | A |
| POST `/auth/register-donor` | public | A donor creates an account (role forced to `donor`) | A |
| POST `/admin/users` | admin | Create camp officer / hub coordinator / admin user | A |
| GET `/items` | any | List active items (filter `?category=FW`) | B |
| POST `/items`, PUT `/items/{id}` | admin | Add or edit an item | B |
| POST `/camps` | admin | Create a camp | B |
| GET `/camps`, GET `/camps/{id}` | admin; officer sees only own camp | View camps | B |
| PUT `/camps/{id}` | admin; officer (own camp) | Update occupancy, counts, damage, access, status | B |
| POST `/requests` | camp_officer | Submit a request (items + qty + escalate + comment) | B |
| GET `/requests` | admin all; officer own camp | List requests (`?camp_id=`, `?status=`) | B |
| GET `/requests/{id}` | admin / owning officer | Request detail with allocated quantities | B |
| POST `/requests/{id}/escalate` | camp_officer (own) | Turn on escalation for an open request | B |
| POST `/requests/{id}/cancel` | camp_officer (own) | Cancel an open request | B |
| POST `/priority/run` | admin | Calculate and save a new ranking | C |
| GET `/priority/latest` | admin | Latest ranking with breakdown | C |
| POST `/hubs` | admin | Create a hub | D |
| GET `/hubs` | admin, hub_coordinator | List hubs | D |
| GET `/stock` | admin; hub coordinator sees own hub | Stock by hub (`?hub_id=`) | D |
| POST `/stock/adjust` | hub_coordinator (own), admin | Manual correction with a reason | D |
| POST `/donations` | donor | Offer items (auto-assigns a hub in the donor's district if one exists) | A |
| GET `/donations` | donor own; admin all; hub coordinator own hub | List donations | A |
| POST `/donations/{id}/assign-hub` | admin | Set or change the hub | A |
| POST `/hub/donations/{id}/receive` | hub_coordinator (own hub) | Confirm arrival → adds stock | D |
| POST `/allocation/run` | admin | Run allocation using the latest ranking | D |
| GET `/allocation/latest` | admin | Latest allocation results | D |
| GET `/allocation?camp_id=` | admin; officer (own camp); hub coordinator (own hub) | Allocations list | D |
| POST `/allocation/{id}/dispatch` | hub_coordinator (own hub) | Mark an allocation dispatched | D |

**Login method (A decides the details):** a simple session cookie after login. Passwords are stored **hashed**, never as plain text.

**Fake login for development (A builds this on Day 1):** in `.env`

```
DEV_BYPASS_LOGIN=true
DEV_FAKE_ROLE=admin          # or camp_officer / hub_coordinator / donor
DEV_FAKE_CAMP_ID=1
DEV_FAKE_HUB_ID=1
```

When `DEV_BYPASS_LOGIN=true`, `get_current_user()` returns a pretend user with those values. This lets B, C and D build their pages before real login works. ⚠️ Turn it **off** before the demo and test with real logins.

**Helpers everyone uses (A provides in `deps.py`):**

```python
from deps import get_current_user, require_role
# Example in a router:  user = Depends(require_role("admin"))
```

---

## 11. Member task sheets

How to read a task: **Task ID** (for the tracker), **Day** (target), **Files** you create or edit, **Steps**, and **Done when** (the checks that prove it works). Use the matching ready-made prompt in Section 12.4.

---

### MEMBER A — Foundation: database, login, donors

**Why your work matters:** every other person's work stands on yours. Be fast on A1.

#### A1 — Project skeleton (Day 1, FIRST, push by evening)
**Files:** everything listed as `[A]` in Section 5, plus **empty stub files for every router** and `.gitignore`.
**Steps**
1. Create the folder structure of Section 5.
2. `schema.sql` = the SQL of Section 6.2 (copy exactly).
3. `database.py`: one function `get_conn()` that connects using `DATABASE_URL` from `.env`.
4. `config.py`: loads `.env`, and holds `SAW_WEIGHTS` and `TIME_CAP_HOURS` (Section 8.2).
5. `deps.py`: `get_current_user()` and `require_role(*roles)` with the **fake login** switch (Section 10).
6. For **every router file** in Section 5, create a stub containing only:
   ```python
   from fastapi import APIRouter
   router = APIRouter()
   ```
7. `main.py`: creates the app, adds **all** routers (so nobody else needs to edit it), serves `static/`, and has `GET /health`.
8. `requirements.txt` (fastapi, uvicorn, psycopg2-binary, python-dotenv, jinja2, python-multipart, itsdangerous, a password-hashing library, pytest, and whatever Antigravity needs). `.env.example` as in Section 4. `.gitignore` containing `venv/`, `.env`, `__pycache__/`, `*.pyc`.
9. `reset_db.py`: runs `schema.sql` against the database.
10. Push to GitHub on `main` (A is the only person allowed to push straight to `main`, and only for A1).

**Done when:** a fresh clone → setup (Section 4) → `uvicorn main:app --reload` starts without errors, `/health` shows ok, and `python reset_db.py` creates all tables (check in pgAdmin that 14 tables exist).

#### A2 — Real login and roles (Day 2)
**Files:** `routers/auth_router.py`, `deps.py`, `seed/seed_users.py`, `templates/base.html`, `templates/login.html`, `static/style.css`
**Steps**
1. Hash passwords. Never store plain text.
2. Endpoints: `/auth/login`, `/auth/logout`, `/auth/me`, `/auth/register-donor`, `/admin/users` (Section 10).
3. `seed_users.py` creates four **test** users (usernames `admin1`, `officer1` → camp 1, `hub1` → hub 1, `donor1` → district "Alappuzha") with a simple test password written in a comment ("test only"). It runs *after* camps and hubs exist (C's loader calls it).
4. `base.html` shows a menu that depends on the user's role (admin sees everything; officer sees camp and requests; and so on).

**Done when:** you can log in as each of the four users and see the right menu; a wrong password is refused; an officer who opens an admin URL gets "403 Forbidden"; `tests/test_auth.py` passes.

#### A3 — Donor module (Day 2–3)
**Files:** `routers/donors_router.py`, `templates/donor_form.html`, `donor_history.html`, `admin_donations.html`
**Steps**
1. Donor form: pick items from the catalog (dropdown, shows `acceptance_rule` next to the item, e.g. "No cream biscuits"), enter quantity; can add several lines.
2. `POST /donations`: check that items are active, quantities > 0, no duplicate items. Create the donation. If an **active hub exists in the donor's district**, set it as `assigned_hub_id` and status `hub_assigned`; otherwise status `offered`.
3. `GET /donations` with the permissions of Section 10.
4. Admin page lists donations and has an **Assign hub** dropdown (`POST /donations/{id}/assign-hub`).
5. Donors never see camps (mandatory routing).

**Done when:** `donor1` offers 100 kg rice → the donation appears as `hub_assigned` to the Alappuzha hub; the admin can change the hub; invalid input (negative quantity) shows a friendly error.

#### A4 — Glue and health of the whole app (Day 4–6)
- Day 4: merge help. Make sure **all routers load** and the menu links to every page.
- Day 5: fix import and menu problems found during integration.
- Day 6: turn **fake login OFF**; run the full demo (Section 15.4) with real logins.
- Keep `requirements.txt` correct: ask everyone "did you install anything new?"

**Done when:** a brand-new laptop can set up from this guide alone and run the demo.

---

### MEMBER B — Camps, catalog and requests

#### B1 — Item catalog (Day 1–2)
**Files:** `seed/seed_items.csv`, `routers/items_router.py`, `templates/items.html`
**Steps**
1. Turn the table in Section 7.2 into `seed_items.csv` (**push on Day 1** so C can load it).
2. `GET /items` (optional `?category=`), `POST /items` and `PUT /items/{id}` (admin only).
3. `items.html`: items grouped by category, with the acceptance rule visible.

**Done when:** the page shows about 43 items in 7 category groups; "Drinking water" shows "can (20 L)" and the "only 20-litre cans" rule; non-admin users cannot add items.

#### B2 — Camps (Day 2–3)
**Files:** `routers/camps_router.py`, `templates/camp_list.html`, `camp_form.html`, `camp_update.html`
**Steps**
1. Admin creates and edits camps (name, district, address, latitude, longitude, capacity, status).
2. **Officer update page** (own camp only): occupancy, children, elderly, pregnant, disabled counts, damage level (1–5), access difficulty (1–5). Each save sets `updated_at = now()`.
3. Validation: numbers must not be negative; damage and access between 1 and 5; each group count cannot exceed occupancy (groups may overlap, so the **sum** is allowed to exceed it).
4. Plain-language help text next to each field (for example, "Damage level: 1 = little damage, 5 = severe").

**Done when:** an officer can update only their own camp (trying another camp's ID gives 403); the admin sees all camps; `GET /camps/{id}` returns the values in the exact field names of Section 6.2.

#### B3 — Requests (Day 3–4)
**Files:** `routers/requests_router.py`, `templates/request_form.html`, `request_list.html`, `request_detail.html`
**Steps**
1. Request form: pick items (grouped by category), quantity, an **Escalate** checkbox ("Mark as urgent"), and a **plain comment box** (max 500 characters; **not scored, not analysed**).
2. `POST /requests`: at least one item; quantity > 0; no duplicate items; camp must be the officer's own camp and `active`. Save `requests` and `request_items`.
3. List page with status; detail page shows **requested vs allocated** for each line.
4. `POST /requests/{id}/escalate` and `POST /requests/{id}/cancel` (only for open requests, only by the owning officer).

**Done when:** `officer1` submits a request with two items and escalation → it appears with status `pending`; submitting zero items or quantity 0 shows an error; `tests/test_requests.py` passes.

#### B4 — "What is coming" and tests (Day 5–6)
- Day 5: officer page showing allocations for their camp (`GET /allocation?camp_id=`, from D). Until D finishes, test with a manually inserted `allocations` row.
- Day 6: finish `tests/test_requests.py`; verify C's tasks (buddy check).

**Done when:** after an allocation run, the officer sees which items are coming, from which hub, and the request status is updated.

---

### MEMBER C — Priority engine, test data, testing

#### C1 — Seed data and loader (Day 1–2; items first)
**Files:** `seed/seed_camps.csv`, `seed_hubs.csv`, `seed_stock.csv`, `seed_requests.csv`, `seed/load_seed.py`
**Steps**
1. Day 1: write `load_seed.py` with the option `--only items` so B can load the catalog immediately.
2. Create the CSVs using Sections 7.4–7.7 (fake data only).
3. Loader order: items → camps → hubs → users (call A's `seed_users.py`) → stock → requests + request_items. Each run starts clean (`reset_db.py`), so it can be repeated safely.
4. At the end, print counts: "items: 43, camps: 6, hubs: 3, ..." (check against the CSV rows).

**Done when:** `python seed/load_seed.py` gives the same counts on every laptop. **Push by midday Day 2.**

#### C2 — Priority engine (Day 2–3)
**Files:** `engines/priority_engine.py`, `tests/test_priority.py`
**Steps**
1. Implement `compute_priority` exactly as in Section 8 (no database inside).
2. Tests: the worked example (≈ 73.92); occupancy = 0; a single camp; `last_supply_at` empty (use `created_at`); time capped at 72 h; tie-break rule; weights that don't add up to 1 → clear error message.

**Done when:** `pytest tests/test_priority.py` is all green.

#### C3 — Ranking router and page (Day 3–4)
**Files:** `routers/priority_router.py`, `templates/admin_priority.html`
**Steps**
1. `POST /priority/run`: load active camps with the fields in Section 8.6 (SQL join with requests to get `has_escalation` and `oldest_open_request_at`), call the engine, save a `priority_runs` row (with `weights_json`) and one `priority_scores` row per camp.
2. `GET /priority/latest`.
3. Page: ranked table (rank, camp, score, escalation icon) with the six breakdown values visible (simple coloured bars are fine), the time of the run and the weights used. A **Recalculate** button.

**Done when:** with seed data, the ranking appears; Test Camp 2 and Test Camp 1 are near the top and Test Camp 6 is near the bottom; changing a camp's damage level and recalculating changes the ranking sensibly.

#### C4 — End-to-end test and demo owner (Day 5–6)
**Files:** `tests/test_flow.py`, a short `docs/DEMO_SCRIPT.md` (copy of Section 15.4 with real screenshots)
**Steps**
1. Write an automated test that runs the flow of Section 15.4 through the API.
2. Day 6: lead the "test day" (Section 16): collect bugs in the tracker, assign them, and re-test.

**Done when:** `pytest tests/test_flow.py` passes on a clean database.

---

### MEMBER D — Hubs, stock, allocation

**Note:** your area is the heaviest. If time runs short, use the **fallback** in D4.

#### D1 — Hubs and stock (Day 1–2)
**Files:** `routers/hubs_router.py`, `routers/stock_router.py`, `templates/hub_list.html`, `hub_dashboard.html`
**Steps**
1. Admin creates hubs; list hubs.
2. `GET /stock` (hub coordinator sees own hub only).
3. `POST /stock/adjust`: coordinator or admin enters a quantity change **with a reason**. In one transaction update `stock` and write `stock_movements` (reason `manual_adjustment`). Refuse changes that would make stock negative.
4. `hub_dashboard.html`: stock table for the hub.

**Done when:** `hub1` sees only their hub's stock; an adjustment changes the stock and creates a movement row; removing more than available is refused with a clear message.

#### D2 — Allocation logic (Day 2–3)
**Files:** `engines/allocation_engine.py` (the `plan_allocation` function), `tests/test_allocation.py`
**Steps:** implement `plan_allocation` as in Section 9.2 and 9.5.
**Tests:** the rice example of Section 9.4 (60 / 40 / 0); the two-hub split (30 from the nearest, 30 from the next); a camp with no needs; an item no hub has; two camps competing for the last stock; hubs at the same distance (pick lowest `hub_id`).

**Done when:** `pytest tests/test_allocation.py` is all green. No database needed for these tests.

#### D3 — Receiving donations (Day 3–4)
**Files:** `routers/stock_router.py` (endpoint `POST /hub/donations/{id}/receive`), `templates/hub_dashboard.html` (incoming donations list)
**Steps**
1. Only the coordinator of the assigned hub can receive; the donation must be `hub_assigned`.
2. One transaction: for each donation item, add to `stock`, write `stock_movements` (`donation_received`, `ref_id = donation_id`), set donation `received` and `received_at`.
3. A second "Receive" click on the same donation must do nothing (no double-adding).

**Done when:** `donor1`'s 100 kg rice donation → `hub1` presses Receive → rice stock +100 → pressing again changes nothing.

#### D4 — Run allocation (Day 4–5)
**Files:** `engines/allocation_engine.py` (`run_allocation`), `routers/allocation_router.py`, `templates/allocation_results.html`, `hub_dashboard.html` (planned allocations + **Mark dispatched**)
**Steps**
1. `run_allocation` as in Section 9.2 (steps 1–8), in one transaction.
2. `POST /allocation/run` (admin), `GET /allocation/latest`, `GET /allocation?camp_id=`, `POST /allocation/{id}/dispatch` (sets `last_supply_at`).
3. Results page: for each camp, what it got, from which hub, and what is still short.

**Fallback if time runs out:** each camp may use only its **single nearest hub** (no splitting across hubs). Tell the team if you switch, and record it in the Change Log.

**Done when:** with seed data and a fresh ranking, the allocation matches your hand calculation; stock goes down; running allocation a second time does **not** allocate the same needs twice.

#### D5 — Tests and fixes (Day 6)
Finish `tests/test_allocation.py`; verify A's work (buddy check); help fix bugs found on test day.

---

## 12. Antigravity rules and ready-made prompts

Antigravity writes code from your instructions. It is fast but it can make mistakes, change files it shouldn't, or "improve" things you didn't ask for. **These rules make it safe.**

### 12.1 The routine for every Antigravity session

1. Open Antigravity **in the project folder** and check you are on **your own branch** (`git branch` — the one with `*`).
2. Paste the **Master Prompt** (12.2).
3. Paste the **task prompt** for your Task ID (12.4).
4. Ask for a **plan first** and read it. If it wants to edit files you don't own, say no.
5. Let it write the code, **one task at a time**.
6. Run it using the commands it gives you. ✅ Check what you see matches what it said you should see.
7. Run the tests. If something fails, paste the **exact error message** back into Antigravity.
8. Run `git status` — are only your files changed? If not, undo the others (`git restore <file>`).
9. Commit and push (Section 13). Update the tracker (Section 14).

### 12.2 The Master Prompt (paste at the start of EVERY session)

```
You are helping a team of final-year students who are NOT confident coders build
a university project called DisasterReliefMVP (a disaster relief allocation
platform for Kerala). Explain things in plain language. Work in small steps.

FIRST read docs/DisasterRelief_Team_Guide.md (at least Sections 1, 5, 6, 8, 9, 10
and the section for my task).

Rules you must follow:
1. I am Member <A / B / C / D>. Create or edit ONLY files that I own (Guide
   Section 5). If another file must change, STOP and tell me what and why.
2. Do NOT change schema.sql, table or column names, function names, API paths
   or status words. They are fixed contracts. If one looks wrong, tell me.
3. Tech: Python, FastAPI, PostgreSQL + PostGIS (psycopg2), Jinja2 HTML templates,
   plain CSS. No JavaScript frameworks. Free tools only. Do not add a new
   library without telling me why.
4. Use parameterised SQL (%s placeholders). Never build SQL by joining strings
   that contain user input.
5. Anything that changes stock or allocations must happen inside ONE database
   transaction and roll back on any error.
6. Never invent data or facts. Test data is fake and must be labelled so.
   Weights and norms are placeholders unless the guide says otherwise.
7. Add short plain-English comments. Keep functions small and simple.
8. BEFORE writing code, show me a short plan in plain words (which files you
   will create or edit) and wait for my OK.
9. AFTER writing code, give me (a) the exact commands to run it, (b) exactly
   what I should see on screen if it works, and (c) tests for my area.
10. If you are unsure, ask me ONE clear question instead of guessing.
```

### 12.3 Do and don't

| ✅ Do | ❌ Don't |
|---|---|
| Ask for one small task at a time | Ask "build the whole project" |
| Paste exact error messages | Say "it doesn't work" with no details |
| Make Antigravity explain code you don't understand | Accept code you can't run |
| Commit after every working step | Wait until the end of the week |
| Keep the guide open in a tab | Rely on Antigravity's memory of earlier chats |
| Say "do not touch other files" | Let it "refactor" or "clean up" everything |

### 12.4 Ready-made task prompts (copy, paste, fill in)

After the Master Prompt, paste the prompt for your task.

**A1**
```
Task A1 (Guide Section 11, Member A). Create the project skeleton exactly as in
Guide Section 5: folders, empty stub router files (only "router = APIRouter()"),
schema.sql copied EXACTLY from Section 6.2, database.py (get_conn using
DATABASE_URL), config.py (.env loading + SAW_WEIGHTS + TIME_CAP_HOURS from
Section 8.2), deps.py with get_current_user and require_role plus the fake-login
switch from Section 10, main.py that includes ALL routers and has GET /health,
reset_db.py, requirements.txt, .env.example and .gitignore. Show the plan first.
```

**A2**
```
Task A2. Build real login. Endpoints: /auth/login, /auth/logout, /auth/me,
/auth/register-donor, /admin/users (Guide Section 10). Hash passwords. Use a
session cookie. Create seed/seed_users.py with 4 TEST users (admin1, officer1 ->
camp 1, hub1 -> hub 1, donor1 -> district Alappuzha). Create templates/base.html
(menu depends on role), login.html and static/style.css. Do not change
schema.sql. Write tests/test_auth.py.
```

**A3**
```
Task A3. Build the donor module: donor form (items from catalog with the
acceptance_rule shown), POST /donations (validate items active, qty>0, no
duplicates; auto-assign an active hub in the donor's district -> status
hub_assigned, else offered), GET /donations (permissions in Section 10),
POST /donations/{id}/assign-hub (admin). Pages: donor_form.html,
donor_history.html, admin_donations.html. Donors must never see camps.
```

**B1**
```
Task B1. Create seed/seed_items.csv from the table in Guide Section 7.2 (columns:
item_code,name,category,unit,perishable,requires_approval,emergency_eligible,
acceptance_rule,norm_note; leave emergency_eligible empty; leave Medicines out).
Then build routers/items_router.py (GET /items with optional ?category=,
POST and PUT for admin only) and templates/items.html grouped by category,
showing the acceptance rule.
```

**B2**
```
Task B2. Build camps: routers/camps_router.py and pages camp_list.html,
camp_form.html (admin) and camp_update.html (officer, own camp only). Fields and
validation exactly as in Guide Section 11 B2 and the camps table in Section 6.2.
Set updated_at on every save. Add plain-language help text beside damage_level
and access_difficulty.
```

**B3**
```
Task B3. Build requests: routers/requests_router.py, request_form.html,
request_list.html, request_detail.html. Include an Escalate checkbox and a plain
comment box (max 500 chars, NOT scored or analysed). Validation as in Guide
Section 11 B3. Detail page shows requested vs allocated per item. Add
POST /requests/{id}/escalate and /cancel for the owning officer on open requests.
```

**B4**
```
Task B4. Add a page where a camp officer sees allocations for their camp using
GET /allocation?camp_id= (the endpoint is owned by Member D; until it exists,
test with a manually inserted allocations row). Then complete tests/test_requests.py.
```

**C1**
```
Task C1. Create seed/load_seed.py (with option --only items) and the CSV files
seed_camps.csv, seed_hubs.csv, seed_stock.csv, seed_requests.csv using Guide
Sections 7.4-7.7. All data is FAKE. Loader order: items, camps, hubs, users
(call seed/seed_users.py), stock, requests+request_items. Re-runnable on a clean
database. Print row counts at the end.
```

**C2**
```
Task C2. Implement engines/priority_engine.py: compute_priority exactly as in
Guide Section 8 (six criteria, placeholder weights from config.py, tie-break,
no database inside). Write tests/test_priority.py including the worked example in
Section 8.4 (expected about 73.92), occupancy 0, one camp, missing last_supply_at,
time cap, weights not adding to 1.
```

**C3**
```
Task C3. Build routers/priority_router.py (POST /priority/run, GET /priority/latest)
and templates/admin_priority.html. Load active camps with has_escalation and
oldest_open_request_at via SQL, call compute_priority, save priority_runs
(with weights_json) and priority_scores. The page shows rank, camp, score,
escalation icon, the six breakdown values (simple bars), time of run and weights.
```

**C4**
```
Task C4. Write tests/test_flow.py: an automated test that runs the demo flow of
Guide Section 15.4 through the API on a clean seeded database. Also create
docs/DEMO_SCRIPT.md from Section 15.4.
```

**D1**
```
Task D1. Build routers/hubs_router.py and routers/stock_router.py: create/list
hubs (admin), GET /stock (coordinator sees own hub only), POST /stock/adjust with
a required reason. Each stock change must update stock AND write stock_movements
inside ONE transaction and must refuse negative stock. Page: hub_list.html and
hub_dashboard.html (stock table).
```

**D2**
```
Task D2. Implement plan_allocation in engines/allocation_engine.py exactly as in
Guide Sections 9.2 and 9.5 (pure function, no database). Write
tests/test_allocation.py with the rice example in Section 9.4 (60 / 40 / 0), the
two-hub split (30 + 30), a camp with no needs, an item no hub has, competing
camps, and equal distances (lowest hub_id wins).
```

**D3**
```
Task D3. Add POST /hub/donations/{id}/receive to routers/stock_router.py. Only
the coordinator of the assigned hub; donation must be hub_assigned. One
transaction: add stock, write stock_movements (donation_received), set the
donation to received. Receiving twice must not add stock twice. Add an
"Incoming donations" list with a Receive button to hub_dashboard.html.
```

**D4**
```
Task D4. Implement run_allocation(conn, priority_run_id, user_id) and
routers/allocation_router.py (POST /allocation/run, GET /allocation/latest,
GET /allocation?camp_id=, POST /allocation/{id}/dispatch) exactly as in Guide
Section 9. Distances use the PostGIS query in Section 9.2. Everything in ONE
transaction. Running twice must not allocate the same need twice. Pages:
allocation_results.html and planned allocations with a Mark dispatched button
on hub_dashboard.html.
```

### 12.5 Checking Antigravity's work (the 8-point review)

Before you commit, answer yes to all of these:

1. Does it run without errors?
2. Does the screen show what the prompt said I should see?
3. Do the tests pass?
4. Did it touch only **my** files? (`git status`)
5. Are table names, column names, function names, API paths and status words **exactly** as in this guide?
6. Is the SQL parameterised (`%s`)? No passwords or secrets typed into the code?
7. Is anything that changes stock inside one transaction?
8. Could I explain in one sentence what this file does? (If not, ask Antigravity to explain it.)

### 12.6 If Antigravity's free limit runs out
Commit what works. Continue later, or use **Claude Code** (the team's backup tool) with the same Master Prompt. Keep prompts short and focused — long chats use more of the limit.

---

## 13. Git and GitHub cheat sheet

**What it is:** Git saves versions of the project. GitHub is the shared online copy. Each person works on their own **branch** (a private copy of the work). When the work is ready it is merged into **main** (the shared official version).

### 13.1 Branch names

| Member | Branch |
|---|---|
| A | `a-foundation` |
| B | `b-camps-requests` |
| C | `c-priority-testing` |
| D | `d-hubs-allocation` |

### 13.2 Your daily commands

```
git checkout main            (go to the shared version)
git pull                     (get everyone's latest merged work)
git checkout <your-branch>   (go to your own branch)
git merge main               (bring the latest shared work into yours)

... work, run, test ...

git status                   (what did I change? only MY files should show)
git add .
git commit -m "B3: request form works"
git push                     (first time: git push -u origin <your-branch>)
```

Create your branch the first time: `git checkout -b <your-branch>`.

### 13.3 Getting your work into main

1. On GitHub, open a **Pull Request** from your branch into `main`.
2. **Another member** reviews it (Section 14.4: who checks whose work), runs it, and presses **Merge**.
3. Everyone then runs `git checkout main` → `git pull` → `git checkout <your-branch>` → `git merge main`.

### 13.4 Commit message format
`<Task ID>: what changed` — for example `C2: priority engine passes worked example`.

### 13.5 Never do these
- Never commit `.env` (it contains your password).
- Never push to `main` directly (except A for task A1).
- Never edit someone else's files.
- If you see the word **CONFLICT**, stop. Do not guess. Take a screenshot and ask the group.

---

## 14. How we follow up

### 14.1 The daily rhythm (Week 1)

| When | What | Time |
|---|---|---|
| Fixed time each day (decide on Day 1) | **Check-in call**: each person answers 3 questions | 15 minutes |
| End of your work day | Post a **written update** in the group chat | 5 minutes |
| After each finished task | Update the **tracker** and post proof (screenshot) | 2 minutes |

**The 3 check-in questions:** (1) What did I finish since yesterday? (2) What am I doing today? (3) Am I blocked, and by whom?

**Written update template**

```
Member: B   Day: 3
Done: B2 camp update page (screenshot attached)
Doing next: B3 request form
Blocked: none  /  waiting for ___ to ___
Pushed: yes (branch b-camps-requests)
```

### 14.2 The progress tracker

Make **one shared Google Sheet** (free) with these columns. Everyone updates their own rows.

| Task ID | Owner | Description | Planned day | Status | Verified by | Proof / link | Notes |
|---|---|---|---|---|---|---|---|

**Status words (use exactly these):** `Not started` · `In progress` · `Blocked` · `Done` · `Verified`.

### 14.3 When is a task "Done"?

A task is **Done** only when **all** of these are true:

1. It runs without errors.
2. Its tests pass.
3. It follows the contracts of this guide.
4. It is pushed to GitHub.
5. Proof (screenshot or short description of what you saw) is posted.

It becomes **Verified** when another member has run it and confirmed.

### 14.4 Who verifies whose work

| Verifier | Checks the work of |
|---|---|
| D | A |
| A | B |
| B | C |
| C | D |

### 14.5 Blockers
If you are waiting for someone, post: `Blocked on <Task ID> — need <exact thing> from <person> by <day>`. The other person replies within a few hours with a date. If a dependency is late, use the workaround (fake login, seed data, a manually inserted row) so your own work continues.

### 14.6 Asking to change a contract

If you think a table, function, API or rule must change:

```
CHANGE REQUEST
From: <name>   Task: <ID>
What must change: ...
Why: ...
Who is affected: ...
```

Post it in the group. The owner of that contract (A for tables, C for the priority function, D for the allocation functions, the endpoint's owner for APIs) answers. If approved, **the owner edits this guide** and adds a line to the Change Log (Section 22). Everyone pulls the new version.

### 14.7 Handoff note

When you finish a part that someone else depends on, post:

```
HANDOFF: <Task ID> is ready on branch <name>.
What it gives you: <function / endpoint / page>
How to try it: <1–3 steps>
Known problems: <honest list>
```

---

## 15. Integration plan (how the pieces join)

### 15.1 The data flow (read left to right)

```
 DONOR ──offers items──► donations (A)
                              │ hub assigned (A) → hub receives (D)
                              ▼
                         STOCK at hubs (D) ◄── manual adjust (D)
                              │
 CAMP OFFICER ──► camp details (B) ──┐
              └─► requests (B) ──────┤
                                     ▼
                       PRIORITY ENGINE (C) ──► ranking
                                     │
                                     ▼
                       ALLOCATION ENGINE (D)
          (ranking + open needs + stock + distances)
                                     │
                                     ▼
              allocations → officer sees "what is coming" (B)
              hub marks dispatched (D) → camp.last_supply_at → next ranking (C)
```

### 15.2 What each person hands to whom

| From → To | What | Exactly |
|---|---|---|
| A → everyone | Tables, login helpers, app skeleton | `schema.sql`, `deps.py`, `main.py` |
| B → C | Camp and request data | Tables `camps`, `requests`, `request_items` (field names in Section 6.2) |
| C → D | Ranking | Tables `priority_runs`, `priority_scores` (latest run) |
| A → D | Donations to receive | Table `donations` with `assigned_hub_id` |
| D → B | Allocations for a camp | `GET /allocation?camp_id=` |
| D → C | Last supply time | `camps.last_supply_at` set at dispatch |

### 15.3 Merge order and checkpoints

| Checkpoint | When | What must be true |
|---|---|---|
| **CP1 Contracts frozen** | End of Day 1 | Everyone has read Sections 5–10; A1 pushed; everyone's setup works |
| **CP2 Data ready** | Day 2 | Seed data loads for everyone (C1) |
| **CP3 Solo parts working** | Day 4 call | Each person's own area runs alone with seed data |
| **CP4 Merge** | Day 4 | Branches merged in this order: **A → B → C → D** (A first because everyone depends on it) |
| **CP5 Flow works** | Day 5 | The demo flow runs once from start to end |
| **CP6 Clean test** | Day 6 | The demo flow passes on a fresh laptop with real login (fake login OFF) |
| **CP7 Demo** | Day 7 | Dry run and cleanup |

### 15.4 The demo flow (our "done" test for 50%)

Start from a clean database: `python reset_db.py` then `python seed/load_seed.py`. Fake login OFF.

| Step | Log in as | Action | You should see |
|---|---|---|---|
| 1 | `admin1` | Open camps and hubs lists | 6 test camps, 3 test hubs |
| 2 | `donor1` | Offer 100 kg rice and 50 blankets | Donation status `hub_assigned` to the Alappuzha hub |
| 3 | `hub1` | Incoming donations → **Receive** | Stock of rice +100 and blankets +50; pressing again changes nothing |
| 4 | `officer1` | Submit a request: rice 60 kg, blankets 30, **Escalate** ticked | Request `pending` |
| 5 | `admin1` | **Priority → Recalculate** | Ranking page; officer1's camp shows an escalation icon and a score with a breakdown |
| 6 | `admin1` | **Allocation → Run** | Results show who gets what from which hub; stock is reduced; shortages listed |
| 7 | `officer1` | Open "What is coming" | Items, quantities, hub; request status `fulfilled` or `partially_allocated` |
| 8 | `hub1` | **Mark dispatched** | Allocation `dispatched`; camp's last supply time updates |
| 9 | `admin1` | Recalculate priority again | That camp's time component drops (it was just supplied) |

If every step shows what is written, the 50% milestone is reached. ✅

### 15.5 Integration checklist (Day 5)

- [ ] Everyone is on the latest `main`.
- [ ] `pip install -r requirements.txt` works on a clean `venv`.
- [ ] `python reset_db.py` and `python seed/load_seed.py` work with no errors.
- [ ] All pages load from the menu.
- [ ] `pytest` passes for all test files.
- [ ] Demo flow (15.4) works from step 1 to step 9.

---

## 16. Week 1 calendar

| Day | A | B | C | D | Everyone |
|---|---|---|---|---|---|
| **1** | **A1** skeleton → push | **B1** items CSV → push | C1 loader (`--only items`) | D1 hubs & stock | Setup (Section 4); read Sections 0–2, 5–10; CP1 |
| **2** | A2 login | B1 items page | **C1** seed data (push by midday); start C2 | D1 finish; start D2 | CP2 |
| **3** | A3 donors | B2 camps | C2 finish; start C3 | D2 finish; start D3 | |
| **4** | A3 finish; A4 merge help | B3 requests | C3 ranking page | D3 receive donations; start D4 | **CP3 call; CP4 merge (A→B→C→D)** |
| **5** | A4 fix integration | B4 "what is coming" | C4 end-to-end test | D4 run allocation | **CP5 demo flow runs** |
| **6** | Real login ON; tests | Tests; verify | **Test day lead**; bug list | D5 fixes; tests | **CP6 clean run** |
| **7** | Cleanup | Cleanup | Demo script + screenshots | Cleanup | **CP7 demo dry-run + retro** (what went well, what to improve, what to carry to Part 3) |

⚠️ If you fall behind: **finish the core flow first** (request → ranking → allocation). Drop these in this order: pretty pages → optional validations → donor extras. Do **not** drop transactions or tests.

---

## 17. When something breaks

| Problem | Likely cause | What to do |
|---|---|---|
| `'python' is not recognized` | Python not on PATH | Re-run the Python installer and tick "Add Python to PATH" |
| `ModuleNotFoundError` | `venv` not active or libraries missing | `venv\Scripts\activate` then `pip install -r requirements.txt` |
| `password authentication failed` | Wrong password in `.env` | Fix `DATABASE_URL` in `.env` |
| `connection refused` | PostgreSQL not running | Start the PostgreSQL service (Windows "Services") |
| `extension "postgis" is not available` | PostGIS not installed | Install via Stack Builder → Spatial Extensions |
| `relation "xyz" does not exist` | Tables not created | `python reset_db.py` |
| Port 8000 already in use | App already running somewhere | Close the other terminal, or run `uvicorn main:app --reload --port 8001` |
| `403 Forbidden` | Wrong role | Check you are logged in as the right user, or `DEV_FAKE_ROLE` |
| `422 Unprocessable` | Data sent is in the wrong shape | Open `/docs`, look at the expected fields |
| `git push` rejected | Remote has newer work | `git pull`, then push again |
| Word **CONFLICT** in git | Two people edited the same file | Stop. Screenshot. Ask the group. Do not guess. |
| Antigravity changed files that aren't mine | It went beyond the task | `git status` to see them; `git restore <file>` to undo (this discards the change) |
| Antigravity keeps failing the same way | Prompt too big or unclear | Start a new session, paste the Master Prompt, give a smaller task and the exact error text |
| Allocation numbers look wrong | Test data or logic | Calculate by hand using the Section 9.4 method on a tiny case and compare |
| Stock went negative / double-counted | Missing transaction | Re-read rule 6.4; ask Antigravity to wrap the change in one transaction |

---

## 18. Open questions for DDMA

Bring this list to the DDMA meeting. Until answered, the guide uses the stated placeholders.

1. **Final SAW weights** (placeholders in Section 8.2).
2. **Time factor cap** (placeholder 72 hours).
3. **Damage weighting** — Part A vs Part B split (this guide uses one `damage_level` for now).
4. **Emergency-eligible items** (the field is empty for now).
5. **Medicines list** — the sheet has a heading with no items.
6. Meaning of **"Food grains"** and **"Clothes for kid's"** (vs "children's").
7. **Who issued the accepted-items list** (needed for citation) and whether it has per-camp or per-person quantities.
8. **Source and edition** of the water and toilet tables (needed for citation).
9. **Fairness rule:** strict priority (Week 1) or proportional sharing when stock is short.
10. **How donors should be matched to hubs** (district rule is a simplification).
11. **Real hub list** and whether hubs have capacity limits.
12. Does **historical camp-level consumption data** exist? (Needed to train forecasting in Part 3; otherwise we use synthetic data and say so openly.)
13. **Role onboarding** — the prototype uses admin-created accounts; the real process (SPARK/PEN-style invites) is simulated or described only.

---

## 19. How to explain the project (evaluator-ready answers)

Keep answers short and honest.

| If they ask… | Say… |
|---|---|
| What is this system? | A decision-support platform: it helps authorities see camp needs, rank camps by priority, and allocate relief stock fairly. Humans stay in charge. |
| How is it different from NGO donation websites? | Those are voluntary and unverified listings. Ours uses **mandatory routing**: all donations go through the system to hubs, so supply is matched to need. |
| Where is the AI/ML? | The priority score uses **SAW**, a multi-criteria decision method (deterministic). Demand forecasting with **Quantile Regression Forest** (Part 3) gives **ranges**, not guarantees. |
| Can you guarantee prediction accuracy? | Ranking is a calculation from entered data, so the same inputs always give the same result. Forecasts are ranges that support decisions; they are not promises. |
| Why not use NLP to judge urgency from comments? | We chose simplicity and trust: an **escalate button** plus a plain, unscored comment box. |
| What about people entering false numbers? | In Part 3, **anomaly-aware triage** flags unusual entries and asks the officer for an explanation. It does not accuse anyone. |
| Why PostgreSQL + PostGIS? | **ACID transactions** keep stock correct (no double counting). PostGIS calculates distances. |
| Is the distance real road distance? | No. Week 1 uses straight-line distance. Road or boat routing is a later improvement. |
| Is the data real? | No. Test data is fake. Item list comes from the team's accepted-items sheet; weights are placeholders until DDMA confirms. |

---

## 20. Glossary (plain words)

| Word | Meaning |
|---|---|
| **API / endpoint** | A web address the program uses to ask for or send data, like `/camps` |
| **Router** | A file that groups related endpoints |
| **Template** | An HTML page with blanks that the program fills in |
| **Database / table** | Where data is stored, like Excel sheets that follow strict rules |
| **Schema** | The full design of all tables |
| **Transaction** | A group of database changes that either all happen or none do |
| **ACID** | The promise that transactions are safe and consistent |
| **PostGIS** | An add-on to PostgreSQL for maps and distances |
| **SAW** | Simple Additive Weighting: score = sum of (weight × normalised value) |
| **MCDM** | Multi-criteria decision making |
| **QRF** | Quantile Regression Forest: a forecasting method that gives a range |
| **Seed data** | Sample data loaded to test the system |
| **Contract** | A rule everyone agrees not to change alone |
| **Pure function** | A function that uses only its inputs (no database), so it's easy to test |
| **Branch** | Your own copy of the work in Git |
| **Commit** | A saved checkpoint |
| **Pull request** | A request to merge your branch into `main` |
| **Merge conflict** | Git can't combine two edits to the same place |
| **venv** | A private box of Python libraries for this project |
| **.env** | A private file of settings (never shared) |
| **Hub** | A storage and distribution point |
| **Mandatory routing** | Donations must go through the platform to a hub; donors can't choose a camp |
| **Stock movement** | A logbook entry for every stock change |

---

## 21. After Week 1 (Parts 3 and 4, outline only)

**Part 3 (75%)**
- **Demand forecasting (QRF)** with the `quantile-forest` library. Output: a range (for example, low–median–high). Open design decision: one model per item **or** one shared model with item type as a feature. Needs consumption data: real if DDMA has it, otherwise synthetic and clearly labelled.
- **Anomaly-aware triage:** compare an entered request with the forecast range; if unusual, ask the officer to explain (a note is saved). No accusation.
- **Hub-to-hub reallocation** using **PuLP** (a Transportation Problem) when one hub has surplus and another has shortage.

**Part 4 (100%)**
- **QR delivery confirmation** (jsQR) → allocation status `delivered`.
- **Monitoring dashboards.**
- **Offline resilience** (kept simple and realistic).
- Testing, documentation, report, and the final project title (the "geo-verified" part was dropped).

---

## 22. Change log

| Date | Who | Change | Approved by |
|---|---|---|---|
| (Day 0) | — | Guide v1.0 created | — |
|  |  |  |  |
|  |  |  |  |
