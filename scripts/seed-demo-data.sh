#!/usr/bin/env bash
# =============================================================================
# seed-demo-data.sh - Insert demo equipment hierarchy, products, state reasons
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; source .env; set +a; fi

PG_USER="${POSTGRES_USER:-mes_user}"
PG_DB="${POSTGRES_DB:-mes_core}"

echo "Seeding demo data into ${PG_DB}..."

docker compose exec -T postgres psql -U "$PG_USER" -d "$PG_DB" <<'EOSQL'
INSERT INTO enterprise (name, description) VALUES
    ('OF', '4.0 Solutions Enterprise')
ON CONFLICT (name) DO NOTHING;

INSERT INTO site (parentid, name, description)
SELECT e.id, s.name, s.desc
FROM enterprise e
CROSS JOIN (VALUES ('Dallas', 'Dallas Manufacturing Site'), ('Atlanta', 'Atlanta Distribution Center')) AS s(name, desc)
WHERE e.name = 'OF'
ON CONFLICT (parentid, name) DO NOTHING;

INSERT INTO area (parentid, name, description)
SELECT s.id, a.name, a.desc
FROM site s JOIN enterprise e ON s.parentid = e.id
CROSS JOIN (VALUES ('Dallas','Production','Main production area'),('Dallas','Packaging','Packaging and shipping'),('Dallas','QC','Quality control lab')) AS a(site_name, name, desc)
WHERE e.name = 'OF' AND s.name = a.site_name
ON CONFLICT (parentid, name) DO NOTHING;

INSERT INTO line (parentid, name, description)
SELECT a.id, l.name, l.desc
FROM area a JOIN site s ON a.parentid = s.id JOIN enterprise e ON s.parentid = e.id
CROSS JOIN (VALUES ('Dallas','Production','Line 1','Assembly Line 1'),('Dallas','Production','Line 2','Assembly Line 2'),('Dallas','Packaging','Pack 1','Packaging Line 1')) AS l(site_name, area_name, name, desc)
WHERE e.name = 'OF' AND s.name = l.site_name AND a.name = l.area_name
ON CONFLICT (parentid, name) DO NOTHING;

INSERT INTO productcode (productcode, description) VALUES
    ('WIDGET-STD','Standard Widget'),('WIDGET-PRO','Premium Widget'),('WIDGET-MINI','Mini Widget')
ON CONFLICT (productcode) DO NOTHING;

INSERT INTO counttag (parentid, name)
SELECT l.id, ct.name FROM line l JOIN area a ON l.parentid = a.id JOIN site s ON a.parentid = s.id JOIN enterprise e ON s.parentid = e.id
CROSS JOIN (VALUES ('Line 1','Infeed Counter'),('Line 1','Outfeed Counter'),('Line 1','Waste Counter'),('Line 2','Infeed Counter'),('Line 2','Outfeed Counter'),('Line 2','Waste Counter')) AS ct(line_name, name)
WHERE e.name = 'OF' AND l.name = ct.line_name
ON CONFLICT DO NOTHING;

INSERT INTO statereason (parentid, reasoncode, reasonname, recorddowntime, planneddowntime)
SELECT l.id, sr.code, sr.name, sr.record_dt, sr.planned_dt
FROM line l JOIN area a ON l.parentid = a.id JOIN site s ON a.parentid = s.id JOIN enterprise e ON s.parentid = e.id
CROSS JOIN (VALUES (0,'Running',FALSE,FALSE),(1,'Idle',FALSE,FALSE),(10,'Changeover',TRUE,TRUE),(11,'Scheduled Break',TRUE,TRUE),(12,'Planned Maintenance',TRUE,TRUE),(20,'Machine Fault',TRUE,FALSE),(21,'Material Shortage',TRUE,FALSE),(22,'Quality Hold',TRUE,FALSE),(30,'No Order',FALSE,FALSE)) AS sr(code, name, record_dt, planned_dt)
WHERE e.name = 'OF' AND l.name IN ('Line 1', 'Line 2', 'Pack 1')
ON CONFLICT (parentid, reasoncode) DO NOTHING;

INSERT INTO workorder (workorder, productcodeid, productcode, quantity)
SELECT wo.wo_num, pc.id, pc.productcode, wo.qty
FROM (VALUES ('WO-2026-0001','WIDGET-STD',500),('WO-2026-0002','WIDGET-PRO',250)) AS wo(wo_num, pc_code, qty)
JOIN productcode pc ON pc.productcode = wo.pc_code
ON CONFLICT (workorder) DO NOTHING;

DO $$ BEGIN RAISE NOTICE 'Demo data seeded successfully!'; END $$;
EOSQL

echo "Done!"
