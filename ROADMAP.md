# 4-Week Project Implementation Roadmap
## A Priority-Based Disaster Relief Resource Allocation & Distribution System

**Target Timeline:** 4 Weeks (1 Month)  
**Team Size:** 4 Members (Alina, Athira, Sreya, Nair Ardra)  
**Project Guide:** Reshma Raj K S  
**Stack:** Python/Flask, MySQL, React/Vite (PWA) or Vanilla JS PWA, Scikit-Learn/Quantile-Forest, PuLP/SciPy, HTML5/CSS3

---

### Project Architecture & Role Breakdown

```
                             [ Statewide Admin / Collector Dashboard ]
                                              │
                    ┌─────────────────────────┴─────────────────────────┐
                    ▼                                                   ▼
       [ Tahsildar (Taluk Level) ]                         [ LSG Hub Coordinators ]
                    │                                                   │
                    ▼                                                   ▼
       [ Village Officer & Camp Officer ]                  [ Hub Inventory & Transit ]
                    │                                                   ▲
                    └───────────► [ SAW Priority Engine ] ──────────────┘
                                  [ QRF Demand Predictor ]
                                  [ Transportation Solver ]
                                              ▲
                                              │
                                   [ Public Donor Portal ]
```

---

## 4-Week Milestone Overview

| Phase | Duration | Primary Focus | Key Deliverables |
|:---|:---|:---|:---|
| **Phase 1** | Week 1 (Days 1–7) | **Foundation, Schema & Core Engines** | Database Schema, Auth (SPARK mock + JWT), SAW Engine, QRF baseline model |
| **Phase 2** | Week 2 (Days 8–14) | **Field Officer Modules & Camp Intake** | Camp Assessment (Parts A/B), QRF auto-fill & anomaly checks, Emergency override |
| **Phase 3** | Week 3 (Days 15–21) | **Logistics, LP Solver & QR Verification** | Transportation LP solver, Hub intake/net position, Dual-stage QR generation/scanning |
| **Phase 4** | Week 4 (Days 22–30) | **Donor Portal, PWA Offline, Testing & Defense** | 3-tier donor portal, PWA offline sync & fallback codes, System testing & viva prep |

---

## Detailed Week-by-Week & Day-by-Day Roadmap

### Phase 1: Foundation, DB Architecture & Core Engines (Days 1 – 7)

#### Objective
Establish the project repository, relational database in MySQL, authentication system with Kerala administrative scoping, and the mathematical core (SAW and QRF).

#### Day-by-Day Breakdown
* **Day 1: Project Scaffolding & Setup**
  - Set up Git repository with branch protection (`main`, `dev`, feature branches).
  - Initialize Flask backend project structure (`/api`, `/models`, `/services`, `/algorithms`, `/utils`).
  - Initialize PWA frontend project (Modern responsive UI structure with service worker setup).
  - Configure environment variables and database connection pools.

* **Day 2: Relational Database Schema Design (MySQL)**
  - Tables: `users` (SPARK PEN, phone, role, scope_id), `administrative_units` (districts, taluks, villages, panchayats).
  - Tables: `item_catalog` (vitality scores 2–10, Sphere categories), `camps`, `camp_assessments` (Part A & B).
  - Tables: `camp_requirements` (quantities, status: Draft, Submitted, Pledged, Fulfilled, SAW scores).
  - Tables: `hubs`, `hub_inventory`, `transfer_orders` (LP recommendations, approval flags, QR payloads).
  - Seed Kerala geographic master data (e.g., Alappuzha, Ernakulam, Wayanad taluks/villages/hubs).

* **Day 3: Authentication & RBAC (FR-1, FR-2)**
  - Implement JWT authentication with role claims and geographic scopes (`district_id`, `taluk_id`, `camp_id`, `hub_id`).
  - Implement SPARK PEN validation service (mock Kerala SPARK database with admin bypass).
  - Role decorators: `@require_role(['camp_officer', 'tahsildar', 'hub_coordinator', 'district_admin'])`.

* **Day 4: Master Item Catalog & Sphere Standards (FR-3)**
  - Fixed categories: Medical, Water, Food, Shelter, Clothing, Household.
  - CRUD & seeding of standard relief items with assigned Sphere Vitality scores (2 to 10).
  - Prevent ad-hoc free-text entries via standardized item dropdowns.

