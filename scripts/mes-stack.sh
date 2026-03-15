#!/usr/bin/env bash
# =============================================================================
# mes-stack.sh - MES Ignition 4.0 Stack Manager
# =============================================================================
# Usage:
#   ./scripts/mes-stack.sh up          Start infrastructure + MES stack
#   ./scripts/mes-stack.sh down        Stop MES stack (infra stays up)
#   ./scripts/mes-stack.sh restart     Restart MES stack
#   ./scripts/mes-stack.sh configure   Auto-configure gateway (DB, MQTT, historian)
#   ./scripts/mes-stack.sh deploy      Full deploy: up + configure + seed
#   ./scripts/mes-stack.sh reset-db    Destroy and rebuild all databases
#   ./scripts/mes-stack.sh status      Show all container/DB/MQTT status
#   ./scripts/mes-stack.sh logs [svc]  Tail logs (all or specific service)
#   ./scripts/mes-stack.sh backup      Download gateway backup
#   ./scripts/mes-stack.sh scan        Trigger Ignition project scan
#   ./scripts/mes-stack.sh infra-up    Start only infrastructure (Traefik+DNS)
#   ./scripts/mes-stack.sh infra-down  Stop infrastructure stack
#   ./scripts/mes-stack.sh all-down    Stop everything (MES + infrastructure)
# =============================================================================

set -euo pipefail
cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC}  $*"; }
ok()    { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC}  $*"; }
err()   { echo -e "${RED}[ERROR]${NC} $*" >&2; }

if [ -f .env ]; then
    set -a; source .env; set +a
fi

IGNITION_URL="http://localhost:${IGNITION_HTTP_PORT:-8088}"
INFRA_COMPOSE="infrastructure/docker-compose.yml"

ensure_infra() {
    if ! docker network inspect infrastructure >/dev/null 2>&1; then
        info "Infrastructure network not found. Starting infrastructure stack..."
        cmd_infra_up
    else
        if ! docker ps --filter "name=infra-traefik" --filter "status=running" -q | grep -q .; then
            warn "Infrastructure network exists but Traefik is not running."
            info "Starting infrastructure stack..."
            cmd_infra_up
        else
            ok "Infrastructure stack is running."
        fi
    fi
}

cmd_up() {
    info "Starting MES Ignition 4.0 stack..."
    ensure_infra
    docker compose pull
    docker compose up -d --build
    ok "Stack is starting. Gateway at ${IGNITION_URL}"
    echo ""
    info "Waiting for gateway readiness..."
    for i in $(seq 1 60); do
        if curl -sf "${IGNITION_URL}/StatusPing" >/dev/null 2>&1; then
            ok "Gateway is ready!"
            echo ""
            info "=== Access Points ==="
            echo "  Ignition Gateway:   ${IGNITION_URL}"
            echo "  Ignition (Traefik): http://ignition.mes.local"
            echo "  PgAdmin:            http://pgadmin.mes.local"
            echo "  HiveMQ:             http://hivemq.mes.local"
            echo "  Historian:          http://historian.mes.local"
            echo "  Traefik Dashboard:  http://traefik.infrastructure.local"
            echo "  DNS Admin:          http://dns.infrastructure.local"
            return 0
        fi
        sleep 5
    done
    warn "Gateway didn't respond within 5 minutes. Check: docker compose logs ignition"
}

cmd_down() {
    info "Stopping MES stack..."
    docker compose down
    ok "Stack stopped."
}

cmd_restart() {
    cmd_down
    cmd_up
}

cmd_configure() {
    info "Auto-configuring Ignition gateway..."
    if [ -f scripts/configure-gateway.sh ]; then
        bash scripts/configure-gateway.sh "$@"
    else
        err "scripts/configure-gateway.sh not found"
        return 1
    fi
}

