#!/usr/bin/env bash
# =============================================================================
# clean-resource-json.sh - Remove Designer timestamp noise before git commits
# =============================================================================
set -euo pipefail
cd "$(dirname "$0")/.."

DRY_RUN=true
if [[ "${1:-}" == "--apply" ]]; then DRY_RUN=false; fi

PROJECTS_DIR="./ignition/projects"
CLEANED=0

if [ ! -d "$PROJECTS_DIR" ]; then echo "No projects directory found."; exit 0; fi

echo "Scanning for resource.json files with only timestamp changes..."

while IFS= read -r file; do
    if [ -z "$file" ]; then continue; fi
    diff_output=$(git diff -- "$file" 2>/dev/null || true)
    if [ -z "$diff_output" ]; then continue; fi
    if echo "$diff_output" | grep -q '"lastModification"'; then
        changed_content=$(echo "$diff_output" | grep -c '^[+-][^+-]' || echo "0")
        if [ "$changed_content" -le 6 ]; then
            if $DRY_RUN; then
                echo "  [DRY RUN] Would restore: $file"
            else
                git checkout -- "$file"
                echo "  [CLEANED] Restored: $file"
            fi
            CLEANED=$((CLEANED + 1))
        fi
    fi
done < <(git diff --name-only -- "$PROJECTS_DIR" 2>/dev/null | grep "resource.json")

echo ""
if [ $CLEANED -eq 0 ]; then
    echo "No timestamp-only changes found."
else
    if $DRY_RUN; then
        echo "Found $CLEANED files. Run with --apply to clean: $0 --apply"
    else
        echo "Cleaned $CLEANED resource.json files."
    fi
fi
