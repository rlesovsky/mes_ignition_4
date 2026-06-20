#* 4.0 Solutions LLC CONFIDENTIAL
#* __________________
#* 
#*  [2015] - [2022] 4.0 Solutions LLC 
#*  All Rights Reserved.
#* 
#* NOTICE:  All information contained herein is, and remains
#* the property of 4.0 Solutions LLC and its suppliers,
#* if any.  The intellectual and technical concepts contained
#* herein are proprietary to 4.0 Solutions LLC
#* and its suppliers and may be covered by U.S. and Foreign Patents,
#* patents in process, and are protected by trade secret or copyright law.
#* Dissemination of this information or reproduction of this material
#* is strictly forbidden unless prior written permission is obtained
#* from 4.0 Solutions LLC.

'''
Optimized MES Core OEE Calculation Library - PostgreSQL Version
	- Fixed tag paths for /Line/ subfolder structure
	- Fixed run-based filtering
	- Added proper error handling
	- Added debug capability
	- Reads CountTypeID from tags instead of hardcoding
	- Converted from MySQL to PostgreSQL syntax
	- FIXED: Added missing Total Time and Run Time calculations
'''

import inspect

from mes_core import config

# Global variables
db = config.DB
DEBUG_MODE = False  # Set to True for debugging

# Get a logger instance
logger = system.util.getLogger("MES_Core_OEE")

def setDebugMode(enabled):
	"""Enable or disable debug mode"""
	global DEBUG_MODE
	DEBUG_MODE = enabled
	logger.info("Debug mode set to: %s" % enabled)

def debugPrint(message, functionName=None):
	"""Log a debug/trace message for the OEE functions.

	Gated behind DEBUG_MODE so the verbose tracing is silent in normal
	operation: when DEBUG_MODE is on it logs at INFO, otherwise at DEBUG (which
	the gateway suppresses unless the MES_Core_OEE logger is set to debug). The
	old redundant second hop through mes_core.logging.log (which re-logged the
	same line to the "MES" logger) has been removed.
	"""
	if functionName is None:
		try:
			functionName = inspect.stack()[1][3]
		except:
			functionName = "unknown"

	logMessage = "[%s] %s" % (functionName, message)
	if DEBUG_MODE:
		logger.info(logMessage)
	else:
		logger.debug(logMessage)


def getTagIDs(db, lineIDPath):
	debugPrint("Getting tag IDs for line path: %s" % lineIDPath)
	
	try:
		listOfTags = []
		lineID = system.tag.readBlocking([lineIDPath])[0].value
		debugPrint("Line ID value: %s" % lineID)
		
		query = 'SELECT id FROM counttag WHERE parentid = ?'
		debugPrint("Query: %s with param: %s" % (query, lineID))
		data = system.db.runPrepQuery(query, [lineID], db)
		debugPrint("Query returned %s rows" % len(data))
		
		for row in data:
			tagID = row[0]
			listOfTags.append(tagID)
		
		debugPrint("Found tag IDs: %s" % str(listOfTags))
		return listOfTags
		
	except Exception as e:
		debugPrint("Error getting tag IDs: %s" % str(e))
		logger.error("getTagIDs error: %s" % str(e))
		return []

		
