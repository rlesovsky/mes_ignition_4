#!/usr/bin/env bash
# =============================================================================
# configure-gateway.sh
# =============================================================================
# Automatically configures a fresh Ignition 8.3 gateway with:
#   - Database connections (mes_core, mes_custom, odoo)
#   - Historian providers (mes_core, mes_custom SQL historians + TimeBase)
#   - MQTT Transmission server and transmitter
#
# Uses the Ignition Gateway Config API (8.3+) to create resources.
#
# Prerequisites:
#   - Gateway must be running and accessible
#   - PostgreSQL must be running and healthy
#   - HiveMQ must be running
#
# Usage:
#   ./scripts/configure-gateway.sh
#   ./scripts/configure-gateway.sh --skip-mqtt
#   ./scripts/configure-gateway.sh --skip-historian
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

SKIP_MQTT=false
SKIP_HISTORIAN=false
for arg in "$@"; do
    case "$arg" in
        --skip-mqtt) SKIP_MQTT=true ;;
        --skip-historian) SKIP_HISTORIAN=true ;;
    esac
done

# ============================================
# Docker hostnames (as seen from INSIDE the Ignition container)
# These use Docker Compose service names which resolve on the 'mes' network.
# ============================================
IGNITION_URL="http://localhost:${IGNITION_HTTP_PORT:-8088}"
ADMIN_USER="${GATEWAY_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${GATEWAY_ADMIN_PASSWORD:-password}"

# Database — service name 'postgres', container_name 'mes-postgres'
PG_HOST="postgres"
PG_PORT="5432"
PG_USER="${POSTGRES_USER:-mes_user}"
PG_PASS="${POSTGRES_PASSWORD:-StrongPostgres123}"

# MQTT — service name 'hivemq', container_name 'mes-hivemq'
MQTT_HOST="hivemq"
MQTT_PORT_INTERNAL="1883"

# TimeBase — service name 'historian', container_name 'mes-timebase-historian'
HISTORIAN_HOST="historian"
HISTORIAN_PORT="4511"

# ============================================
# Helper: Wait for gateway
# ============================================
wait_for_gateway() {
    info "Waiting for Ignition gateway..."
    for i in $(seq 1 60); do
        if curl -sf "${IGNITION_URL}/StatusPing" >/dev/null 2>&1; then
            ok "Gateway is ready at ${IGNITION_URL}"
            return 0
        fi
        sleep 5
    done
    err "Gateway not responding after 5 minutes"
    exit 1
}

# ============================================
# Helper: Ignition Config API
# ============================================
igc_put() {
    local resource_type="$1"
    local resource_name="$2"
    local json_payload="$3"

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -X PUT \
        -H "Content-Type: application/json" \
        -u "${ADMIN_USER}:${ADMIN_PASS}" \
        -d "$json_payload" \
        "${IGNITION_URL}/config/v1/resources/${resource_type}/${resource_name}" 2>/dev/null)

    if [ "$http_code" = "200" ] || [ "$http_code" = "201" ] || [ "$http_code" = "204" ]; then
        return 0
    else
        return 1
    fi
}

igc_exists() {
    local resource_type="$1"
    local resource_name="$2"

    local http_code
    http_code=$(curl -s -o /dev/null -w "%{http_code}" \
        -u "${ADMIN_USER}:${ADMIN_PASS}" \
        "${IGNITION_URL}/config/v1/resources/${resource_type}/${resource_name}" 2>/dev/null)

    [ "$http_code" = "200" ]
}

# ============================================
# Configure Database Connections
# ============================================
configure_databases() {
    info "=== Configuring Database Connections ==="

    for db_name in mes_core mes_custom odoo; do
        local connect_url="jdbc:postgresql://${PG_HOST}:${PG_PORT}/${db_name}"

        if igc_exists "ignition/database-connection" "$db_name"; then
            ok "  ${db_name} already exists — skipping"
            continue
        fi

        info "  Creating: ${db_name} → ${connect_url}"

        local payload
        payload=$(cat <<EOF
{
  "connectURL": "${connect_url}",
  "driver": "PostgreSQL",
  "translator": "POSTGRES",
  "username": "${PG_USER}",
  "password": "${PG_PASS}",
  "poolMaxActive": 8,
  "poolMaxIdle": 8,
  "poolMaxWait": 5000,
  "poolMinIdle": 0,
  "poolInitSize": 0,
  "testOnBorrow": true,
  "validationQuery": "SELECT 1",
  "validationSleepTime": 10000,
  "slowQueryLogThreshold": 60000,
  "defaultTransactionLevel": "DEFAULT",
  "failoverMode": "STANDARD"
}
EOF
)

        if igc_put "ignition/database-connection" "$db_name" "$payload"; then
            ok "  ${db_name} created"
        else
            err "  Failed to create ${db_name}"
        fi
    done
}

