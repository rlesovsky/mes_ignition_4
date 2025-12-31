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
REFACTORED: PostgreSQL compatibility + Optimized tag reads
- Batched system.tag.readBlocking calls for performance
- Batched system.tag.writeBlocking calls where possible
'''

db = 'mes_core'

def calcFinishTime(parentPath, db=db):
	from datetime import datetime, timedelta
	
	query = """
		SELECT r.id AS id, wo.workorder AS workorder, r.runstartdatetime AS starttime, sch.schedulefinishdatetime AS finishtime,
		sch.quantity AS quantity FROM run r
		LEFT JOIN schedule sch
		ON r.scheduleid = sch.id
		LEFT JOIN workorder wo
		ON sch.workorderid = wo.id
		WHERE r.id = ?
		AND r.closed = FALSE
	"""
	
	# Batched tag read - get all needed values in one call
	tagPaths = [
		parentPath + '/OEE/RunID',
		parentPath + '/OEE/Good Count',
		parentPath + '/OEE/Production Rate'
	]
	tagResults = system.tag.readBlocking(tagPaths)
	runID = tagResults[0].value
	goodParts = tagResults[1].value
	productionRate = tagResults[2].value
	
	if runID > -1:
		
		runData = system.db.runPrepQuery(query,[runID],db)
		# get order quantity from run table
		
		# Check if we got results
		if len(runData) == 0:
			return 'No Run Data'
		
		quantity = None
		for row in runData:
			quantity = row['quantity']
		
		if quantity is None:
			return 'No Quantity'
			
		#calculate how many parts remain to produce
		remainingParts = quantity - goodParts
		
		#get current time and hours remaining in order
		currentTime = datetime.now().replace(microsecond=0)
		
		if productionRate > 0:
			pass
		else:
			productionRate = 1
			
		hoursRemaining = remainingParts/productionRate
		
		#calc estimated finish time by adding remaining hours to current time
		finishTime = currentTime + timedelta(hours=hoursRemaining)
		return finishTime.replace(microsecond=0)
		
	else:
		return 'No Order'
		
		
		
def updateRun(runID, db=db):
	try:
		from datetime import datetime
		from java.lang import Exception
		
		#build a query to retrieve lineID and linePath
		
		lineQuery = """
			SELECT l.id AS "Line ID", CONCAT('[default]',e.name,'/',s.name,'/',a.name,'/',l.name,'/Line') AS "Line Path" 
			FROM run r
			LEFT JOIN schedule sch
			ON r.scheduleid = sch.id
			LEFT JOIN line l
			ON sch.lineid = l.id
			LEFT JOIN area a
			ON l.parentid = a.id
			LEFT JOIN site s
			ON a.parentid = s.id
			LEFT JOIN enterprise e
			ON s.parentid = e.id
			WHERE r.id = ?
		"""
		
		data = system.db.runPrepQuery(lineQuery,[runID],db)
		
		if len(data) == 0:
			return 0
			
		for row in data:
			lineID = row['Line ID']
			linePath = row['Line Path']
			
		#calculate Finish Time
		finishTime = calcFinishTime(linePath)
		
		#get TimeStamp and Format
		timeStamp = datetime.now()
		timeStamp = timeStamp.replace(microsecond=0)
		
		#tagPaths - build list for batched read
		tagPaths = [
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
			linePath + '/OEE/Runtime',
			linePath + '/OEE/Unplanned Downtime',
			linePath + '/OEE/Planned Downtime',
			linePath + '/OEE/Total Time'
		]
		
		# Batched tag read - single gateway call for all 14 tags
		tagResults = system.tag.readBlocking(tagPaths)
		
		infeed = tagResults[0].value
		outfeed = tagResults[1].value
		waste = tagResults[2].value
		totalCount = tagResults[3].value
		badCount = tagResults[4].value
		goodCount = tagResults[5].value
		quality = tagResults[6].value
		performance = tagResults[7].value
		availability = tagResults[8].value
		oee = tagResults[9].value
		runTime = tagResults[10].value
		unplannedDownTime = tagResults[11].value
		plannedDownTime = tagResults[12].value
		totalTime = tagResults[13].value
		
		#update Run
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
		
		args = [infeed,outfeed,waste,totalCount,badCount,goodCount,availability,performance,quality,oee,runTime,unplannedDownTime,plannedDownTime,totalTime,str(timeStamp),False,str(finishTime),runID]
		system.db.runPrepUpdate(query,args,db)
		
		return 1
		
	except:
		return 0
		
		


'''This script takes 1 argument, scheduleId.  The scheduleId connects the run through the schedule back to the original work order.  The pertinent tagPaths are read from
client tags and used to update the OEE and Run tags with the appropriate values.  After completion, a new runID will be created and the runID in the OEE UDT will be updated.
'''

def startRun(scheduleId,linePath,lineID):
	try:
		from datetime import datetime
		from java.lang import Exception

		timeStamp = datetime.now()
		timeStamp = timeStamp.replace(microsecond=0)
		
		#tagPaths for reading
		readPaths = [
			linePath + '/Dispatch/OEE Infeed/Count',
			linePath + '/Dispatch/OEE Outfeed/Count',
			linePath + '/Dispatch/OEE Waste/Count'
		]
		
		#tagPaths for writing
		runIdPath = linePath + '/OEE/RunID'
		startTimePath = linePath + '/Start Time'
		runEnabledPath = linePath + '/Run Enabled'
		
		# Batched tag read - single gateway call
		tagResults = system.tag.readBlocking(readPaths)
		infeed = tagResults[0].value
		outfeed = tagResults[1].value
		waste = tagResults[2].value
			
		db = 'mes_core'
		query = '''INSERT INTO run (
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
		) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?); 
		'''
		args = [scheduleId,str(timeStamp),infeed,outfeed,0,waste,0,0,0,0,0,0,0,0,0,0,0,0,str(timeStamp),False]
		
		runID = system.db.runPrepUpdate(query,args,db, getKey=True) 

		# Batched tag write - single gateway call for all 3 tags
		writePaths = [runIdPath, startTimePath, runEnabledPath]
		writeValues = [runID, timeStamp, 1]
		system.tag.writeBlocking(writePaths, writeValues)

		return 1
	
	except:
		return 0
			


'''This script takes 1 argument, runId.  The runID is passed in and used to determine the lineID and the linePath.  The pertinent tagPaths are built from the linePath
and used to update the run record and stop the run.  After completion, the runID and runEnabled tags are set to 0 in the line UDT.
'''

def stopRun(runID):
	try:
		from datetime import datetime
		from java.lang import Exception

		# build a query to retrieve the lineID and linePath
		
		db = 'mes_core'
		lineQuery = '''SELECT l.id AS "Line ID", CONCAT('[default]',e.name,'/',s.name,'/',a.name,'/',l.name,'/Line') AS "Line Path" FROM run r
						LEFT JOIN schedule sch
						ON r.scheduleid = sch.id
						LEFT JOIN line l
						ON sch.lineid = l.id
						LEFT JOIN area a
						ON l.parentid = a.id
						LEFT JOIN site s
						ON a.parentid = s.id
						LEFT JOIN enterprise e
						ON s.parentid = e.id
						WHERE r.id = ?
						'''	
						
		data = system.db.runPrepQuery(lineQuery,[runID],db)
		
		if len(data) == 0:
			return 0
			
		for row in data:
			lineID = row['Line ID']
			linePath = row['Line Path']

		timeStamp = datetime.now()
		timeStamp = timeStamp.replace(microsecond=0)
		
		#tagPaths - build list for batched read
		tagPaths = [
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
			linePath + '/OEE/Runtime',
			linePath + '/OEE/Unplanned Downtime',
			linePath + '/OEE/Planned Downtime',
			linePath + '/OEE/Total Time'
		]
		
		# Batched tag read - single gateway call for all 14 tags
		tagResults = system.tag.readBlocking(tagPaths)
		
		infeed = tagResults[0].value
		outfeed = tagResults[1].value
		waste = tagResults[2].value
		totalCount = tagResults[3].value
		badCount = tagResults[4].value
		goodCount = tagResults[5].value
		quality = tagResults[6].value
		performance = tagResults[7].value
		availability = tagResults[8].value
		oee = tagResults[9].value
		runTime = tagResults[10].value
		unplannedDowntime = tagResults[11].value
		plannedDowntime = tagResults[12].value
		totalTime = tagResults[13].value
		

		query = '''UPDATE run SET
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
		'''
		args = [str(timeStamp),infeed,outfeed,waste,totalCount,badCount,goodCount,availability,performance,quality,oee,runTime,unplannedDowntime,plannedDowntime,totalTime,str(timeStamp),True,runID]
		system.db.runPrepUpdate(query,args,db)

		# Batched tag write - single gateway call for both tags
		runIdPath = linePath + '/OEE/RunID'
		runEnabledPath = linePath + '/Run Enabled'
		system.tag.writeBlocking([runIdPath, runEnabledPath], [-1, 0])
		
		return 1
		
	except:

		return 0	
		
	
	
def cancelRun(runID, linePath):
	try:
		from datetime import datetime
		from java.lang import Exception
		
		db = 'mes_core'
		
		#in the counthistory table, set the runID to -1 where the runID = the runID that was passed in
		query = '''UPDATE counthistory SET runid = -1 WHERE id = ?'''
		args = [runID]
		system.db.runPrepUpdate(query,args,db)
		
		#delete the record from the run table for that runID
		runQuery = '''DELETE FROM run WHERE id = ?'''
		args = [runID]
		system.db.runPrepUpdate(runQuery,args,db)
		
		# Batched tag write - single gateway call for both tags
		runEnabledPath = linePath + '/Run Enabled'
		runIDPath = linePath + '/OEE/RunID'
		system.tag.writeBlocking([runEnabledPath, runIDPath], [0, -1])
		
		return 1
		
	except:

		return 0