def getTotalCount(db, lineIDPath, totalCountPath, startTimePath, endTimePath, runID=None):
	debugPrint("Getting total count for line: %s, Run: %s" % (lineIDPath, runID))
	
	try:
		tagIDs = getTagIDs(db, lineIDPath)
		if not tagIDs:
			debugPrint("No tags found for line")
			system.tag.writeBlocking([totalCountPath], [0])
			return 0
		
		placeholders = ','.join(['?' for _ in tagIDs])
		
		startTime = system.tag.readBlocking([startTimePath])[0].value
		endTime = system.tag.readBlocking([endTimePath])[0].value
		
		# FIXED: Sum only OUTPUT count types (Good=2, Waste=3)
		# Total Count for OEE = Good + Bad/Waste
		if runID is not None:
			query = '''
				SELECT SUM(count) FROM counthistory
				WHERE counttypeid IN (2, 3) AND runid = ? AND tagid IN (%s)
				AND count >= 0
			''' % placeholders
			params = [runID] + tagIDs
			debugPrint("Using run-based query with RunID: %s" % runID)
		else:
			query = '''
				SELECT SUM(count) FROM counthistory
				WHERE counttypeid IN (2, 3) AND "TimeStamp" BETWEEN ? AND ? AND tagid IN (%s)
				AND count >= 0
			''' % placeholders
			params = [startTime, endTime] + tagIDs
			debugPrint("Using time-based query from %s to %s" % (startTime, endTime))
		
		debugPrint("Query params: %s" % str(params))
		data = system.db.runPrepQuery(query, params, db)
		
		totalCount = 0
		for row in data:
			totalCount = row[0] if row[0] is not None else 0
		
		system.tag.writeBlocking([totalCountPath], [totalCount])
		debugPrint("Total count: %s (Good + Waste)" % totalCount)
		return totalCount
		
	except Exception as e:
		debugPrint("Error getting total count: %s" % str(e))
		logger.error("getTotalCount error: %s" % str(e))
		system.tag.writeBlocking([totalCountPath], [0])
		return 0
		
def getUnplannedDowntimeSeconds(db, startTimePath, unplannedDowntimePath, lineIDPath, runID=None):
	debugPrint("Getting unplanned downtime for line: %s, Run: %s" % (lineIDPath, runID))
	
	try:
		startTime = system.tag.readBlocking([startTimePath])[0].value
		lineID = system.tag.readBlocking([lineIDPath])[0].value
		debugPrint("Line ID value: %s, Start time: %s" % (lineID, startTime))
		
		# Choose query based on whether we have a runID
		if runID is not None:
			query = '''
				SELECT SUM(EXTRACT(EPOCH FROM (
					COALESCE(s.enddatetime, CURRENT_TIMESTAMP) - s.startdatetime
				))) as TotalSeconds
				FROM statehistory s
				LEFT JOIN statereason st ON s.statereasonid = st.id
				WHERE st.recorddowntime = true 
				AND s.lineid = ? 
				AND s.runid = ?
			'''
			params = [lineID, runID]
			debugPrint("Using run-based downtime query with RunID: %s" % runID)
		else:
			query = '''
				SELECT SUM(EXTRACT(EPOCH FROM (
					COALESCE(s.enddatetime, CURRENT_TIMESTAMP) - s.startdatetime
				))) as TotalSeconds
				FROM statehistory s
				LEFT JOIN statereason st ON s.statereasonid = st.id
				WHERE st.recorddowntime = true
				AND s.lineid = ?
				AND s.startdatetime > ?
				AND (s.enddatetime <= CURRENT_TIMESTAMP OR s.enddatetime IS NULL)
			'''
			params = [lineID, startTime]
			debugPrint("Using time-based downtime query from: %s" % startTime)
		
		debugPrint("Query: %s" % query)
		debugPrint("Params: %s" % str(params))
		data = system.db.runPrepQuery(query, params, db)
		debugPrint("Query returned %s rows" % len(data))
		
		unplannedDowntime = 0
		for row in data:
			unplannedDowntime = row[0] if row[0] is not None else 0
		
		system.tag.writeBlocking([unplannedDowntimePath], [unplannedDowntime])
		debugPrint("Unplanned downtime: %s seconds (%.2f hours)" % (unplannedDowntime, unplannedDowntime / 3600.0))
		return unplannedDowntime
		
	except Exception as e:
		debugPrint("Error getting unplanned downtime: %s" % str(e))
		logger.error("getUnplannedDowntimeSeconds error: %s" % str(e))
		system.tag.writeBlocking([unplannedDowntimePath], [0])
		return 0

