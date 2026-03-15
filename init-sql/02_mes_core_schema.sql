-- =============================================================================
-- 02_mes_core_schema.sql
-- =============================================================================
-- MES Core database schema — matches the 4.0 Solutions mes_core script library.
-- ISA-95 equipment hierarchy: enterprise → site → area → line → cell
-- Production tracking: workorder, schedule, run, counthistory, statehistory
-- =============================================================================

CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";

-- ============================================
-- ISA-95 Equipment Model
-- ============================================

CREATE TABLE IF NOT EXISTS enterprise (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(128) NOT NULL UNIQUE,
    description     TEXT,
    disable         BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS site (
    id              SERIAL PRIMARY KEY,
    parentid        INTEGER      NOT NULL REFERENCES enterprise(id),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    disable         BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parentid, name)
);

CREATE TABLE IF NOT EXISTS area (
    id              SERIAL PRIMARY KEY,
    parentid        INTEGER      NOT NULL REFERENCES site(id),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    disable         BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parentid, name)
);

CREATE TABLE IF NOT EXISTS line (
    id              SERIAL PRIMARY KEY,
    parentid        INTEGER      NOT NULL REFERENCES area(id),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    disable         BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parentid, name)
);

CREATE TABLE IF NOT EXISTS cell (
    id              SERIAL PRIMARY KEY,
    parentid        INTEGER      NOT NULL REFERENCES line(id),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    disable         BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parentid, name)
);

-- ============================================
-- Product & Work Order Management
-- ============================================

