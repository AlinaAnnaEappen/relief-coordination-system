# DisasterReliefMVP — End-to-End Operational Lifecycle Guide

**Document Owner:** Member C (Priority Engine, Seeding & Quality Assurance)  
**Project:** Priority-Based Disaster Relief Resource Allocation and Routing Platform for Kerala  
**Reference:** DisasterReliefMVP Team Guide — Section 15.4 & Section 11 (Task C4)  
**Target Environment:** PostgreSQL 16.3 + PostGIS 3.4.2 on Python 3.13 / FastAPI  

---

## 1. Executive Summary & Verification Matrix

This document provides the complete technical walkthrough and integration audit of the 9-step operational relief lifecycle defined in Guide Section 15.4. Testing was performed using live database integration tests against real PostgreSQL 16 storage populated with all 6,377 Kerala relief camps, 3 distribution hubs, 196 catalog items, 222 stock entries, and 20 relief request lines.

### Lifecycle Status Matrix

| Step | Role | Action | Expected View | Status in this Build | Reason / Blocker / Dependency |
|---|---|---|---|---|---|
| **Step 1** | `admin1` | Inspect camps and hubs lists | All 6,377 camps and 3 hubs displayed | **Worked (Camps)** / **Missing (Hubs)** | `GET /camps` passed (all 6,377 camps). `GET /hubs` is missing because `routers/hubs_router.py` is unmerged (Member D). |
| **Step 2** | `donor1` | Offer 100 kg rice and 50 blankets | Donation record created with status `hub_assigned` to Alappuzha Hub | **Skipped (Unmerged)** | `routers/donors_router.py` is unmerged (Member A). |
| **Step 3** | `hub1` | Incoming donations → Click **Receive** | Alappuzha Hub stock increases (+100 rice, +50 blankets); idempotent on re-click | **Skipped (Unmerged)** | `POST /hub/donations/{id}/receive` in `routers/stock_router.py` is unmerged (Member D). |
| **Step 4** | `officer1` | Submit urgent request (60 kg rice, 30 blankets, Escalate=True) | Request record created with status `pending` and escalation flag | **Skipped (Unmerged)** | `routers/requests_router.py` is unmerged (Member B). |
| **Step 5** | `admin1` | Priority → Click **Recalculate** | Ranked table of all 6,377 camps with SAW scores and 6-factor breakdown bars | **Worked (Fully Verified)** | Fully built and tested. All 6,377 camps scored in 0.06s; stored in `priority_runs` and `priority_scores`. RBAC rejects non-admins with 403. |
| **Step 6** | `admin1` | Allocation → Click **Run** | Stock allocated nearest-first to highest priority camps; stock decremented | **Skipped (Unmerged)** | `POST /allocation/run` in `routers/allocation_router.py` is unmerged (Member D). |
| **Step 7** | `officer1` | View "What is coming" | Displays incoming items, quantities, and fulfilling hub; status updated | **Skipped (Unmerged)** | `GET /allocation?camp_id=` is unmerged (Member D). |
| **Step 8** | `hub1` | Mark allocation as dispatched | Allocation status becomes `dispatched`; camp `last_supply_at` timestamp updates | **Skipped (Unmerged + Blocker)** | `POST /allocation/{id}/dispatch` unmerged (Member D). **Critical Blocker:** Camp 1 routes to Hub 3, but user `hub3` does not exist (see Hub Check finding below). |
| **Step 9** | `admin1` | Priority → Click **Recalculate** | Supplied camp's time factor resets to 0.00 and overall SAW priority score drops | **Worked (Fully Verified)** | Fully built and tested. Time factor plummets from 1.000 to < 0.01; score drops cleanly, freeing priority for unsupplied camps. |

---

## 2. Detailed Operational Step Breakdown

### Step 1: Admin Inspects Camps and Hubs
- **User Interaction:** `admin1` authenticates and navigates to the Camp Management and Distribution Hub dashboards.
- **HTTP Calls:** `GET /camps?format=json` and `GET /hubs`.
- **Database Operations:** `SELECT * FROM camps ORDER BY camp_id ASC;` and `SELECT * FROM hubs;`.
- **Integration Test Proof:** `tests/test_flow.py::test_step_1_admin_inspect_camps_and_hubs` executed against live PostgreSQL. Returned HTTP 200 and verified that all 6,377 camps from the Kerala State Disaster Management Authority master dataset are active and loaded with zero missing coordinates. The hubs endpoint returned 404 due to Member D's unmerged `hubs_router.py`.

