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
MES Core Run Management - PostgreSQL Version

MySQL to PostgreSQL conversions:
- Column aliases: 'Name' -> "Name" (double quotes)
- Column names: Mixed case -> lowercase
- Booleans: 0/1 -> false/true
- Timestamps: str(datetime) -> pass directly
- now() -> CURRENT_TIMESTAMP
'''

from mes_core import config

db = config.DB
logger = system.util.getLogger("MES_Run")


def calcFinishTime(parentPath, db=db):
	"""Calculate estimated finish time and write it to the Estimated Finish Time tag."""
	estPath = parentPath + '/OEE/Estimated Finish Time'

	query = """
		SELECT
			r.id AS "ID",
			wo.workorder AS "WorkOrder",
			r.runstartdatetime AS "StartTime",
			sch.schedulefinishdatetime AS "FinishTime",
			sch.quantity AS "Quantity"
		FROM run r
		LEFT JOIN schedule sch ON r.scheduleid = sch.id
		LEFT JOIN workorder wo ON sch.workorderid = wo.id
		WHERE r.id = ?
		AND r.closed = false
	"""

	runID = system.tag.readBlocking([parentPath + '/OEE/RunID'])[0].value

	if runID is not None and runID > config.RUN_ID_SENTINEL:
		runData = system.db.runPrepQuery(query, [runID], db)

		if len(runData) == 0:
			system.tag.writeBlocking([estPath], [None])
			return 'No Order'

		quantity = runData[0]['Quantity']
		if quantity is None:
			quantity = 0

		goodParts = system.tag.readBlocking([parentPath + '/OEE/Good Count'])[0].value
		if goodParts is None:
			goodParts = 0

		# Clamp so hitting/exceeding target doesn't push the estimate into the past
		remainingParts = max(0, quantity - goodParts)

		productionRate = system.tag.readBlocking([parentPath + '/OEE/Production Rate'])[0].value
		if productionRate is None or productionRate <= 0:
			productionRate = 1

		currentTime = system.date.now()
		hoursRemaining = float(remainingParts) / float(productionRate)
		secondsRemaining = int(round(hoursRemaining * 3600))
		finishTime = system.date.addSeconds(currentTime, secondsRemaining)

		system.tag.writeBlocking([estPath], [finishTime])
		return finishTime
	else:
		system.tag.writeBlocking([estPath], [None])
		return 'No Order'


def updateRun(runID, db=db):
	"""Update run record with current tag values"""
	try:
		# PostgreSQL: lowercase columns, double-quoted aliases
		lineQuery = """
			SELECT 
				l.id AS "Line ID", 
				CONCAT('[default]', e.name, '/', s.name, '/', a.name, '/', l.name, '/Line') AS "Line Path" 
			FROM run r
			LEFT JOIN schedule sch ON r.scheduleid = sch.id
			LEFT JOIN line l ON sch.lineid = l.id
			LEFT JOIN area a ON l.parentid = a.id
			LEFT JOIN site s ON a.parentid = s.id
			LEFT JOIN enterprise e ON s.parentid = e.id
			WHERE r.id = ?
		"""
		
		data = system.db.runPrepQuery(lineQuery, [runID], db)
		
		if len(data) == 0:
			logger.warn("No line found for runID: %s" % runID)
			return 0
		
		linePath = data[0]['Line Path']
		
		# Calculate Finish Time
		finishTime = calcFinishTime(linePath)
		
		# Get timestamp
		timestamp = system.date.now()
		
		# Shared OEE snapshot (mes_core.tags) - bulk read, null-coalesced to 0
		snap = mes_core.tags.readOeeSnapshot(linePath)

		# PostgreSQL: lowercase columns, pass timestamps directly
		query = """
			UPDATE run SET
				currentinfeed = ?,
				currentoutfeed = ?,
				currentwaste = ?,
				totalcount = ?,
				wastecount = ?,
				goodcount = ?,
				availability = ?,
				performance = ?,
				quality = ?,
				oee = ?,
				runtime = ?,
				unplanneddowntime = ?,
				planneddowntime = ?,
				totaltime = ?,
				"TimeStamp" = ?,
				closed = ?,
				estimatedfinishtime = ?
			WHERE id = ?
		"""
		
		# Handle finishTime - convert to timestamp if it's a string
		finishTimeValue = finishTime if finishTime != 'No Order' else None
		
		args = [
			snap['infeed'], snap['outfeed'], snap['waste'], snap['totalCount'], snap['badCount'], snap['goodCount'],
			snap['availability'], snap['performance'], snap['quality'], snap['oee'],
			snap['runTime'], snap['unplannedDowntime'], snap['plannedDowntime'], snap['totalTime'],
			timestamp, False, finishTimeValue, runID
		]
		
		system.db.runPrepUpdate(query, args, db)
		
		return 1
		
	except Exception as e:
		logger.error("updateRun error for runID %s: %s" % (runID, str(e)))
		return 0


def startRun(scheduleId, linePath, lineID):
	"""Start a new run for a schedule. Creates a run record and updates tags."""
	try:
		timestamp = system.date.now()

		infeedPath     = linePath + '/Dispatch/OEE Infeed/Count'
		outfeedPath    = linePath + '/Dispatch/OEE Outfeed/Count'
		wastePath      = linePath + '/Dispatch/OEE Waste/Count'
		runIdPath      = linePath + '/OEE/RunID'
		startTimePath  = linePath + '/Start Time'
		runEnabledPath = linePath + '/Run Enabled'

		results = system.tag.readBlocking([infeedPath, outfeedPath, wastePath])
		infeed  = results[0].value if results[0].value is not None else 0
		outfeed = results[1].value if results[1].value is not None else 0
		waste   = results[2].value if results[2].value is not None else 0

		# Snapshot the rates this run will be measured against
		rateData = system.db.runPrepQuery('''
			SELECT pcr.standard_rate, pcr.theoretical_rate
			FROM schedule sch
			JOIN workorder wo ON sch.workorderid = wo.id
			JOIN productcoderate pcr ON pcr.productcodeid = wo.productcodeid
			WHERE sch.id = ?
		''', [scheduleId], db)
		standardRate    = rateData[0]['standard_rate']    if len(rateData) else None
		theoreticalRate = rateData[0]['theoretical_rate'] if len(rateData) else None
		if len(rateData) == 0:
			logger.warn("startRun: no rate row for schedule %s; theoretical OEE will be null" % scheduleId)

		query = '''
			INSERT INTO run (
				scheduleid, runstartdatetime, startinfeed, startoutfeed, currentoutfeed,
				startwaste, currentwaste, totalcount, wastecount, goodcount,
				availability, performance, quality, oee, runtime,
				unplanneddowntime, planneddowntime, totaltime,
				standard_rate, theoretical_rate,
				"TimeStamp", closed
			) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		'''
		args = [
			scheduleId, timestamp, infeed, outfeed, 0,
			waste, 0, 0, 0, 0,
			0, 0, 0, 0, 0,
			0, 0, 0,
			standardRate, theoreticalRate,
			timestamp, False
		]

		runID = system.db.runPrepUpdate(query, args, db, getKey=True)
		system.tag.writeBlocking([runIdPath, startTimePath, runEnabledPath], [runID, timestamp, 1])

		# Push the snapshotted standard rate to the tag so the UDT Target Count expression
		# ((Standard Rate / 3600) * Run Time) is non-zero, and getOee Performance (Total / Target)
		# doesn't fall back to its 1.0 default. OEE/Standard Rate is a memory tag defaulting to 0
		# that nothing else writes.
		if standardRate is not None:
			system.tag.writeBlocking([linePath + '/OEE/Standard Rate'], [standardRate])

		logger.info("Started run %s for schedule %s on %s" % (runID, scheduleId, linePath))
		return 1

	except Exception as e:
		logger.error("startRun failed: %s" % str(e))
		return 0


def stopRun(runID):
	"""
	Stop an active run.
	Updates the run record with final values and disables the run.
	"""
	try:
		# PostgreSQL: lowercase columns, double-quoted aliases
		lineQuery = """
			SELECT
				l.id AS "Line ID",
				CONCAT('[default]', e.name, '/', s.name, '/', a.name, '/', l.name, '/Line') AS "Line Path"
			FROM run r
			LEFT JOIN schedule sch ON r.scheduleid = sch.id
			LEFT JOIN line l ON sch.lineid = l.id
			LEFT JOIN area a ON l.parentid = a.id
			LEFT JOIN site s ON a.parentid = s.id
			LEFT JOIN enterprise e ON s.parentid = e.id
			WHERE r.id = ?
		"""

		data = system.db.runPrepQuery(lineQuery, [runID], db)

		if len(data) == 0:
			logger.warn("No line found for runID: %s" % runID)
			return 0

		linePath = data[0]['Line Path']

		timestamp = system.date.now()

		# Shared OEE snapshot (mes_core.tags) - bulk read, null-coalesced to 0
		snap = mes_core.tags.readOeeSnapshot(linePath)

		# PostgreSQL: lowercase columns
		query = """
			UPDATE run SET
				runstopdatetime = ?,
				currentinfeed = ?,
				currentoutfeed = ?,
				currentwaste = ?,
				totalcount = ?,
				wastecount = ?,
				goodcount = ?,
				availability = ?,
				performance = ?,
				quality = ?,
				oee = ?,
				runtime = ?,
				unplanneddowntime = ?,
				planneddowntime = ?,
				totaltime = ?,
				"TimeStamp" = ?,
				closed = ?
			WHERE id = ?
		"""

		args = [
			timestamp, snap['infeed'], snap['outfeed'], snap['waste'],
			snap['totalCount'], snap['badCount'], snap['goodCount'],
			snap['availability'], snap['performance'], snap['quality'], snap['oee'],
			snap['runTime'], snap['unplannedDowntime'], snap['plannedDowntime'], snap['totalTime'],
			timestamp, True, runID
		]

		system.db.runPrepUpdate(query, args, db)

		# Run row is finalized above; both calls below read the committed row.
		# Compute theoretical Performance / OEE for this run (after-the-fact).
		try:
			mes_core.oee.calcRunTheoreticalOee(runID)
		except Exception as e:
			logger.error("theoretical OEE calc failed for run %s: %s" % (runID, str(e)))

		# Roll the run actuals up into the schedule row for this work order.
		try:
			updateScheduleActuals(runID)
		except Exception as e:
			logger.error("schedule actuals update failed for run %s: %s" % (runID, str(e)))

		# Reset tags. A3: also clear OEE/Standard Rate (written at startRun) so the
		# next run on this line cannot inherit a stale rate.
		runIdPath = linePath + '/OEE/RunID'
		runEnabledPath = linePath + '/Run Enabled'
		standardRatePath = linePath + '/OEE/Standard Rate'
		system.tag.writeBlocking([runIdPath, runEnabledPath, standardRatePath], [config.RUN_ID_SENTINEL, 0, 0])

		logger.info("Stopped run %s" % runID)
		return 1

	except Exception as e:
		logger.error("stopRun failed for runID %s: %s" % (runID, str(e)))
		return 0


def cancelRun(runID, linePath):
	"""
	Cancel a run - removes the run record and resets tags.
	"""
	try:
		# PostgreSQL: lowercase column names
		# Update counthistory to disassociate from this run.
		# "No run" is NULL in both history tables (statehistory below uses NULL too);
		# -1 is reserved only for the non-nullable Int RunID tag.
		query = '''UPDATE counthistory SET runid = NULL WHERE runid = ?'''
		system.db.runPrepUpdate(query, [runID], db)
		
		# Update statehistory to disassociate from this run
		stateQuery = '''UPDATE statehistory SET runid = NULL WHERE runid = ?'''
		system.db.runPrepUpdate(stateQuery, [runID], db)
		
		# Delete the run record
		runQuery = '''DELETE FROM run WHERE id = ?'''
		system.db.runPrepUpdate(runQuery, [runID], db)
		
		# Reset tags. A3: also clear OEE/Standard Rate (written at startRun) so the
		# next run on this line cannot inherit a stale rate.
		runEnabledPath = linePath + '/Run Enabled'
		runIDPath = linePath + '/OEE/RunID'
		standardRatePath = linePath + '/OEE/Standard Rate'
		system.tag.writeBlocking([runEnabledPath, runIDPath, standardRatePath], [0, config.RUN_ID_SENTINEL, 0])
		
		logger.info("Cancelled run %s" % runID)
		return 1
		
	except Exception as e:
		logger.error("cancelRun failed for runID %s: %s" % (runID, str(e)))
		return 0
		
		
def updateScheduleActuals(runID, db=db):
	"""Roll a run's actuals up into its schedule row when a work order finishes.
	Aggregates across ALL runs for that schedule, so a stop/restart (multiple
	runs on one schedule) still produces correct totals."""
	try:
		sch = system.db.runPrepQuery("SELECT scheduleid FROM run WHERE id = ?", [runID], db)
		if len(sch) == 0 or sch[0]['scheduleid'] is None:
			logger.warn("updateScheduleActuals: no schedule for run %s" % runID)
			return 0
		scheduleId = sch[0]['scheduleid']

		query = '''
			UPDATE schedule SET
				runid                = ?,
				actualstartdatetime  = (SELECT MIN(runstartdatetime) FROM run WHERE scheduleid = ?),
				actualfinishdatetime = (SELECT MAX(COALESCE(runstopdatetime, CURRENT_TIMESTAMP)) FROM run WHERE scheduleid = ?),
				actualquantity       = (SELECT SUM(goodcount) FROM run WHERE scheduleid = ?),
				runstartdatetime     = (SELECT MIN(runstartdatetime) FROM run WHERE scheduleid = ?)
			WHERE id = ?
		'''
		system.db.runPrepUpdate(
			query,
			[runID, scheduleId, scheduleId, scheduleId, scheduleId, scheduleId],
			db
		)
		logger.info("Updated schedule %s actuals from run %s" % (scheduleId, runID))
		return 1

	except Exception as e:
		logger.error("updateScheduleActuals error for run %s: %s" % (runID, str(e)))
		return 0
		