def getPlannedDowntimeSeconds(db, startTimePath, plannedDowntimePath, lineIDPath, runID=None):
	debugPrint("Getting planned downtime for line: %s, Run: %s" % (lineIDPath, runID))
	
	try:
		startTime = system.tag.readBlocking([startTimePath])[0].value
		lineID = system.tag.readBlocking([lineIDPath])[0].value
		
		# Choose query based on whether we have a runID
		if runID is not None:
			query = '''
				SELECT SUM(EXTRACT(EPOCH FROM (
					COALESCE(s.enddatetime, CURRENT_TIMESTAMP) - s.startdatetime
				))) as TotalSeconds
				FROM statehistory s
				LEFT JOIN statereason st ON s.statereasonid = st.id
				WHERE st.planneddowntime = true 
				AND s.lineid = ? 
				AND s.runid = ?
			'''
			params = [lineID, runID]
			debugPrint("Using run-based planned downtime query with RunID: %s" % runID)
		else:
			query = '''
				SELECT SUM(EXTRACT(EPOCH FROM (
					COALESCE(s.enddatetime, CURRENT_TIMESTAMP) - s.startdatetime
				))) as TotalSeconds
				FROM statehistory s
				LEFT JOIN statereason st ON s.statereasonid = st.id
				WHERE st.planneddowntime = true
				AND s.lineid = ?
				AND s.startdatetime > ?
				AND (s.enddatetime <= CURRENT_TIMESTAMP OR s.enddatetime IS NULL)
			'''
			params = [lineID, startTime]
			debugPrint("Using time-based planned downtime query from: %s" % startTime)
		
		data = system.db.runPrepQuery(query, params, db)
		
		plannedDowntime = 0
		for row in data:
			plannedDowntime = row[0] if row[0] is not None else 0
			
		system.tag.writeBlocking([plannedDowntimePath], [plannedDowntime])
		debugPrint("Planned downtime: %s seconds (%.2f hours)" % (plannedDowntime, plannedDowntime / 3600.0))
		return plannedDowntime
		
	except Exception as e:
		debugPrint("Error getting planned downtime: %s" % str(e))
		logger.error("getPlannedDowntimeSeconds error: %s" % str(e))
		system.tag.writeBlocking([plannedDowntimePath], [0])
		return 0

def getCurrentRunID(lineID, db=db):
	"""Get the current active run ID for a line"""
	debugPrint("Getting current run ID for line: %s" % lineID)
	try:
		query = '''
			SELECT r.id 
			FROM run r
			INNER JOIN schedule s ON r.scheduleid = s.id
			WHERE s.lineid = ? 
			AND (r.closed IS NULL OR r.closed = false)
			AND r.runstartdatetime IS NOT NULL
			AND r.runstopdatetime IS NULL
			ORDER BY r.runstartdatetime DESC
			LIMIT 1
		'''
		
		debugPrint("Query: %s" % query)
		debugPrint("Param: %s" % lineID)
		data = system.db.runPrepQuery(query, [lineID], db)
		debugPrint("Query returned %s rows" % len(data))
		
		if len(data) > 0:
			runID = data[0][0]
			debugPrint("Found active run ID %s for line %s" % (runID, lineID))
			return runID
		else:
			debugPrint("No active run found for line %s" % lineID)
			return None
			
	except Exception as e:
		debugPrint("Error getting current run ID for line %s: %s" % (lineID, str(e)))
		logger.error("getCurrentRunID error: %s" % str(e))
		return None


