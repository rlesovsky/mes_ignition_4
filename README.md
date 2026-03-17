# MES Ignition 4.0

Industry 4.0 MES stack built on Ignition 8.3.2 with Docker, PostgreSQL, HiveMQ MQTT, TimeBase Historian, and Sparkplug B. Git-integrated for version-controlled development. Managed via Portainer.

## One-Command Deploy

```bash
git clone https://github.com/rlesovsky/mes_ignition_4.git
cd mes_ignition_4
cp .env.example .env    # Edit credentials
chmod +x scripts/*.sh
./scripts/mes-stack.sh deploy
```

This single command starts all infrastructure (Traefik + DNS), spins up the full MES stack (Ignition, Postgres, HiveMQ, TimeBase), waits for the gateway to be ready, auto-configures all database connections + historian providers + MQTT Transmission, seeds demo data, and triggers a project scan.

Gateway: `http://localhost:8088` or `http://ignition.mes.local`

## Ignition Projects

| Project | Parent | Description |
|---|---|---|
| **mes_core** | — (inheritable) | MES script libraries: OEE, run/state/count management, production model, UNS publishing |
| **mes_project** | mes_core | Perspective views: operations dashboard, work orders, admin, OEE/downtime templates |
| **i3x** | — | I3X REST API (Industrial Information Interface eXchange) |
| **CESMII** | — | CESMII SM Profile Converter for Ignition UDTs |

## What Gets Auto-Configured

### Databases (auto-provisioned on first start)

| Database | Connection | Tables |
|---|---|---|
| `mes_core` | `mes_core` | enterprise, site, area, line, cell, productcode, workorder, schedule, run, counttag, counttype, counthistory, statereason, statehistory |
| `mes_custom` | `mes_custom` | Client-specific (empty, ready for customization) |
| `odoo` | `odoo` | Odoo ERP integration (empty, ready for Odoo) |

### Gateway Connections (auto-configured via REST API)

| Resource | Type | Target |
|---|---|---|
| `mes_core` | DB Connection | `jdbc:postgresql://mes-postgres:5432/mes_core` |
| `mes_custom` | DB Connection | `jdbc:postgresql://mes-postgres:5432/mes_custom` |
| `odoo` | DB Connection | `jdbc:postgresql://mes-postgres:5432/odoo` |
| `mes_core` | SQL Historian | Monthly partitions on `mes_core` database |
| `mes_custom` | SQL Historian | Monthly partitions on `mes_custom` database |
| `timebase` | TimeBase Historian | `http://mes-timebase-historian:4511` |
| `HiveMQ` | MQTT Server | `tcp://mes-hivemq:1883` (Sparkplug B) |
| `Line1` | MQTT Transmitter | Group=`MES`, Edge Node=`Dallas`, Path=`Enterprise/Site/Area` |

### Demo Data (seeded automatically)

Equipment hierarchy (OF → Dallas → Production/Packaging/QC → Line 1/Line 2/Pack 1), product codes, count tags, state reasons (Running, Idle, Changeover, Machine Fault, etc.), and sample work orders.

## Stack Components

### Infrastructure

| Service | Port | URL |
|---|---|---|
| Traefik v3 | 80 | `traefik.infrastructure.local` |
| Technitium DNS | 5380 | `dns.infrastructure.local` |

### MES

| Service | Port | URL |
|---|---|---|
| Ignition 8.3.2 | 8088 | `ignition.mes.local` |
| PostgreSQL 15 | 5432 | — |
| PgAdmin 4 | 5050 | `pgadmin.mes.local` |
| HiveMQ 4 | 1883 | `hivemq.mes.local` |
| TimeBase Historian | 4511 | `historian.mes.local` |
| TimeBase Explorer | 4531 | `explorer.mes.local` |
| TimeBase MQTT Collector | 4521 | `collector.mes.local` |
| TimeBase Simulator | 4523 | `simulator.mes.local` |

## Scripts

| Command | Description |
|---|---|
| **`mes-stack.sh deploy`** | **Full deploy: up + configure + seed + scan** |
| `mes-stack.sh up` | Start infrastructure + MES stack |
| `mes-stack.sh down` | Stop MES stack (infra stays running) |
| `mes-stack.sh configure` | Auto-configure gateway connections |
| `mes-stack.sh status` | Show all container/DB/MQTT/infra status |
| `mes-stack.sh reset-db` | Rebuild databases from init-sql |
| `mes-stack.sh backup` | Download gateway backup |
| `mes-stack.sh scan` | Trigger project scan |
| `mes-stack.sh logs [svc]` | Tail logs |
| `mes-stack.sh infra-up/down` | Infrastructure control |
| `mes-stack.sh all-down` | Stop everything |
| `configure-gateway.sh` | Standalone gateway auto-config |
| `seed-demo-data.sh` | Insert demo equipment/products |
| `sync-from-backup.sh <path>` | Sync gateway config into repo |
| `clean-resource-json.sh` | Remove Designer timestamp noise |
| `portainer-deploy.sh` | Deploy stacks for Portainer |

## Portainer

Deploy via Portainer UI → Stacks → Add Stack → Repository → `https://github.com/rlesovsky/mes_ignition_4`. Or `./scripts/portainer-deploy.sh`.

## Git Workflow

```bash
# After making changes in Designer:
./scripts/clean-resource-json.sh --apply   # Remove timestamp noise
git add -A
git commit -m "feat: added new OEE dashboard view"
git push
```

## License

MIT