* **Day 5: SAW Multi-Criteria Decision Making Engine (FR-5, Appendix A)**
  - Implement SAW formula in Python:
    $$\text{Score} = (I_{\text{vitality}} \times W_{\text{item}}) + (D_{\text{score}} \times W_{\text{damage}}) + (V_{\text{ratio}} \times 10 \times W_{\text{vuln}}) + (T_{\text{score}} \times W_{\text{time}})$$
  - Unit tests to guarantee sub-500ms execution on priority recalculation.

* **Day 6: QRF Dataset Synthesis & Model Training (FR-7, Appendix A)**
  - Generate realistic Kerala flood training data (camp size, vulnerability split, damage severity, days active, actual consumption).
  - Train Quantile Regression Forest (`quantile-forest` or scikit-learn GradientBoostingRegressor with quantile loss) for 10th, 50th, and 90th percentiles.
  - Save serialized pipeline models (`qrf_models.joblib`).

* **Day 7: Phase 1 Review & Integration Test**
  - Verify JWT scope containment.
  - Verify SAW priority output against reference test cases.
  - Test QRF prediction endpoints with sample camp demographics.

---

### Phase 2: Camp Operations, Assessments & Anomaly Detection (Days 8 – 14)

#### Objective
Build the field officer workflow for relief camp damage assessment, automated requirement generation, anomaly validation, and emergency escalations.

#### Day-by-Day Breakdown
* **Day 8: Factual Damage Assessment Module (FR-4)**
  - Implement assessment forms:
    - **Part A (Human Impact):** Camp population, elderly count, children under 5, pregnant/lactating mothers, chronic illness count.
    - **Part B (Infrastructure Severity):** Access road status (flooded/cut-off/accessible), power outage status, clean water source status.
  - Auto-calculate Damage Tier score: 2 (Mild), 6 (Moderate), 10 (Severe/Cut-off).

* **Day 9: QRF Requirement Auto-Fill (FR-7)**
  - Backend endpoint `/api/camps/<id>/suggest-demand` integrating trained QRF models.
  - Auto-populate item request inputs with the median predicted demand ($q_{50}$).
  - Display confidence range ($q_{10} - q_{90}$) visually on the officer interface.

* **Day 10: Anomaly Detection & Range Validation (FR-8)**
  - Validate entered quantities against predicted confidence bounds.
  - If requested quantity $> q_{90}$ or $< q_{10}$, flag as anomaly.
  - UI enforcement: Require mandatory justification remarks before the submission can be submitted.

* **Day 11: Emergency Override Button (FR-6)**
  - Pre-approved critical medical item list (insulin, oxygen cylinders, dialysis kits, antivenom).
  - Emergency toggle button that bypasses the normal SAW scoring loop.
  - Instantly pins request to Global Rank 1 and logs instant notification events.

* **Day 12: Camp Officer & Village Officer Dashboard UI**
  - High-contrast, clean emergency-zone responsive UI.
  - Camp Officer view: Enter daily status, log new needs, check fulfillment status.
  - Village Officer view: Review, verify, and optionally override camp submissions across their revenue village.

* **Day 13: Live Requirement Feed & Status State Machine (FR-2.3, FR-4.1)**
  - Implement system states: `Draft` $\rightarrow$ `Submitted/Verified` $\rightarrow$ `Pledged` $\rightarrow$ `In Transit` $\rightarrow$ `Fulfilled`.
  - Trigger SAW score calculation upon village officer approval and push to active needs pool.

* **Day 14: Phase 2 Code Freeze & Milestone Testing**
  - End-to-end camp request walkthrough: Camp Officer fills Part A/B $\rightarrow$ QRF pre-fills $\rightarrow$ Anomaly warning triggered and overridden with comment $\rightarrow$ SAW score assigned.

---

### Phase 3: Hub Operations, LP Transportation Solver & QR Verification (Days 15 – 21)

#### Objective
Implement the logistics brain of the system: inter-hub net position balancing using Linear Programming, Tahsildar/Collector approvals, and dual-stage QR tracking.

