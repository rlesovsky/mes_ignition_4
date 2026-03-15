#!/usr/bin/env bash
# =============================================================================
# sync-from-backup.sh - Sync gateway config from an extracted backup into repo
# =============================================================================
# Usage: ./scripts/sync-from-backup.sh /path/to/extracted/ignition/backup
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

BACKUP_DIR="${1:-}"
if [ -z "$BACKUP_DIR" ]; then
    echo "Usage: $0 /path/to/extracted/ignition/backup"
    exit 1
fi

if [ ! -d "$BACKUP_DIR/config" ]; then
    echo "ERROR: No config/ directory found in: $BACKUP_DIR"
    exit 1
fi

CONFIG_CORE="$BACKUP_DIR/config/resources/core"

echo "=== Syncing Gateway Configuration ==="

# Database connections
if [ -d "$CONFIG_CORE/ignition/database-connection" ]; then
    echo "Syncing database connections..."
    rsync -a "$CONFIG_CORE/ignition/database-connection/" "config/database-connection/"
    # Redact passwords
    find "config/database-connection" -name "config.json" -exec \
        sed -i.bak 's/"ciphertext": "[^"]*"/"ciphertext": "REDACTED"/g' {} \;
    find "config/database-connection" -name "*.bak" -delete
    echo "  Done (passwords redacted)"
fi

# Historian providers
if [ -d "$CONFIG_CORE/com.inductiveautomation.historian/historian-provider" ]; then
    echo "Syncing historian providers..."
    rsync -a "$CONFIG_CORE/com.inductiveautomation.historian/historian-provider/" "config/historian-provider/"
    echo "  Done"
fi

# MQTT Engine
if [ -d "$CONFIG_CORE/com.cirruslink.mqtt.engine.gateway" ]; then
    echo "Syncing MQTT Engine config..."
    rsync -a "$CONFIG_CORE/com.cirruslink.mqtt.engine.gateway/" "config/mqtt-engine/"
    find "config/mqtt-engine" -name "config.json" -exec \
        sed -i.bak 's/"ciphertext": "[^"]*"/"ciphertext": "REDACTED"/g' {} \;
    find "config/mqtt-engine" -name "*.bak" -delete
    echo "  Done (passwords redacted)"
fi

# MQTT Transmission
if [ -d "$CONFIG_CORE/com.cirruslink.mqtt.transmission.gateway" ]; then
    echo "Syncing MQTT Transmission config..."
    rsync -a "$CONFIG_CORE/com.cirruslink.mqtt.transmission.gateway/" "config/mqtt-transmission/"
    find "config/mqtt-transmission" -name "config.json" -exec \
        sed -i.bak 's/"ciphertext": "[^"]*"/"ciphertext": "REDACTED"/g' {} \;
    find "config/mqtt-transmission" -name "*.bak" -delete
    echo "  Done (passwords redacted)"
fi

# UDT definitions
if [ -d "$CONFIG_CORE/ignition/tag-type-definition" ]; then
    echo "Syncing UDT definitions..."
    rsync -a "$CONFIG_CORE/ignition/tag-type-definition/" "config/tag-type-definition/"
    echo "  Done"
fi

echo ""
echo "=== Sync Complete ==="
echo "Review with: git diff --stat"
echo "Commit with: git add -A && git commit -m 'sync: gateway config $(date +%Y-%m-%d)'"
