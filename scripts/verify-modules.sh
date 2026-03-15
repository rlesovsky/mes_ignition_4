#!/usr/bin/env bash
# =============================================================================
# verify-modules.sh
# =============================================================================
# Checks that required third-party .modl files are present in gw-build/modules/
# before building the stack. Run this before your first deploy.
#
# Usage:
#   ./scripts/verify-modules.sh
# =============================================================================

set -euo pipefail
cd "$(dirname "$0")/.."

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

MODULES_DIR="gw-build/modules"
MISSING=0

echo ""
echo "=== MES Ignition 4.0 — Module Verification ==="
echo ""

check_module() {
    local pattern="$1"
    local name="$2"
    local required="$3"

    # Case-insensitive glob search
    local found
    found=$(find "$MODULES_DIR" -maxdepth 1 -iname "$pattern" -type f 2>/dev/null | head -1)

    if [ -n "$found" ]; then
        local size
        size=$(du -h "$found" | cut -f1)
        echo -e "  ${GREEN}✓${NC} ${name} ($(basename "$found"), ${size})"
        return 0
    else
        if [ "$required" = "required" ]; then
            echo -e "  ${RED}✗${NC} ${name} — MISSING (${pattern})"
            MISSING=$((MISSING + 1))
        else
            echo -e "  ${YELLOW}○${NC} ${name} — not found (optional)"
        fi
        return 1
    fi
}

echo "Required modules:"
check_module "*mqtt*engine*.modl"       "MQTT Engine (Cirrus Link)"        "required"
check_module "*mqtt*transmission*.modl" "MQTT Transmission (Cirrus Link)"  "required"
check_module "*timebase*.modl"          "TimeBase Historian"               "required"

echo ""
echo "Optional modules:"
check_module "*mqtt*distributor*.modl"  "MQTT Distributor (Cirrus Link)"   "optional"
check_module "*project*scan*.modl"      "Project Scan Endpoint"            "optional"
check_module "*web*dev*.modl"           "Web Developer Module"             "optional"

echo ""
if [ $MISSING -gt 0 ]; then
    echo -e "${RED}${MISSING} required module(s) missing!${NC}"
    echo ""
    echo "Download and place .modl files in: ${MODULES_DIR}/"
    echo ""
    echo "  Cirrus Link modules: https://www.cirrus-link.com/software-downloads/"
    echo "  TimeBase modules:    https://www.timebase.us/downloads"
    echo ""
    echo "After adding modules, rebuild with:"
    echo "  docker compose build ignition"
    echo "  docker compose up -d ignition"
    exit 1
else
    echo -e "${GREEN}All required modules present!${NC}"
    echo ""
    echo "Ready to build: ./scripts/mes-stack.sh deploy"
fi
