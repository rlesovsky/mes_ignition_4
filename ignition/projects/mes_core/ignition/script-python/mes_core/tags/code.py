"""
MES Core tag helpers
=====================
Ignition Gateway Script Library: mes_core.tags

Shared tag-path construction and bulk-read helpers. Extracted so the OEE
snapshot that run.updateRun and run.stopRun both need is built and read in
exactly one place — path typos can no longer diverge between the two.

Introducing this module changes no runtime behavior: the path list, read order
and null-coalescing match the blocks it replaces.
"""


def coalesce(value, default=0):
	"""Return `default` when `value` is None, else `value`.

	Mirrors the `x if x is not None else 0` guard the run module applied to
	every tag in its snapshot reads.
	"""
	return value if value is not None else default


def oeeSnapshotPaths(linePath):
	"""Ordered OEE/Dispatch tag paths for the run snapshot.

	The order is significant — readOeeSnapshot maps positional results back to
	named values by this order, and it matches the original updateRun/stopRun
	read blocks exactly.
	"""
	return [
		linePath + '/Dispatch/OEE Infeed/Count',
		linePath + '/Dispatch/OEE Outfeed/Count',
		linePath + '/Dispatch/OEE Waste/Count',
		linePath + '/OEE/Total Count',
		linePath + '/OEE/Bad Count',
		linePath + '/OEE/Good Count',
		linePath + '/OEE/OEE Quality',
		linePath + '/OEE/OEE Performance',
		linePath + '/OEE/OEE Availability',
		linePath + '/OEE/OEE',
		linePath + '/OEE/Run Time',
		linePath + '/OEE/Unplanned Downtime',
		linePath + '/OEE/Planned Downtime',
		linePath + '/OEE/Total Time'
	]


def readOeeSnapshot(linePath):
	"""Bulk-read the OEE snapshot for a line and return null-coalesced values.

	Returns a dict keyed to match the `run` table column groupings used by
	updateRun/stopRun. Every value is coalesced to 0 when the tag is None,
	exactly as the original inline blocks did.
	"""
	results = system.tag.readBlocking(oeeSnapshotPaths(linePath))
	return {
		'infeed':            coalesce(results[0].value),
		'outfeed':           coalesce(results[1].value),
		'waste':             coalesce(results[2].value),
		'totalCount':        coalesce(results[3].value),
		'badCount':          coalesce(results[4].value),
		'goodCount':         coalesce(results[5].value),
		'quality':           coalesce(results[6].value),
		'performance':       coalesce(results[7].value),
		'availability':      coalesce(results[8].value),
		'oee':               coalesce(results[9].value),
		'runTime':           coalesce(results[10].value),
		'unplannedDowntime': coalesce(results[11].value),
		'plannedDowntime':   coalesce(results[12].value),
		'totalTime':         coalesce(results[13].value)
	}