def getOee(parentPath, runID=None):
	"""Simplified OEE calculation - works with UDT expressions"""
	debugPrint("========== Starting OEE calculation ==========")
	debugPrint("Parent path: %s" % parentPath)
	
	try:
		linePath = parentPath + '/Line'
		oeeBasePath = linePath + '/OEE'
		dispatchBasePath = linePath + '/Dispatch'
		
		# Tag paths
		lineIDPath = linePath + '/Line ID'
		startTimePath = linePath + '/Start Time'  # Line level
		currentTimePath = linePath + '/Current Time'
		
		# OEE calculation tags
		unplannedDowntimePath = oeeBasePath + '/Unplanned Downtime'
		plannedDowntimePath = oeeBasePath + '/Planned Downtime'
		totalCountPath = oeeBasePath + '/Total Count'
		goodCountPath = oeeBasePath + '/Good Count'
		badCountPath = oeeBasePath + '/Bad Count'
		oeeQualityPath = oeeBasePath + '/OEE Quality'
		oeePerformancePath = oeeBasePath + '/OEE Performance'
		oeeAvailabilityPath = oeeBasePath + '/OEE Availability'
		runIDPath = oeeBasePath + '/RunID'
		
		# Tag ownership (verified against tags.json, UDT type "OEE-Downtime"):
		# These are UDT EXPRESSION tags — read-only from getOee, computed by the UDT:
		#   Total Time  = ({Current Time} - {Start Time}) / 1000   (Current Time = now())
		#   Run Time    = {Total Time} - {Unplanned Downtime} - {Planned Downtime}
		#   Target Count= ({Standard Rate} / 3600) * {Run Time}
		#   OEE         = Availability * Performance * Quality
		# getOee writes only the memory tags OEE Quality/Performance/Availability below.

		runTimePath = oeeBasePath + '/Run Time'          # UDT expression (read-only)
		targetCountPath = oeeBasePath + '/Target Count'  # UDT expression (read-only)
		
		# Dispatch tags
		goodCountIDPath = dispatchBasePath + '/OEE Outfeed/TagID'
		goodCountTypePath = dispatchBasePath + '/OEE Outfeed/CountTypeID'
		badCountIDPath = dispatchBasePath + '/OEE Waste/TagID'
		badCountTypePath = dispatchBasePath + '/OEE Waste/CountTypeID'
		
		# Get values
		lineIDResult = system.tag.readBlocking([lineIDPath])[0]
		lineIDValue = lineIDResult.value
		
		if not lineIDResult.quality.isGood():
			debugPrint("ERROR: Line ID tag not found!")
			return
		
		# Dispatch IDs/types in one batched read
		_disp = system.tag.readBlocking([goodCountIDPath, goodCountTypePath, badCountIDPath, badCountTypePath])
		goodCountID = _disp[0].value
		goodCountTypeID = _disp[1].value or 2
		badCountID = _disp[2].value
		badCountTypeID = _disp[3].value or 3
		
		# Get or detect run ID
		currentRunID = runID
		if currentRunID is None:
			currentRunID = getCurrentRunID(lineIDValue, db)
			debugPrint("Auto-detected run ID: %s" % currentRunID)
		
		if currentRunID is not None:
			system.tag.writeBlocking([runIDPath], [currentRunID])
		
		# Calculate downtimes (writes to the memory tags the UDT Run Time expression reads)
		debugPrint("--- Calculating Downtimes ---")
		getUnplannedDowntimeSeconds(db, startTimePath, unplannedDowntimePath, lineIDPath, currentRunID)
		getPlannedDowntimeSeconds(db, startTimePath, plannedDowntimePath, lineIDPath, currentRunID)

		# Get counts from database (writes to tags)
		debugPrint("--- Calculating Counts ---")
		# Note: These write to Outfeed Count and Waste Count, not Good Count
		# Good Count is calculated by UDT expression or reference
		getTotalCount(db, lineIDPath, totalCountPath, startTimePath, currentTimePath, currentRunID)

		# Read the UDT-calculated values in one batched read (incl. Total Time used below).
		# Run Time, Target Count and Total Time are UDT EXPRESSION tags (verified in tags.json,
		# type "OEE-Downtime") — getOee reads them, it does not write them.
		_calc = system.tag.readBlocking([totalCountPath, goodCountPath, runTimePath, targetCountPath, oeeBasePath + '/Total Time'])
		totalCount = _calc[0].value
		goodCount = _calc[1].value    # UDT reference (mirrors Outfeed Count)
		runTime = _calc[2].value      # UDT expression
		targetCount = _calc[3].value  # UDT expression
		totalTime = _calc[4].value    # UDT expression

		debugPrint("Total Count: %s, Good Count: %s" % (totalCount, goodCount))
		debugPrint("Run Time: %s sec, Target Count: %s" % (runTime, targetCount))

		# Calculate the three OEE percentages
		debugPrint("--- Calculating OEE Components ---")

		# Quality = Good / Total
		if totalCount and totalCount > 0:
			quality = float(goodCount or 0) / float(totalCount)
		else:
			quality = 1.0
		system.tag.writeBlocking([oeeQualityPath], [quality])
		debugPrint("Quality: %.2f%%" % (quality * 100))

		# Performance = Total / Target
		if targetCount and targetCount > 0:
			performance = float(totalCount or 0) / float(targetCount)
		else:
			performance = 1.0
		system.tag.writeBlocking([oeePerformancePath], [performance])
		debugPrint("Performance: %.2f%%" % (performance * 100))

		# Availability = Run Time / Total Time (totalTime already read in the batch above)
		if totalTime and totalTime > 0:
			availability = float(runTime or 0) / float(totalTime)
		else:
			availability = 1.0
		system.tag.writeBlocking([oeeAvailabilityPath], [availability])
		debugPrint("Availability: %.2f%%" % (availability * 100))

		# OEE roll-up is the UDT "OEE" expression = Availability * Performance * Quality.
		# getOee writes only the three memory tags above; the UDT recomputes OEE from them.
		finalOEE = availability * performance * quality
		debugPrint("========== Final OEE: %.2f%% ==========" % (finalOEE * 100))
		
	except Exception as e:
		import traceback
		debugPrint("ERROR: %s" % str(e))
		debugPrint("Traceback: %s" % traceback.format_exc())
		logger.error("getOee error: %s" % traceback.format_exc())
		raise