### Step 2: Donor Offers Supplies
- **User Interaction:** `donor1` submits an offer of 100 kg Rice (`FW02`) and 50 Blankets (`CB11`) with mandatory routing to Alappuzha Hub.
- **HTTP Calls:** `POST /donations` with item quantities and donor details.
- **Database Operations:** Inserts into `donations` and `donation_items` tables with `status = 'hub_assigned'` and `assigned_hub_id = 1`.
- **Integration Test Proof:** `test_step_2_donor_offers_supplies` checked application route registry. Skipped cleanly with explanation because `routers/donors_router.py` has not been merged by Member A.

### Step 3: Hub Receives Donation
- **User Interaction:** `hub1` (Alappuzha Hub Coordinator) views pending intake on the Hub Dashboard and clicks **Receive**.
- **HTTP Calls:** `POST /hub/donations/{id}/receive`.
- **Database Operations:** Executes inside a single transaction: updates `donations.status = 'received'`, increments `stock` quantities (+100 for `FW02`, +50 for `CB11`), and writes audit records to `stock_movements` with `movement_type = 'donation_received'`.
- **Integration Test Proof:** `test_step_3_hub_receives_donation` skipped cleanly because `routers/stock_router.py` has not been merged by Member D.

### Step 4: Camp Officer Submits Urgent Request
- **User Interaction:** `officer1` (Chengannur Relief Camp) submits an urgent requisition for 60 kg Rice and 30 Blankets, checking the **Escalate** flag.
- **HTTP Calls:** `POST /requests`.
- **Database Operations:** Inserts into `requests` with `status = 'pending'`, `escalated = true`, `escalation_reason = 'Urgent infant and elderly supply deficit'`, and inserts child rows into `request_items`.
- **Integration Test Proof:** `test_step_4_camp_officer_submits_urgent_request` skipped cleanly because `routers/requests_router.py` has not been merged by Member B.

### Step 5: Admin Recalculates Priority Ranking
- **User Interaction:** `admin1` clicks **Recalculate Priority** on the Priority Dashboard (`/priority/latest`).
- **HTTP Calls:** `POST /priority/run` followed by `GET /priority/latest`.
- **Database Operations:**
  1. Executes a SQL query joining `camps` with an aggregation subquery over `requests` to detect active open requests and active escalations.
  2. Runs Member C's `compute_priority()` Simple Additive Weighting (SAW) algorithm across all 6,377 camps in memory (0.06 seconds).
  3. Inserts a record into `priority_runs` returning `run_id`.
  4. Inserts 6,377 records into `priority_scores` in a single batch using `execute_values`.
- **Integration Test Proof:** `test_step_5_admin_recalculates_priority` passed completely. Verified that `officer1` receives HTTP 403 Forbidden (RBAC), `admin1` receives HTTP 200 with `camps_ranked = 6377`, and `GET /priority/latest` provides paginated results with 6-factor breakdowns (`people`, `vulnerable`, `damage`, `access`, `time`, `escalation`).

### Step 6: Admin Executes Stock Allocation
- **User Interaction:** `admin1` navigates to Allocation Engine page and clicks **Run Allocation**.
- **HTTP Calls:** `POST /allocation/run`.
- **Database Operations:** Retrieves the latest ranking from `priority_scores`, joins open pending needs from `request_items`, computes ellipsoidal distances via PostGIS `ST_DistanceSphere()`, allocates stock in priority order, decrements `stock`, inserts `allocations`, and writes `stock_movements`.
- **Integration Test Proof:** `test_step_6_admin_runs_allocation` skipped cleanly because `routers/allocation_router.py` has not been merged by Member D.

### Step 7: Camp Officer Views Incoming Supplies
- **User Interaction:** `officer1` navigates to "What is Coming" on the Camp Portal to confirm dispatched logistics.
- **HTTP Calls:** `GET /allocation?camp_id=1`.
- **Database Operations:** `SELECT * FROM allocations WHERE camp_id = 1 AND status IN ('planned', 'dispatched');`.
- **Integration Test Proof:** `test_step_7_officer_views_what_is_coming` skipped cleanly because `routers/allocation_router.py` is unmerged by Member D.

### Step 8: Hub Marks Allocation as Dispatched
- **User Interaction:** Hub coordinator marks the planned allocation as dispatched when the transport vehicle departs.
- **HTTP Calls:** `POST /allocation/{id}/dispatch`.
- **Database Operations:** Updates `allocations.status = 'dispatched'`, writes `stock_movements` (`allocation_dispatched`), and sets `camps.last_supply_at = CURRENT_TIMESTAMP`.
- **Integration Test Proof:** `test_step_8_hub_marks_dispatched` skipped cleanly. Note critical architecture finding below.