cmd_deploy() {
    info "============================================"
    info "  Full MES Stack Deployment"
    info "============================================"
    echo ""

    # Step 1: Start everything
    info "Step 1/4: Starting stack..."
    cmd_up
    echo ""

    # Step 2: Auto-configure gateway
    info "Step 2/4: Configuring gateway..."
    cmd_configure
    echo ""

    # Step 3: Seed demo data
    info "Step 3/4: Seeding demo data..."
    if [ -f scripts/seed-demo-data.sh ]; then
        bash scripts/seed-demo-data.sh
    else
        warn "scripts/seed-demo-data.sh not found — skipping"
    fi
    echo ""

    # Step 4: Trigger project scan
    info "Step 4/4: Triggering project scan..."
    cmd_scan
    echo ""

    ok "============================================"
    ok "  MES Stack Fully Deployed!"
    ok "============================================"
    echo ""
    echo "  Gateway:    ${IGNITION_URL}"
    echo "  Designer:   Launch from ${IGNITION_URL}"
    echo "  PgAdmin:    http://pgadmin.mes.local"
    echo "  HiveMQ:     http://hivemq.mes.local"
    echo "  Historian:  http://historian.mes.local"
    echo ""
    echo "  Database connections: mes_core, mes_custom, odoo"
    echo "  Historian providers:  mes_core, mes_custom, timebase"
    echo "  MQTT Transmission:    MES/Dallas → Enterprise/Site/Area"
    echo ""
}

cmd_reset_db() {
    warn "This will DESTROY all database data and rebuild from init-sql scripts."
    read -p "Are you sure? (y/N): " confirm
    if [[ "$confirm" != "y" && "$confirm" != "Y" ]]; then
        info "Cancelled."
        return 0
    fi

    info "Stopping postgres..."
    docker compose stop postgres
    docker compose rm -f postgres

    info "Removing postgres volume..."
    docker volume rm "${COMPOSE_PROJECT_NAME:-mes-ignition-4.0}_postgres-data" 2>/dev/null || true

    info "Restarting postgres (will run init-sql scripts)..."
    docker compose up -d postgres

    info "Waiting for postgres health check..."
    for i in $(seq 1 30); do
        if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-mes_user}" -d "${POSTGRES_DB:-mes_core}" >/dev/null 2>&1; then
            ok "Databases rebuilt successfully!"
            echo ""
            info "Databases available:"
            docker compose exec -T postgres psql -U "${POSTGRES_USER:-mes_user}" -d postgres -c "SELECT datname FROM pg_database WHERE datistemplate = false;" 2>/dev/null
            return 0
        fi
        sleep 2
    done
    err "Postgres didn't become healthy. Check: docker compose logs postgres"
}

cmd_status() {
    echo ""
    info "=== Infrastructure Containers ==="
    if [ -f "$INFRA_COMPOSE" ]; then
        docker compose -f "$INFRA_COMPOSE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || warn "Infrastructure stack not running"
    fi
    echo ""

    info "=== MES Containers ==="
    docker compose ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}"
    echo ""

    info "=== Traefik Reverse Proxy ==="
    if docker ps --filter "name=infra-traefik" --filter "status=running" -q | grep -q .; then
        ok "Traefik is routing traffic"
        echo "  Dashboard: http://traefik.infrastructure.local"
    else
        err "Traefik is NOT running — *.local domains won't resolve"
    fi
    echo ""

    info "=== DNS Server ==="
    if docker ps --filter "name=infra-dns" --filter "status=running" -q | grep -q .; then
        ok "Technitium DNS running on :5380"
        echo "  Admin: http://dns.infrastructure.local"
    else
        warn "DNS server is not running"
    fi
    echo ""

    info "=== Database Connectivity ==="
    if docker compose exec -T postgres pg_isready -U "${POSTGRES_USER:-mes_user}" -d "${POSTGRES_DB:-mes_core}" >/dev/null 2>&1; then
        ok "PostgreSQL is accepting connections"
        echo "  Databases:"
        docker compose exec -T postgres psql -U "${POSTGRES_USER:-mes_user}" -d postgres \
            -t -c "SELECT '    - ' || datname FROM pg_database WHERE datistemplate = false ORDER BY datname;" 2>/dev/null
    else
        err "PostgreSQL is not responding"
    fi
    echo ""

    info "=== MQTT Broker ==="
    if curl -sf "http://localhost:${HIVEMQ_WEB_PORT:-8083}" >/dev/null 2>&1; then
        ok "HiveMQ dashboard accessible at http://localhost:${HIVEMQ_WEB_PORT:-8083}"
    else
        warn "HiveMQ dashboard not responding"
    fi
    echo ""

    info "=== Ignition Gateway ==="
    if curl -sf "${IGNITION_URL}/StatusPing" >/dev/null 2>&1; then
        ok "Gateway accessible at ${IGNITION_URL}"
    else
        warn "Gateway not responding at ${IGNITION_URL}"
    fi
}

