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

db = 'mes_core'
logger = system.util.getLogger("MES_Run")


def calcFinishTime(parentPath, db=db):
	"""Calculate estimated finish time based on production rate"""
	
	# PostgreSQL: lowercase columns, double-quoted aliases
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
	
	if runID is not None and runID > -1:
		runData = system.db.runPrepQuery(query, [runID], db)
		
		if len(runData) == 0:
			return 'No Order'
		
		quantity = runData[0]['Quantity']
		if quantity is None:
			quantity = 0
		
		# Calculate remaining parts
		goodParts = system.tag.readBlocking([parentPath + '/OEE/Good Count'])[0].value
		if goodParts is None:
			goodParts = 0
		
		remainingParts = quantity - goodParts
		
		productionRate = system.tag.readBlocking([parentPath + '/OEE/Production Rate'])[0].value
		if productionRate is None or productionRate <= 0:
			productionRate = 1
		
		# Calculate finish time
		currentTime = system.date.now()
		hoursRemaining = float(remainingParts) / float(productionRate)
		finishTime = system.date.addHours(currentTime, hoursRemaining)
		
		return finishTime
	else:
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
		
		lineID = data[0]['Line ID']
		linePath = data[0]['Line Path']
		
		# Calculate Finish Time
		finishTime = calcFinishTime(linePath)
		
		# Get timestamp
		timestamp = system.date.now()
		
		# Tag paths
		paths = [
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
		
		# Read all tags at once
		results = system.tag.readBlocking(paths)
		
		infeed = results[0].value if results[0].value is not None else 0
		outfeed = results[1].value if results[1].value is not None else 0
		waste = results[2].value if results[2].value is not None else 0
		totalCount = results[3].value if results[3].value is not None else 0
		badCount = results[4].value if results[4].value is not None else 0
		goodCount = results[5].value if results[5].value is not None else 0
		quality = results[6].value if results[6].value is not None else 0
		performance = results[7].value if results[7].value is not None else 0
		availability = results[8].value if results[8].value is not None else 0
		oee = results[9].value if results[9].value is not None else 0
		runTime = results[10].value if results[10].value is not None else 0
		unplannedDowntime = results[11].value if results[11].value is not None else 0
		plannedDowntime = results[12].value if results[12].value is not None else 0
		totalTime = results[13].value if results[13].value is not None else 0
		
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
			infeed, outfeed, waste, totalCount, badCount, goodCount,
			availability, performance, quality, oee,
			runTime, unplannedDowntime, plannedDowntime, totalTime,
			timestamp, False, finishTimeValue, runID
		]
		
		system.db.runPrepUpdate(query, args, db)
		
		return 1
		
	except Exception as e:
		logger.error("updateRun error for runID %s: %s" % (runID, str(e)))
		return 0


def startRun(scheduleId, linePath, lineID):
	"""
	Start a new run for a schedule.
	Creates a new run record and updates relevant tags.
	"""
	try:
		timestamp = system.date.now()
		
		# Tag paths
		infeedPath = linePath + '/Dispatch/OEE Infeed/Count'
		outfeedPath = linePath + '/Dispatch/OEE Outfeed/Count'
		wastePath = linePath + '/Dispatch/OEE Waste/Count'
		runIdPath = linePath + '/OEE/RunID'
		startTimePath = linePath + '/Start Time'
		runEnabledPath = linePath + '/Run Enabled'
		
		# Get starting counts
		results = system.tag.readBlocking([infeedPath, outfeedPath, wastePath])
		infeed = results[0].value if results[0].value is not None else 0
		outfeed = results[1].value if results[1].value is not None else 0
		waste = results[2].value if results[2].value is not None else 0
		
		# PostgreSQL: lowercase column names, pass timestamp directly
		query = '''
			INSERT INTO run (
				scheduleid,
				runstartdatetime,
				startinfeed,
				startoutfeed,
				currentoutfeed,
				startwaste,
				currentwaste,
				totalcount,
				wastecount,
				goodcount,
				availability,
				performance,
				quality,
				oee,
				runtime,
				unplanneddowntime,
				planneddowntime,
				totaltime,
				"TimeStamp",
				closed
			) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
		'''
		
		args = [
			scheduleId,
			timestamp,
			infeed,
			outfeed,
			0,
			waste,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			0,
			timestamp,
			False
		]
		
		runID = system.db.runPrepUpdate(query, args, db, getKey=True)
		
		# Write to tags
		system.tag.writeBlocking([runIdPath, startTimePath, runEnabledPath], [runID, timestamp, 1])
		
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
		
		lineID = data[0]['Line ID']
		linePath = data[0]['Line Path']
		
		timestamp = system.date.now()
		
		# Tag paths - read all at once for efficiency
		paths = [
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
		
		results = system.tag.readBlocking(paths)
		
		infeed = results[0].value if results[0].value is not None else 0
		outfeed = results[1].value if results[1].value is not None else 0
		waste = results[2].value if results[2].value is not None else 0
		totalCount = results[3].value if results[3].value is not None else 0
		badCount = results[4].value if results[4].value is not None else 0
		goodCount = results[5].value if results[5].value is not None else 0
		quality = results[6].value if results[6].value is not None else 0
		performance = results[7].value if results[7].value is not None else 0
		availability = results[8].value if results[8].value is not None else 0
		oee = results[9].value if results[9].value is not None else 0
		runTime = results[10].value if results[10].value is not None else 0
		unplannedDowntime = results[11].value if results[11].value is not None else 0
		plannedDowntime = results[12].value if results[12].value is not None else 0
		totalTime = results[13].value if results[13].value is not None else 0
		
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
			timestamp, infeed, outfeed, waste,
			totalCount, badCount, goodCount,
			availability, performance, quality, oee,
			runTime, unplannedDowntime, plannedDowntime, totalTime,
			timestamp, True, runID
		]
		
		system.db.runPrepUpdate(query, args, db)
		
		# Reset tags
		runIdPath = linePath + '/OEE/RunID'
		runEnabledPath = linePath + '/Run Enabled'
		system.tag.writeBlocking([runIdPath, runEnabledPath], [-1, 0])
		
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
		# Update counthistory to disassociate from this run
		query = '''UPDATE counthistory SET runid = -1 WHERE runid = ?'''
		system.db.runPrepUpdate(query, [runID], db)
		
		# Update statehistory to disassociate from this run
		stateQuery = '''UPDATE statehistory SET runid = NULL WHERE runid = ?'''
		system.db.runPrepUpdate(stateQuery, [runID], db)
		
		# Delete the run record
		runQuery = '''DELETE FROM run WHERE id = ?'''
		system.db.runPrepUpdate(runQuery, [runID], db)
		
		# Reset tags
		runEnabledPath = linePath + '/Run Enabled'
		runIDPath = linePath + '/OEE/RunID'
		system.tag.writeBlocking([runEnabledPath, runIDPath], [0, -1])
		
		logger.info("Cancelled run %s" % runID)
		return 1
		
	except Exception as e:
		logger.error("cancelRun failed for runID %s: %s" % (runID, str(e)))
		return 0
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		
		