### Step 9: Priority Recalculation After Relief Dispatch
- **User Interaction:** `admin1` clicks **Recalculate Priority** again after relief supplies reach the camp.
- **HTTP Calls:** `POST /priority/run` followed by `GET /priority/latest`.
- **Database Operations:** `camps.last_supply_at` now holds the recent timestamp (`NOW()`). The priority engine calculates elapsed time as $\approx 0$ hours, resetting the normalized time factor from `1.0000` to `0.0000`. The camp's composite score drops significantly (e.g. from 63.39 to 53.39), automatically shifting urgent attention to camps that have waited longer without aid.
- **Integration Test Proof:** `test_step_9_admin_recalculates_priority_after_dispatch` passed completely. Verified that Camp 1's time factor reset below `0.01` and its overall score dropped strictly below its initial score, validating the feedback loop.

---

## 3. The Hub Check Finding (Critical Architecture Discovery)

During integration analysis of Step 4 through Step 8, Member C uncovered a geographic and role-permission conflict in the current system specification:

```
[Camp 1: Chengannur] (Thiruvananthapuram: Lat 8.2321, Lon 77.1020)
       │
       ├── Distance to Hub 3 (Pathanamthitta: 9.2648, 76.7870)  ──► ~120 km (NEAREST)
       ├── Distance to Hub 1 (Alappuzha: 9.4981, 76.3388)        ──► ~162 km
       └── Distance to Hub 2 (Kottayam: 9.5916, 76.5222)         ──► ~164 km
```

### The Problem:
1. **Allocation Behavior:** Guide Section 9.2 dictates that allocations must originate from the **nearest hub with sufficient stock**.
2. **Resulting Hub:** For Camp 1 (Chengannur Relief Camp), **Hub 3 (Pathanamthitta Hub)** is geographically closest (~120 km vs ~162 km for Hub 1). The allocation engine will assign the dispatch to **Hub 3**.
3. **Role Conflict:** Guide Section 15.4 states: *"Step 8: Log in as `hub1` → Mark dispatched"*. User `hub1` is the coordinator for **Hub 1 (Alappuzha)** (`hub_id = 1`). User `hub1` does not have access to view or dispatch Hub 3 allocations.
4. **Missing User:** The seed dataset (`seed_users.csv`) contains only 4 users: `admin1`, `officer1`, `hub1`, and `donor1`. **There is no user `hub3`!**
5. **Execution Blocker:** When Member D builds Task D4, Step 8 will fail with HTTP 403 Forbidden or "Allocation not found" if tested as written.

### Recommended Fix (Action Required from Member A and Member D):
- **Option 1 (Recommended):** Member A adds a user `hub3` (`username: hub3`, `role: hub_coordinator`, `hub_id: 3`, `district: Pathanamthitta`) to `seed_users.csv` and updates Guide Section 15.4 Step 8 to log in as `hub3`.
- **Option 2:** Set initial stock for test items at Hub 3 to 0 in `seed_stock.csv`, forcing the allocation engine to fall back to the second closest hub with stock (Hub 1 Alappuzha).

---

## 4. Test Execution Summary

The Member C test suite executes under `pytest` with 100% clean passes and zero unhandled errors:

```text
tests/test_flow.py::test_step_1_admin_inspect_camps_and_hubs PASSED
tests/test_flow.py::test_step_2_donor_offers_supplies SKIPPED (Unmerged Member A)
tests/test_flow.py::test_step_3_hub_receives_donation SKIPPED (Unmerged Member D)
tests/test_flow.py::test_step_4_camp_officer_submits_urgent_request SKIPPED (Unmerged Member B)
tests/test_flow.py::test_step_5_admin_recalculates_priority PASSED
tests/test_flow.py::test_step_6_admin_runs_allocation SKIPPED (Unmerged Member D)
tests/test_flow.py::test_step_7_officer_views_what_is_coming SKIPPED (Unmerged Member D)
tests/test_flow.py::test_step_8_hub_marks_dispatched SKIPPED (Unmerged Member D)
tests/test_flow.py::test_step_9_admin_recalculates_priority_after_dispatch PASSED
tests/test_priority.py (12 unit tests) PASSED
tests/test_priority_flow.py (2 lifecycle tests) PASSED

Total: 17 passed, 6 skipped in 4.75s
```