cmd_logs() {
    local service="${1:-}"
    if [ -n "$service" ]; then
        docker compose logs -f "$service"
    else
        docker compose logs -f
    fi
}

cmd_backup() {
    info "Downloading gateway backup..."
    mkdir -p backups
    local timestamp
    timestamp=$(date +%Y%m%d_%H%M%S)
    local backup_file="backups/gateway_${timestamp}.gwbk"
    if curl -sf -o "$backup_file" \
        -u "${GATEWAY_ADMIN_USERNAME:-admin}:${GATEWAY_ADMIN_PASSWORD:-password}" \
        "${IGNITION_URL}/system/gwbk"; then
        ok "Backup saved to ${backup_file}"
        ls -lh "$backup_file"
    else
        err "Failed to download backup. Is the gateway running?"
        return 1
    fi
}

cmd_scan() {
    info "Triggering Ignition project scan..."
    if curl -sf -X POST \
        -u "${GATEWAY_ADMIN_USERNAME:-admin}:${GATEWAY_ADMIN_PASSWORD:-password}" \
        "${IGNITION_URL}/data/project-scan-endpoint/scan" >/dev/null 2>&1; then
        ok "Project scan triggered."
    else
        warn "Project scan endpoint not available."
        info "Install the project-scan-endpoint module, or run from Designer:"
        info "  system.util.requestProjectScan()"
    fi
}

cmd_infra_up() {
    if [ ! -f "$INFRA_COMPOSE" ]; then
        err "Infrastructure compose file not found at ${INFRA_COMPOSE}"
        info "Creating infrastructure network manually as fallback..."
        docker network create infrastructure 2>/dev/null || true
        return 0
    fi
    info "Starting infrastructure stack (Traefik + DNS)..."
    docker compose -f "$INFRA_COMPOSE" pull
    docker compose -f "$INFRA_COMPOSE" up -d
    ok "Infrastructure stack is running."
    echo "  Traefik:  http://traefik.infrastructure.local"
    echo "  DNS:      http://dns.infrastructure.local (port 5380)"
}

cmd_infra_down() {
    if [ ! -f "$INFRA_COMPOSE" ]; then
        err "Infrastructure compose file not found at ${INFRA_COMPOSE}"
        return 1
    fi
    info "Stopping infrastructure stack..."
    docker compose -f "$INFRA_COMPOSE" down
    ok "Infrastructure stack stopped."
    warn "MES *.local domains will no longer resolve via Traefik."
}

cmd_all_down() {
    info "Stopping ALL stacks..."
    cmd_down
    cmd_infra_down
    ok "Everything is stopped."
}

case "${1:-help}" in
    up)          cmd_up ;;
    down)        cmd_down ;;
    restart)     cmd_restart ;;
    configure)   shift; cmd_configure "$@" ;;
    deploy)      cmd_deploy ;;
    reset-db)    cmd_reset_db ;;
    status)      cmd_status ;;
    logs)        cmd_logs "${2:-}" ;;
    backup)      cmd_backup ;;
    scan)        cmd_scan ;;
    infra-up)    cmd_infra_up ;;
    infra-down)  cmd_infra_down ;;
    all-down)    cmd_all_down ;;
    *)
        echo ""
        echo "MES Ignition 4.0 Stack Manager"
        echo "=============================="
        echo ""
        echo "Usage: $0 <command>"
        echo ""
        echo "  Stack Commands:"
        echo "    up          Start infrastructure + MES stack"
        echo "    down        Stop MES stack (infrastructure stays up)"
        echo "    restart     Restart MES stack"
        echo "    status      Show all container status"
        echo "    logs [svc]  Tail logs (all or specific service)"
        echo ""
        echo "  Setup Commands:"
        echo "    deploy      Full deploy: up + configure + seed + scan"
        echo "    configure   Auto-configure gateway (DB, MQTT, historian)"
        echo ""
        echo "  Database Commands:"
        echo "    reset-db    Destroy and rebuild all databases"
        echo ""
        echo "  Ignition Commands:"
        echo "    backup      Download gateway backup"
        echo "    scan        Trigger project scan"
        echo ""
        echo "  Infrastructure Commands:"
        echo "    infra-up    Start only Traefik + DNS"
        echo "    infra-down  Stop Traefik + DNS"
        echo "    all-down    Stop everything (MES + infrastructure)"
        echo ""
        exit 1
        ;;
esac
