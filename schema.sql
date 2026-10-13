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
  group_code         TEXT NOT NULL CHECK (group_code IN ('FW','CB','SH','MF','KU','SU','SG','CA','SS','WI','PR','LV','RC','TL')),
  group_kind         TEXT NOT NULL CHECK (group_kind IN ('core','extended')),
  unit               TEXT NOT NULL,
  item_type          TEXT NOT NULL CHECK (item_type IN ('Consumable','Durable','Infrastructure','Service')),
  perishable         TEXT NOT NULL DEFAULT 'No' CHECK (perishable IN ('No','Yes','Semi')),
  requires_approval  TEXT NOT NULL DEFAULT 'No' CHECK (requires_approval IN ('No','Yes')),
  emergency_eligible BOOLEAN NOT NULL DEFAULT FALSE,
  notes              TEXT,
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
