"""
MES Core shared configuration
==============================
Ignition Gateway Script Library: mes_core.config

Single source of truth for values that were previously re-declared across the
mes_core modules (the datasource name, the enterprise root, the output count
type IDs, the run-ID sentinel and the logger prefix). Importing from here means
a datasource rename or a constant change happens in exactly one place.

Introducing this module changes no runtime behavior: every value below equals
the literal it replaced.
"""

# --- Datasource -------------------------------------------------------------
# PostgreSQL connection name. Was re-declared as `db = 'mes_core'` in the
# run, oee, order, state and count modules.
DB = 'mes_core'

# --- Model / hierarchy ------------------------------------------------------
# Only the 'OF' enterprise is supported (enforced in model.getEnterpriseID);
# deeper levels prepend this root when a caller omits it.
ENTERPRISE_ROOT = 'OF'

# --- Count types (counthistory.counttypeid) ---------------------------------
# Output count types summed for OEE Total Count (Good + Waste).
COUNT_TYPE_GOOD = 2
COUNT_TYPE_WASTE = 3

# --- Run identifiers --------------------------------------------------------
# Sentinel written to the non-nullable OEE/RunID Int tag to mean "no active
# run". History tables use NULL instead; only the Int tag uses this sentinel.
RUN_ID_SENTINEL = -1

# --- Logging ----------------------------------------------------------------
# Common prefix for the MES gateway loggers (e.g. "MES_Run", "MES_Core_OEE").
LOGGER_PREFIX = 'MES'


def getLogger(suffix=None):
	"""Return a gateway logger under the shared MES prefix.

	getLogger()       -> "MES"
	getLogger("Run")  -> "MES_Run"

	Existing modules keep their current logger names; this factory is provided
	so new code stays consistent with the established naming.
	"""
	if suffix:
		return system.util.getLogger('%s_%s' % (LOGGER_PREFIX, suffix))
	return system.util.getLogger(LOGGER_PREFIX)
