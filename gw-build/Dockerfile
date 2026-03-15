ARG IGNITION_VERSION=8.3.2
FROM inductiveautomation/ignition:${IGNITION_VERSION}

# =============================================================================
# Third-party module installation
# =============================================================================
# Required modules in gw-build/modules/:
#   - MQTT-Engine-signed.modl        (Cirrus Link)
#   - MQTT-Transmission-signed.modl  (Cirrus Link)
#   - Timebase.Historian-*.modl      (TimeBase)
#
# Docker build context is gw-build/, so paths are relative to that directory.
# The modules/ directory always has at least README.md so COPY never fails.
# Ignition only loads .modl files — the README is harmlessly ignored.
# =============================================================================

COPY modules/ /usr/local/bin/ignition/user-lib/modules/