CREATE TABLE IF NOT EXISTS productcode (
    id              SERIAL PRIMARY KEY,
    productcode     VARCHAR(128) NOT NULL UNIQUE,
    description     TEXT,
    disable         BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS productcodeline (
    id              SERIAL PRIMARY KEY,
    productcodeid   INTEGER      NOT NULL REFERENCES productcode(id),
    lineid          INTEGER      NOT NULL REFERENCES line(id),
    enable          BOOLEAN      NOT NULL DEFAULT TRUE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (productcodeid, lineid)
);

CREATE TABLE IF NOT EXISTS workorder (
    id              SERIAL PRIMARY KEY,
    workorder       VARCHAR(128) NOT NULL UNIQUE,
    productcodeid   INTEGER      REFERENCES productcode(id),
    productcode     VARCHAR(128),
    quantity        NUMERIC(12,3) NOT NULL DEFAULT 0,
    closed          BOOLEAN      NOT NULL DEFAULT FALSE,
    hide            BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

-- ============================================
-- Schedule & Run Management
-- ============================================

CREATE TABLE IF NOT EXISTS schedule (
    id              SERIAL PRIMARY KEY,
    workorderid     INTEGER      REFERENCES workorder(id),
    lineid          INTEGER      REFERENCES line(id),
    quantity        NUMERIC(12,3),
    schedulestartdatetime   TIMESTAMPTZ,
    schedulefinishdatetime  TIMESTAMPTZ,
    sequence        INTEGER,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS run (
    id              SERIAL PRIMARY KEY,
    scheduleid      INTEGER      REFERENCES schedule(id),
    runstartdatetime    TIMESTAMPTZ,
    runstopdatetime     TIMESTAMPTZ,
    startinfeed         NUMERIC(12,3) DEFAULT 0,
    startoutfeed        NUMERIC(12,3) DEFAULT 0,
    currentinfeed       NUMERIC(12,3) DEFAULT 0,
    currentoutfeed      NUMERIC(12,3) DEFAULT 0,
    startwaste          NUMERIC(12,3) DEFAULT 0,
    currentwaste        NUMERIC(12,3) DEFAULT 0,
    totalcount          NUMERIC(12,3) DEFAULT 0,
    wastecount          NUMERIC(12,3) DEFAULT 0,
    goodcount           NUMERIC(12,3) DEFAULT 0,
    availability        DOUBLE PRECISION DEFAULT 0,
    performance         DOUBLE PRECISION DEFAULT 0,
    quality             DOUBLE PRECISION DEFAULT 0,
    oee                 DOUBLE PRECISION DEFAULT 0,
    runtime             DOUBLE PRECISION DEFAULT 0,
    unplanneddowntime   DOUBLE PRECISION DEFAULT 0,
    planneddowntime     DOUBLE PRECISION DEFAULT 0,
    totaltime           DOUBLE PRECISION DEFAULT 0,
    estimatedfinishtime TIMESTAMPTZ,
    closed              BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"         TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_run_schedule ON run (scheduleid);
CREATE INDEX IF NOT EXISTS idx_run_closed ON run (closed) WHERE closed = FALSE;

-- ============================================
-- Count Tracking
-- ============================================

CREATE TABLE IF NOT EXISTS counttag (
    id              SERIAL PRIMARY KEY,
    parentid        INTEGER      NOT NULL REFERENCES line(id),
    name            VARCHAR(128) NOT NULL,
    description     TEXT,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS counttype (
    id              SERIAL PRIMARY KEY,
    name            VARCHAR(64)  NOT NULL UNIQUE,
    description     TEXT
);

-- Seed default count types (referenced by OEE library: 2=Good/Outfeed, 3=Waste)
INSERT INTO counttype (id, name, description) VALUES
    (1, 'Infeed',  'Input count'),
    (2, 'Outfeed', 'Good output count'),
    (3, 'Waste',   'Reject / waste count')
ON CONFLICT (id) DO NOTHING;

SELECT setval('counttype_id_seq', (SELECT MAX(id) FROM counttype));

CREATE TABLE IF NOT EXISTS counthistory (
    id              BIGSERIAL PRIMARY KEY,
    tagid           INTEGER      NOT NULL REFERENCES counttag(id),
    counttypeid     INTEGER      NOT NULL REFERENCES counttype(id),
    count           INTEGER      NOT NULL DEFAULT 0,
    runid           INTEGER,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS idx_counthistory_tag_type ON counthistory (tagid, counttypeid);
CREATE INDEX IF NOT EXISTS idx_counthistory_run ON counthistory (runid) WHERE runid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_counthistory_ts ON counthistory ("TimeStamp");

-- ============================================
-- State / Downtime Tracking
-- ============================================

CREATE TABLE IF NOT EXISTS statereason (
    id              SERIAL PRIMARY KEY,
    parentid        INTEGER      NOT NULL REFERENCES line(id),
    reasoncode      INTEGER      NOT NULL,
    reasonname      VARCHAR(128) NOT NULL,
    description     TEXT,
    recorddowntime  BOOLEAN      NOT NULL DEFAULT FALSE,
    planneddowntime BOOLEAN      NOT NULL DEFAULT FALSE,
    "TimeStamp"     TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (parentid, reasoncode)
);

CREATE TABLE IF NOT EXISTS statehistory (
    id              BIGSERIAL PRIMARY KEY,
    statereasonid   INTEGER      REFERENCES statereason(id),
    reasonname      VARCHAR(128),
    lineid          INTEGER      NOT NULL REFERENCES line(id),
    reasoncode      INTEGER,
    runid           INTEGER,
    startdatetime   TIMESTAMPTZ  NOT NULL DEFAULT CURRENT_TIMESTAMP,
    enddatetime     TIMESTAMPTZ
);

CREATE INDEX IF NOT EXISTS idx_statehistory_line ON statehistory (lineid);
CREATE INDEX IF NOT EXISTS idx_statehistory_run ON statehistory (runid) WHERE runid IS NOT NULL;
CREATE INDEX IF NOT EXISTS idx_statehistory_open ON statehistory (lineid) WHERE enddatetime IS NULL;

-- ============================================
-- Read-only grants
-- ============================================
GRANT SELECT ON ALL TABLES IN SCHEMA public TO mes_readonly;
ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mes_readonly;

DO $$
BEGIN
    RAISE NOTICE 'mes_core schema created successfully.';
END
$$;
