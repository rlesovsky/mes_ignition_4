# =============================================================================
# MES Ignition 4.0 — Required Third-Party Modules
# =============================================================================
# Place .modl files in this directory before building the stack.
# The Dockerfile copies them into the Ignition user-lib/modules/ directory.
#
# REQUIRED:
# ---------
# 1. MQTT-Engine.modl
#    Source: Cirrus Link (https://www.cirrus-link.com/software-downloads/)
#    Purpose: MQTT Engine tag provider — receives Sparkplug B data from PLCs
#
# 2. MQTT-Transmission.modl
#    Source: Cirrus Link (https://www.cirrus-link.com/software-downloads/)
#    Purpose: Publishes Ignition tag data as Sparkplug B to the UNS
#    Config: Group=MES, Edge Node=Dallas, Path=Enterprise/Site/Area
#
# 3. Timebase-Historian.modl
#    Source: TimeBase (https://www.timebase.us/downloads)
#    Purpose: TimeBase historian provider for Ignition
#    Config: Points to http://historian:4511
#
# OPTIONAL:
# ---------
# 4. MQTT-Distributor.modl
#    Source: Cirrus Link
#    Purpose: Embedded MQTT broker (not needed if using HiveMQ)
#
# 5. project-scan-endpoint.modl
#    Source: Design Group (https://github.com/design-group/ignition-project-scan-endpoint)
#    Purpose: REST endpoint to trigger project scan after git pull
#
# HOW TO ADD:
# -----------
# 1. Download the .modl files from the sources above
# 2. Copy them into this directory: gw-build/modules/
# 3. Rebuild the stack: ./scripts/mes-stack.sh restart
#    (or: docker compose build ignition && docker compose up -d ignition)
#
# NOTE: .modl files are gitignored (they contain licensed binaries).
#       Each developer needs to provide their own licensed copies.
# =============================================================================
