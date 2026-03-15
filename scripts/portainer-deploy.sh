#!/usr/bin/env bash
# =============================================================================
# portainer-deploy.sh - Deploy stacks for Portainer visibility
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

if [ -f .env ]; then set -a; source .env; set +a; fi

echo "=== Portainer Stack Deployment ==="
echo ""

echo "Step 1: Starting infrastructure stack..."
if [ -f infrastructure/docker-compose.yml ]; then
    docker compose -f infrastructure/docker-compose.yml up -d
    echo "  Infrastructure stack running"
fi

echo ""
echo "Step 2: Starting MES stack..."
docker compose up -d --build
echo "  MES stack running"

echo ""
echo "=== Stacks Deployed ==="
echo ""
echo "Both stacks are now running and visible in Portainer."
echo ""
echo "To import as a managed Portainer stack from GitHub:"
echo "  1. Portainer → Stacks → Add Stack → Repository"
echo "  2. Repo URL: https://github.com/rlesovsky/mes_Ignition_4.0"
echo "  3. Compose path: docker-compose.yml"
echo "  4. Upload .env or set env vars inline"
