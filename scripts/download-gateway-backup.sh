#!/usr/bin/env bash
# =============================================================================
# download-gateway-backup.sh - Download gateway backup from running Ignition
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; source .env; set +a; fi

IGNITION_URL="http://localhost:${IGNITION_HTTP_PORT:-8088}"
ADMIN_USER="${GATEWAY_ADMIN_USERNAME:-admin}"
ADMIN_PASS="${GATEWAY_ADMIN_PASSWORD:-password}"

mkdir -p backups
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="backups/gateway_${TIMESTAMP}.gwbk"

echo "Downloading gateway backup from ${IGNITION_URL}..."

HTTP_CODE=$(curl -s -o "$BACKUP_FILE" -w "%{http_code}" \
    -u "${ADMIN_USER}:${ADMIN_PASS}" \
    "${IGNITION_URL}/system/gwbk" 2>/dev/null || echo "000")

if [ "$HTTP_CODE" = "200" ] && [ -s "$BACKUP_FILE" ]; then
    echo "Backup saved: ${BACKUP_FILE}"
    ls -lh "$BACKUP_FILE"
    echo ""
    echo "To auto-restore on fresh deploys:"
    echo "  1. cp ${BACKUP_FILE} backups/gateway.gwbk"
    echo "  2. Uncomment restore volume in docker-compose.yml"
else
    rm -f "$BACKUP_FILE"
    echo "ERROR: Failed to download backup (HTTP ${HTTP_CODE})."
    exit 1
fi
