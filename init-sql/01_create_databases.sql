-- =============================================================================
-- 01_create_databases.sql
-- =============================================================================
-- Creates all databases and roles used by the MES Ignition gateway.
-- Matches the actual gateway database connections:
--   mes_core   - Main MES application database (default, created by env var)
--   mes_custom - Custom/client-specific tables
--   odoo       - Odoo ERP integration database
--
-- PostgreSQL only runs init scripts when the data volume is EMPTY.
-- To re-run: docker compose down -v (destroys all data!) then up.
-- =============================================================================

-- mes_core is created automatically by POSTGRES_DB env var.
-- Create the additional databases:

CREATE DATABASE mes_custom
    OWNER mes_user
    ENCODING 'UTF8'
    LC_COLLATE 'en_US.utf8'
    LC_CTYPE 'en_US.utf8';

CREATE DATABASE odoo
    OWNER mes_user
    ENCODING 'UTF8'
    LC_COLLATE 'en_US.utf8'
    LC_CTYPE 'en_US.utf8';

-- ============================================
-- Read-only role for reporting/dashboards
-- ============================================
DO $$
BEGIN
    IF NOT EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mes_readonly') THEN
        CREATE ROLE mes_readonly LOGIN PASSWORD 'ReadOnly123';
    END IF;
END
$$;

GRANT CONNECT ON DATABASE mes_core TO mes_readonly;
GRANT CONNECT ON DATABASE mes_custom TO mes_readonly;
GRANT CONNECT ON DATABASE odoo TO mes_readonly;

DO $$
BEGIN
    RAISE NOTICE '============================================';
    RAISE NOTICE 'MES databases created:';
    RAISE NOTICE '  - mes_core   (main MES / OEE / runs)';
    RAISE NOTICE '  - mes_custom (client customizations)';
    RAISE NOTICE '  - odoo       (ERP integration)';
    RAISE NOTICE '  - mes_readonly role for reporting';
    RAISE NOTICE '============================================';
END
$$;