#### Day-by-Day Breakdown
* **Day 15: Hub Inventory & Net Position Engine (FR-10)**
  - Grama Panchayat / Municipality hub intake recording.
  - Real-time calculation:
    $$\text{Net Position} = \text{Current Stock} - \text{Total Forecasted Need in Covered Camps}$$
  - Classify hubs into Surplus ($\text{Net} > 0$) and Deficit ($\text{Net} < 0$).

* **Day 16: Classical LP Transportation Solver (FR-11, Appendix A)**
  - Implement PuLP / SciPy solver:
    $$\text{Minimize } Z = \sum_{i} \sum_{j} (\text{Distance}_{ij} \times \text{Quantity}_{ij})$$
  - Subject to:
    - $\sum_j \text{Quantity}_{ij} \le \text{Surplus}_i$
    - $\sum_i \text{Quantity}_{ij} \ge \text{Deficit}_j$
  - Compute distance matrix using Kerala coordinates (Haversine distance or road distance matrix).
  - Ensure solution time is within $< 3$ seconds.

* **Day 17: Administrative Transfer Approval Hierarchy (FR-11, Section 1.5)**
  - System generates proposed redistribution transfer orders.
  - Intra-taluk transfer proposal sent to **Tahsildar dashboard** for 1-click approval.
  - Inter-taluk transfer proposal sent to **District Collector dashboard** for authorization.
  - Ensure transfers cannot execute automatically without official sign-off.

* **Day 18: Dual-Stage QR Code Generation Engine (FR-12)**
  - Secure QR payload generation (encrypted/signed HMAC token containing order ID, item, quantity, source, target).
  - **Stage 1 QR:** Generated when public donor or drop-off pledges to a hub/camp.
  - **Stage 2 QR:** Generated upon transit dispatch between hubs or hub-to-camp.
  - Fallback mechanism: Generate human-readable 6 to 8-character alphanumeric code (e.g., `KL-AL-7890`).

* **Day 19: QR Scanner & Inventory Reconciliation Module**
  - Integrate in-browser HTML5 camera QR scanner (`html5-qrcode` library) in PWA.
  - Scanning Stage 1 QR at hub intake: Verifies donor pledge, increments hub inventory.
  - Scanning Stage 2 QR at destination camp: Verifies manifest, decrements transit inventory, marks camp requirement as `Fulfilled`.

* **Day 20: Tahsildar & Hub Coordinator Dashboards**
  - Tahsildar view: Taluk map, hub stock balances, pending transfer approvals, bottleneck alerts.
  - Hub Coordinator view: Inventory manager, QR scan receiver, outgoing dispatch list.

* **Day 21: Phase 3 Integration & Stress Testing**
  - Test 10 surplus hubs and 15 deficit hubs through the LP solver. Verify solver runtime and feasibility.
  - Test QR generation $\rightarrow$ camera scan $\rightarrow$ inventory balance updates.

---

### Phase 4: Donor Portal, PWA Offline, Final Polish & Defense Prep (Days 22 – 30)

#### Objective
Build the public-facing donor interface with 3-tier geographic visibility, finalize PWA offline capabilities, perform end-to-end testing, and prepare documentation/demonstration.

#### Day-by-Day Breakdown
* **Day 22: Three-Tier Donor Management Portal (FR-9)**
  - Donor landing page with distance/location detection:
    - **Local Donors (< 15 km):** Directly view nearby camp-level urgent requirements (drops directly to camp).
    - **Regional Donors (15 – 60 km):** Routed to active Panchayat collection hubs.
    - **Statewide Donors (> 60 km / Out of District):** View aggregated district rollup priorities.
  - Pledge workflow: Donor chooses items $\rightarrow$ generates Stage 1 QR code + alphanumeric pickup code $\rightarrow$ donor privacy protected (no personal details leaked).

* **Day 23: PWA Offline Capabilities & Caching (FR-12, Section 1.4)**
  - Service Worker implementation (cache core assets, forms, static catalogs).
  - IndexedDB / LocalStorage queue for Camp Officers: Store offline damage assessments & requests.
  - Auto-sync pipeline: Sync locally stored forms within 5 seconds of network restoration.