# Legacy function for backward compatibility
def getRunOee(parentPath, runID):
	"""Calculate OEE for a specific run"""
	return getOee(parentPath, runID)


logger.info("Optimized MES Core OEE Library (PostgreSQL) loaded successfully")


def calcRunTheoreticalOee(runID, db=db):
	"""After-the-fact: compute theoretical Performance and OEE for a run from
	values already stored on the run row. A and Q are rate-independent.
	Returns None outputs (not 1.0) when the theoretical rate is missing/zero."""
	try:
		row = system.db.runPrepQuery('''
			SELECT runtime, totalcount, availability, quality, theoretical_rate
			FROM run WHERE id = ?
		''', [runID], db)
		if len(row) == 0:
			return 0

		runTime         = row[0]['runtime'] or 0
		totalCount      = row[0]['totalcount'] or 0
		availability    = row[0]['availability']
		quality         = row[0]['quality']
		theoreticalRate = row[0]['theoretical_rate']

		perfTheo = None
		if theoreticalRate and theoreticalRate > 0 and runTime > 0:
			targetTheo = (runTime / 3600.0) * theoreticalRate
			if targetTheo > 0:
				perfTheo = float(totalCount) / targetTheo

		oeeTheo = None
		if perfTheo is not None and availability is not None and quality is not None:
			oeeTheo = availability * perfTheo * quality

		system.db.runPrepUpdate('''
			UPDATE run SET performance_theoretical = ?, oee_theoretical = ?
			WHERE id = ?
		''', [perfTheo, oeeTheo, runID], db)
		return 1

	except Exception as e:
		logger.error("calcRunTheoreticalOee error for runID %s: %s" % (runID, str(e)))
		return 0


def recalcTheoreticalForRange(startDate, endDate, lineID=None, db=db):
	"""Backfill helper: recompute theoretical OEE for closed runs in a window.
	Run once after entering rates to populate history."""
	q = '''SELECT r.id FROM run r
		   JOIN schedule sch ON r.scheduleid = sch.id
		   WHERE r.closed = true AND r.runstartdatetime BETWEEN ? AND ?'''
	params = [startDate, endDate]
	if lineID is not None:
		q += ' AND sch.lineid = ?'
		params.append(lineID)
	for row in system.db.runPrepQuery(q, params, db):
		calcRunTheoreticalOee(row[0], db)
	return 1
	
# Dedicated logger for the shift block. Do NOT rebind the module `logger` here — it is a
# module global resolved at call time, so rebinding it would silently reroute every OEE
# function above to "MES_Shift" and point error triage at the wrong logger.
shiftLogger = system.util.getLogger("MES_Shift")