# ============================================
# Configure Historian Providers
# ============================================
configure_historians() {
    if $SKIP_HISTORIAN; then
        warn "Skipping historian configuration (--skip-historian)"
        return
    fi

    info ""
    info "=== Configuring Historian Providers ==="

    for hist_name in mes_core mes_custom; do
        if igc_exists "com.inductiveautomation.historian/historian-provider" "$hist_name"; then
            ok "  ${hist_name} historian already exists — skipping"
            continue
        fi

        info "  Creating SQL historian: ${hist_name}"

        local payload
        payload=$(cat <<EOF
{
  "profile": { "type": "SqlHistorian" },
  "settings": {
    "database": "${hist_name}",
    "profile": "${hist_name}",
    "partition": {
      "enabled": true,
      "optimized": false,
      "optimizedWindowSeconds": 60,
      "size": 1,
      "sizeUnits": "MONTH"
    },
    "pruning": {
      "age": 1,
      "ageUnits": "YEAR",
      "enabled": false
    },
    "staleMultiplier": 2,
    "trackSce": true
  }
}
EOF
)

        if igc_put "com.inductiveautomation.historian/historian-provider" "$hist_name" "$payload"; then
            ok "  ${hist_name} historian created"
        else
            err "  Failed to create ${hist_name} historian"
        fi
    done

    # TimeBase Historian
    if igc_exists "com.inductiveautomation.historian/historian-provider" "timebase"; then
        ok "  timebase historian already exists — skipping"
    else
        info "  Creating TimeBase historian: http://${HISTORIAN_HOST}:${HISTORIAN_PORT}"

        local payload
        payload=$(cat <<EOF
{
  "profile": { "type": "com.flowsoftware.timebase.historian" },
  "settings": {
    "BASE_URL": "http://${HISTORIAN_HOST}:${HISTORIAN_PORT}",
    "CLIENT_ID": "",
    "DATASET_PREFIX": "ignition",
    "IDP_URL": ""
  }
}
EOF
)

        if igc_put "com.inductiveautomation.historian/historian-provider" "timebase" "$payload"; then
            ok "  timebase historian created"
        else
            warn "  TimeBase historian failed (module may not be installed yet)"
        fi
    fi
}

# ============================================
# Configure MQTT Transmission
# ============================================
configure_mqtt() {
    if $SKIP_MQTT; then
        warn "Skipping MQTT configuration (--skip-mqtt)"
        return
    fi

    info ""
    info "=== Configuring MQTT Transmission ==="

    info "  Server: tcp://${MQTT_HOST}:${MQTT_PORT_INTERNAL}"

    local server_payload
    server_payload=$(cat <<EOF
{
  "dataFormatTypeWrapper": "Sparkplug_B_v1_0_Protobuf",
  "hostnameVerification": true,
  "keepAlive": 30,
  "mqttServerConnectionEnabled": true,
  "password": "",
  "reconnectDelay": 1000,
  "serverSet": "Bootcamp",
  "subscribeToLegacyStateTopic": true,
  "url": "tcp://${MQTT_HOST}:${MQTT_PORT_INTERNAL}",
  "username": "admin"
}
EOF
)

    if igc_put "com.cirruslink.mqtt.transmission.gateway/server" "HiveMQ" "$server_payload"; then
        ok "  MQTT server configured"
    else
        warn "  MQTT server config failed (module may not be installed)"
    fi

    info "  Transmitter: MES/Dallas → Enterprise/Site/Area"

    local transmitter_payload
    transmitter_payload=$(cat <<EOF
{
  "convertUdts": true,
  "edgeNodeId": "Dallas",
  "enableStoreForwardByDefault": true,
  "groupId": "MES",
  "includeSparkplugDataTypes": true,
  "optimizeUdts": true,
  "publishUdtDefinitions": true,
  "rebirthDebounceDelay": 5000,
  "serverSet": "Bootcamp",
  "tagPacingPeriod": 1000,
  "tagPath": "Enterprise/Site/Area",
  "tagProvider": "default",
  "useCirrusEncoder": true
}
EOF
)

    if igc_put "com.cirruslink.mqtt.transmission.gateway/transmitter" "Line1" "$transmitter_payload"; then
        ok "  Transmitter Line1 configured"
    else
        warn "  Transmitter config failed (module may not be installed)"
    fi
}

# ============================================
# Main
# ============================================
echo ""
echo "============================================"
echo "  MES Ignition 4.0 - Gateway Auto-Config"
echo "============================================"
echo ""

wait_for_gateway
configure_databases
configure_historians
configure_mqtt

echo ""
info "=== Configuration Complete ==="
echo ""
echo "  Database Connections:"
echo "    - mes_core   → jdbc:postgresql://${PG_HOST}:${PG_PORT}/mes_core"
echo "    - mes_custom → jdbc:postgresql://${PG_HOST}:${PG_PORT}/mes_custom"
echo "    - odoo       → jdbc:postgresql://${PG_HOST}:${PG_PORT}/odoo"
echo ""
echo "  Historian Providers:"
echo "    - mes_core   (SQL Historian, monthly partitions)"
echo "    - mes_custom (SQL Historian, monthly partitions)"
echo "    - timebase   (TimeBase at http://${HISTORIAN_HOST}:${HISTORIAN_PORT})"
echo ""
if ! $SKIP_MQTT; then
echo "  MQTT Transmission:"
echo "    - Server:      tcp://${MQTT_HOST}:${MQTT_PORT_INTERNAL} (Sparkplug B)"
echo "    - Transmitter: MES/Dallas → Enterprise/Site/Area"
echo ""
fi
echo "  Verify: ${IGNITION_URL}"
echo ""