* **Day 24: SMS / Low-Connectivity Fallback Simulation (FR-1.3.2, FR-5.3)**
  - Mock/simulated SMS ingestion endpoint (`POST /api/sms/inbound`) accepting structured syntax:
    `REQ <CAMP_ID> <ITEM_CODE> <QTY> <URGENCY>`
  - Fallback lookup screen for hub coordinators to verify drop-offs by phone number or alphanumeric code.

* **Day 25: District Administrator / Executive Dashboard (FR-11)**
  - High-level district overview: Total displaced population, active camps, critical shortages, transit movements.
  - Heatmap of priority scores across taluks.
  - Audit logging for all actions and approvals.

* **Day 26: Performance Optimization & Non-Functional Validation (Section 5)**
  - Benchmark SAW calculations ($< 500\text{ms}$).
  - Benchmark QR scan verification ($< 2\text{s}$).
  - Benchmark LP optimization resolution ($< 3\text{s}$).
  - Security audit: Test JWT RBAC boundary violations (e.g. Camp Officer attempting taluk-level queries).

* **Day 27: Comprehensive End-to-End Simulation**
  - Simulate a complete disaster scenario (e.g., Alappuzha Flood Event):
    1. Disaster event triggered $\rightarrow$ Camps registered.
    2. Camp Officers report damage (Part A & B) $\rightarrow$ QRF suggests items $\rightarrow$ SAW ranks needs.
    3. Emergency button triggered for insulin $\rightarrow$ Rank 1 alert displayed.
    4. Donors pledge items using 3-tier view $\rightarrow$ Stage 1 QR scanned at Hub.
    5. Net positions calculated $\rightarrow$ LP solver proposes inter-hub transfer $\rightarrow$ Tahsildar approves.
    6. Stage 2 Transit QR dispatched and scanned at Camp $\rightarrow$ Need fulfilled.

* **Day 28: Project Report, Viva Presentation & Demo Script**
  - Prepare final project documentation matching SRS format.
  - Create presentation slides covering: Problem statement, Mathematical Models (SAW, QRF, LP), System Architecture, Live Demo flow, Results.
  - Record a backup video demonstration of the live system.

* **Days 29–30: Final Code Cleanup, Bug Fixes & Dry Run**
  - Final git tags, code commenting, and Dockerfile / local startup scripts.
  - Mock viva presentation and question-answer rehearsal with guide/team.

---

## Team Work Division (4 Members)

To complete the project in 30 days, tasks must run in parallel across the 4 members:

| Member | Primary Ownership | Core Responsibilities |
|:---|:---|:---|
| **Member 1 (Alina)** | **Backend Architecture & Auth** | Flask REST APIs, MySQL schema, JWT RBAC, SPARK integration, audit logs. |
| **Member 2 (Athira)** | **AI & Optimization Algorithms** | SAW priority engine, QRF synthetic dataset & ML training, PuLP transportation LP solver. |
| **Member 3 (Sreya)** | **PWA Frontend & Field UI** | High-contrast PWA interface, Camp Officer Part A/B forms, Tahsildar/Admin dashboards, offline sync. |
| **Member 4 (Nair Ardra)** | **Logistics, QR Engine & Donor Portal**| 3-Tier Donor portal, Dual-Stage QR generator/scanner, SMS fallback simulator, test scripts. |

---

## Risk Management & Fallback Strategies

| Potential Risk | Severity | Mitigation Strategy |
|:---|:---|:---|
| **Real SPARK API unavailable** | High | Built-in mock SPARK identity verification with pre-seeded PEN numbers and bypass toggle. |
| **QRF training data scarcity** | Medium | Use parametric synthetic data generator based on Sphere Humanitarian Standards and past Kerala flood reports. |
| **LP Solver complexity for large matrices** | Medium | Scope initial optimization to Taluk-level clusters; statewide transfers handled at aggregated hub level. |
| **PWA Camera QR scan issues across devices** | Low | Implement robust HTML5 camera scanner with instant fallback to 6-character alphanumeric code entry. |
| **Network failure during viva demo** | Medium | Full local offline capability (Docker / localhost MySQL) with pre-loaded mock scenarios. |