def calcShiftOee(lineID, shiftId, shiftDate, db=db):
	"""Standard + theoretical OEE for one line over one shift window.
	After-the-fact: windowed counts, downtime clipped to the window,
	Performance derived per product. shiftDate as 'yyyy-MM-dd'.
	Negative count rows (counter resets / new-run restarts) are excluded,
	matching the run-level OEE convention."""
	try:
		w = system.db.runPrepQuery('''
			SELECT (CAST(? AS date) + start_time) AS shift_start,
			       (CAST(? AS date) + end_time
			           + (CASE WHEN crosses_midnight THEN INTERVAL '1 day' ELSE INTERVAL '0' END)) AS shift_end
			FROM shift WHERE id = ?
		''', [shiftDate, shiftDate, shiftId], db)
		if len(w) == 0:
			shiftLogger.warn("calcShiftOee: shift %s not found" % shiftId); return 0
		shiftStart = w[0]['shift_start']; shiftEnd = w[0]['shift_end']
		elapsed = (system.date.toMillis(shiftEnd) - system.date.toMillis(shiftStart)) / 1000.0

		# counts in window (good=2, waste=3); exclude negative reset deltas
		good = 0; waste = 0
		for row in system.db.runPrepQuery('''
				SELECT ch.counttypeid, COALESCE(SUM(ch.count),0) AS cnt
				FROM counthistory ch JOIN counttag ct ON ch.tagid = ct.id
				WHERE ct.parentid = ? AND ch."TimeStamp" BETWEEN ? AND ? AND ch.counttypeid IN (2,3) AND ch.count >= 0
				GROUP BY ch.counttypeid''', [lineID, shiftStart, shiftEnd], db):
			if row['counttypeid'] == 2: good = row['cnt']
			elif row['counttypeid'] == 3: waste = row['cnt']
		total = good + waste

		# downtime clipped to the window
		def clipped(flagCol):
			q = '''SELECT COALESCE(SUM(EXTRACT(EPOCH FROM (
			          LEAST(COALESCE(s.enddatetime, ?), ?) - GREATEST(s.startdatetime, ?)))),0) AS secs
			       FROM statehistory s JOIN statereason st ON s.statereasonid = st.id
			       WHERE st.%s = true AND s.lineid = ?
			         AND s.startdatetime < ? AND COALESCE(s.enddatetime, ?) > ?''' % flagCol
			r = system.db.runPrepQuery(q, [shiftEnd, shiftEnd, shiftStart, lineID, shiftEnd, shiftEnd, shiftStart], db)
			return r[0]['secs'] if len(r) else 0
		unplannedDt = clipped('recorddowntime'); plannedDt = clipped('planneddowntime')

		totalTime = max(0, elapsed - plannedDt)
		runTime   = max(0, totalTime - unplannedDt)
		quality      = (float(good)/float(total)) if total > 0 else 1.0
		availability = (runTime/totalTime) if totalTime > 0 else 1.0

		# Performance per product: ideal hours (count/rate) / actual run hours; exclude negatives
		idealStd = 0.0; idealTheo = 0.0; haveStd = False; haveTheo = False
		for row in system.db.runPrepQuery('''
				SELECT pcr.standard_rate AS sr, pcr.theoretical_rate AS tr, COALESCE(SUM(ch.count),0) AS cnt
				FROM counthistory ch
				JOIN counttag ct ON ch.tagid = ct.id
				JOIN run r ON ch.runid = r.id
				JOIN schedule sch ON r.scheduleid = sch.id
				JOIN workorder wo ON sch.workorderid = wo.id
				LEFT JOIN productcoderate pcr ON pcr.productcodeid = wo.productcodeid
				WHERE ct.parentid = ? AND ch."TimeStamp" BETWEEN ? AND ? AND ch.counttypeid IN (2,3) AND ch.count >= 0
				GROUP BY pcr.standard_rate, pcr.theoretical_rate''', [lineID, shiftStart, shiftEnd], db):
			cnt = float(row['cnt'] or 0)
			if row['sr'] and row['sr'] > 0: idealStd += cnt/float(row['sr']); haveStd = True
			if row['tr'] and row['tr'] > 0: idealTheo += cnt/float(row['tr']); haveTheo = True
		runHours = runTime/3600.0
		performance     = (idealStd/runHours)  if (haveStd  and runHours > 0) else None
		performanceTheo = (idealTheo/runHours) if (haveTheo and runHours > 0) else None
		oee     = (availability*performance*quality)     if performance     is not None else None
		oeeTheo = (availability*performanceTheo*quality)  if performanceTheo is not None else None

		system.db.runPrepUpdate('''
			INSERT INTO shift_oee (lineid, shiftid, shift_date, shift_start, shift_end,
				totaltime, runtime, planneddowntime, unplanneddowntime,
				totalcount, goodcount, wastecount, availability, performance, quality, oee,
				performance_theoretical, oee_theoretical, "TimeStamp")
			VALUES (?,?,CAST(? AS date),?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,NOW())
			ON CONFLICT (lineid, shiftid, shift_date) DO UPDATE SET
				shift_start=EXCLUDED.shift_start, shift_end=EXCLUDED.shift_end,
				totaltime=EXCLUDED.totaltime, runtime=EXCLUDED.runtime,
				planneddowntime=EXCLUDED.planneddowntime, unplanneddowntime=EXCLUDED.unplanneddowntime,
				totalcount=EXCLUDED.totalcount, goodcount=EXCLUDED.goodcount, wastecount=EXCLUDED.wastecount,
				availability=EXCLUDED.availability, performance=EXCLUDED.performance,
				quality=EXCLUDED.quality, oee=EXCLUDED.oee,
				performance_theoretical=EXCLUDED.performance_theoretical,
				oee_theoretical=EXCLUDED.oee_theoretical, "TimeStamp"=NOW()
		''', [lineID, shiftId, shiftDate, shiftStart, shiftEnd, totalTime, runTime, plannedDt, unplannedDt,
		      total, good, waste, availability, performance, quality, oee, performanceTheo, oeeTheo], db)
		shiftLogger.info("Shift OEE: line %s shift %s %s" % (lineID, shiftId, shiftDate))
		return 1
	except Exception as e:
		import traceback
		shiftLogger.error("calcShiftOee error: %s" % traceback.format_exc()); return 0


