#!/bin/bash
# =============================================================================
# 05_init_extra_databases.sh
# =============================================================================
# Initializes mes_custom and odoo databases with extensions and grants.
# This runs as a shell script because PostgreSQL Docker init scripts (.sql)
# can only connect to the default POSTGRES_DB. Cross-database connections
# require a shell wrapper that calls psql with --dbname.
# =============================================================================

set -e

echo "Initializing mes_custom database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "mes_custom" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

echo "Initializing odoo database..."
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "odoo" <<-EOSQL
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
EOSQL

# Grant readonly access if the role exists
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "mes_custom" <<-EOSQL
    DO \$\$
    BEGIN
        IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mes_readonly') THEN
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mes_readonly;
            RAISE NOTICE 'mes_custom: readonly grants applied';
        END IF;
    END
    \$\$;
EOSQL

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "odoo" <<-EOSQL
    DO \$\$
    BEGIN
        IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'mes_readonly') THEN
            ALTER DEFAULT PRIVILEGES IN SCHEMA public GRANT SELECT ON TABLES TO mes_readonly;
            RAISE NOTICE 'odoo: readonly grants applied';
        END IF;
    END
    \$\$;
EOSQL

echo "============================================"
echo "Extra databases initialized:"
echo "  - mes_custom (uuid-ossp, readonly grants)"
echo "  - odoo       (uuid-ossp, readonly grants)"
echo "============================================"