def shiftDateForNow(shiftId, db=db):
	"""Date to attribute to a shift ending ~now (yesterday for a night shift)."""
	sh = system.db.runPrepQuery("SELECT crosses_midnight FROM shift WHERE id = ?", [shiftId], db)
	now = system.date.now()
	d = system.date.addDays(now, -1) if (len(sh) and sh[0]['crosses_midnight']) else now
	return system.date.format(d, "yyyy-MM-dd")


def runShiftForLines(shiftId, shiftDate, db=db):
	"""Compute a shift for every line it applies to (all lines if shift.lineid is NULL)."""
	sh = system.db.runPrepQuery("SELECT lineid FROM shift WHERE id = ? AND enabled = true", [shiftId], db)
	if len(sh) == 0: return 0
	scope = sh[0]['lineid']
	lines = [scope] if scope is not None else [r['id'] for r in system.db.runPrepQuery("SELECT id FROM line", [], db)]
	for lid in lines:
		calcShiftOee(lid, shiftId, shiftDate, db)
	return len(lines)


def recalcShiftRange(startDate, endDate, db=db):
	"""Backfill: recompute every enabled shift for each day in the range."""
	shifts = [r['id'] for r in system.db.runPrepQuery("SELECT id FROM shift WHERE enabled = true", [], db)]
	d = system.date.parse(startDate, "yyyy-MM-dd")
	end = system.date.parse(endDate, "yyyy-MM-dd")
	while not system.date.isAfter(d, end):
		ds = system.date.format(d, "yyyy-MM-dd")
		for sid in shifts:
			runShiftForLines(sid, ds, db)
		d = system.date.addDays(d, 1)
	return 1