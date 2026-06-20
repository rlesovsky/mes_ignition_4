"""
MES Core OEE - QUARANTINED LEGACY FUNCTIONS (deprecated, off the live path)
==========================================================================
Ignition Gateway Script Library: mes_core.oeeLegacy

Moved out of mes_core.oee during the B4 refactor. A project-wide grep confirmed
ZERO callers for every function below (the live OEE path is the "Get OEE" timer
-> mes_core.oee.getOee -> UDT expressions). Retained for reference only; nothing
imports this module.

Most would fail against the current tag model anyway: Total Time / Run Time /
Target Count are UDT EXPRESSION tags and writing them returns Bad_NotWritable.
Do not re-enable without revisiting the OEE source-of-truth analysis in
REWORK_PLAN.md.
"""

import inspect

from mes_core import config

db = config.DB
DEBUG_MODE = False

logger = system.util.getLogger("MES_Core_OEE_Legacy")

def debugPrint(message, functionName=None):
	"""Minimal gated debug logger for the quarantined functions."""
	if functionName is None:
		try:
			functionName = inspect.stack()[1][3]
		except:
			functionName = "unknown"
	if DEBUG_MODE:
		logger.info("[%s] %s" % (functionName, message))
	else:
		logger.debug("[%s] %s" % (functionName, message))


def calcTotalTime(startTimePath, currentTimePath, plannedDowntimePath, totalTimePath):
	"""Calculate total elapsed time minus planned downtime"""
	debugPrint("Calculating total time")
	debugPrint("Paths - Start: %s, Current: %s, PlannedDT: %s, Total: %s" % (startTimePath, currentTimePath, plannedDowntimePath, totalTimePath))
	
	try:
		startTime = system.tag.readBlocking([startTimePath])[0].value
		currentTime = system.tag.readBlocking([currentTimePath])[0].value
		plannedDowntime = system.tag.readBlocking([plannedDowntimePath])[0].value
		
		debugPrint("Values - Start: %s, Current: %s, PlannedDT: %s" % (startTime, currentTime, plannedDowntime))
		
		if startTime is None or currentTime is None:
			debugPrint("ERROR: Start or current time is None")
			system.tag.writeBlocking([totalTimePath], [0])
			return 0
		
		# Calculate elapsed time in seconds
		elapsedMillis = currentTime - startTime
		elapsedSeconds = elapsedMillis / 1000.0
		
		# Subtract planned downtime
		totalTime = elapsedSeconds - (plannedDowntime if plannedDowntime is not None else 0)
		totalTime = max(0, totalTime)  # Ensure non-negative
		
		system.tag.writeBlocking([totalTimePath], [totalTime])
		debugPrint("Total Time calculated: %s seconds (%.2f hours)" % (totalTime, totalTime / 3600.0))
		return totalTime
		
	except Exception as e:
		debugPrint("Error calculating total time: %s" % str(e))
		logger.error("calcTotalTime error: %s" % str(e))
		system.tag.writeBlocking([totalTimePath], [0])
		return 0

def calcRunTime(totalTimePath, unplannedDowntimePath, runTimePath):
	"""Calculate run time = total time - unplanned downtime"""
	debugPrint("Calculating run time")
	debugPrint("Paths - Total: %s, UnplannedDT: %s, Run: %s" % (totalTimePath, unplannedDowntimePath, runTimePath))
	
	try:
		totalTime = system.tag.readBlocking([totalTimePath])[0].value
		unplannedDowntime = system.tag.readBlocking([unplannedDowntimePath])[0].value
		
		debugPrint("Values - Total: %s, UnplannedDT: %s" % (totalTime, unplannedDowntime))
		
		if totalTime is None:
			debugPrint("ERROR: Total time is None")
			system.tag.writeBlocking([runTimePath], [0])
			return 0
		
		runTime = totalTime - (unplannedDowntime if unplannedDowntime is not None else 0)
		runTime = max(0, runTime)  # Ensure non-negative
		
		system.tag.writeBlocking([runTimePath], [runTime])
		debugPrint("Run Time calculated: %s seconds (%.2f hours)" % (runTime, runTime / 3600.0))
		return runTime
		
	except Exception as e:
		debugPrint("Error calculating run time: %s" % str(e))
		logger.error("calcRunTime error: %s" % str(e))
		system.tag.writeBlocking([runTimePath], [0])
		return 0

def calcQuality(totalCountPath, goodCountPath, oeeQualityPath):
	debugPrint("Starting quality calculation")
	debugPrint("Paths - Total: %s, Good: %s, OEE: %s" % (totalCountPath, goodCountPath, oeeQualityPath))
	
	try:
		totalCount = system.tag.readBlocking([totalCountPath])[0].value
		goodCount = system.tag.readBlocking([goodCountPath])[0].value
		
		debugPrint("Values - Total: %s, Good: %s" % (totalCount, goodCount))
		
		if totalCount is None or totalCount == 0:
			quality = 1.0
		else:
			quality = float(goodCount if goodCount is not None else 0) / float(totalCount)
		
		system.tag.writeBlocking([oeeQualityPath], [quality])
		debugPrint("Quality calculated: %s (%.2f%%)" % (quality, quality * 100))
		return quality
		
	except Exception as e:
		debugPrint("Error in calcQuality: %s" % str(e))
		logger.error("calcQuality error: %s" % str(e))
		system.tag.writeBlocking([oeeQualityPath], [1.0])
		return 1.0

def calcAvailability(runTimePath, totalTimePath, oeeAvailabilityPath):
	debugPrint("Starting availability calculation")
	debugPrint("Paths - Runtime: %s, Total: %s, OEE: %s" % (runTimePath, totalTimePath, oeeAvailabilityPath))
	
	try:
		runTime = system.tag.readBlocking([runTimePath])[0].value
		totalTime = system.tag.readBlocking([totalTimePath])[0].value
		
		debugPrint("Values - Runtime: %s, Total: %s" % (runTime, totalTime))
		
		if totalTime is None or totalTime == 0:
			debugPrint("WARNING: Total time is 0 or None, defaulting availability to 1.0")
			availability = 1.0
		else:
			availability = float(runTime if runTime is not None else 0) / float(totalTime)
		
		system.tag.writeBlocking([oeeAvailabilityPath], [availability])
		debugPrint("Availability calculated: %s (%.2f%%)" % (availability, availability * 100))
		return availability
		
	except Exception as e:
		debugPrint("Error in calcAvailability: %s" % str(e))
		logger.error("calcAvailability error: %s" % str(e))
		system.tag.writeBlocking([oeeAvailabilityPath], [1.0])
		return 1.0

def calcPerformance(totalCountPath, targetCountPath, oeePerformancePath):
	debugPrint("Starting performance calculation")
	debugPrint("Paths - Total: %s, Target: %s, OEE: %s" % (totalCountPath, targetCountPath, oeePerformancePath))
	
	try:
		totalCount = system.tag.readBlocking([totalCountPath])[0].value
		targetCount = system.tag.readBlocking([targetCountPath])[0].value
		
		debugPrint("Values - Total: %s, Target: %s" % (totalCount, targetCount))
		
		if targetCount is None or targetCount == 0:
			debugPrint("WARNING: Target count is 0 or None, defaulting performance to 1.0")
			performance = 1.0
		else:
			performance = float(totalCount if totalCount is not None else 0) / float(targetCount)
		
		system.tag.writeBlocking([oeePerformancePath], [performance])
		debugPrint("Performance calculated: %s (%.2f%%)" % (performance, performance * 100))
		return performance
		
	except Exception as e:
		debugPrint("Error in calcPerformance: %s" % str(e))
		logger.error("calcPerformance error: %s" % str(e))
		system.tag.writeBlocking([oeePerformancePath], [1.0])
		return 1.0

def getGoodCount(goodCountPath, startTimePath, endTimePath, tagID, countTypeID, runID=None, db=db):
	debugPrint("Getting good count - Tag: %s, Type: %s, Run: %s" % (tagID, countTypeID, runID))
	
	try:
		startTime = system.tag.readBlocking([startTimePath])[0].value
		endTime = system.tag.readBlocking([endTimePath])[0].value
		debugPrint("Time range: %s to %s" % (startTime, endTime))
		
		# Choose query based on whether we have a runID
		if runID is not None:
			query = '''
				SELECT SUM(count) FROM counthistory
				WHERE tagid = ? AND counttypeid = ? AND runid = ?
				AND count >= 0
			'''
			params = [tagID, countTypeID, runID]
			debugPrint("Using run-based query with RunID: %s" % runID)
		else:
			query = '''
				SELECT SUM(count) FROM counthistory
				WHERE tagid = ? AND counttypeid = ? 
				AND "TimeStamp" BETWEEN ? AND ?
				AND count >= 0
			'''
			params = [tagID, countTypeID, startTime, endTime]
			debugPrint("Using time-based query from %s to %s" % (startTime, endTime))
		
		debugPrint("Query: %s" % query)
		debugPrint("Params: %s" % str(params))
		data = system.db.runPrepQuery(query, params, db)
		debugPrint("Query returned %s rows" % len(data))
		
		goodCount = 0
		for row in data:
			goodCount = row[0] if row[0] is not None else 0
			
		system.tag.writeBlocking([goodCountPath], [goodCount])
		debugPrint("Good count: %s" % goodCount)
		return goodCount
		
	except Exception as e:
		debugPrint("Error getting good count: %s" % str(e))
		logger.error("getGoodCount error: %s" % str(e))
		system.tag.writeBlocking([goodCountPath], [0])
		return 0

def getBadCount(badCountPath, startTimePath, endTimePath, tagID, countTypeID, runID=None, db=db):
	debugPrint("Getting bad count - Tag: %s, Type: %s, Run: %s" % (tagID, countTypeID, runID))
	
	try:
		startTime = system.tag.readBlocking([startTimePath])[0].value
		endTime = system.tag.readBlocking([endTimePath])[0].value
		
		# Choose query based on whether we have a runID
		if runID is not None:
			query = '''
				SELECT SUM(count) FROM counthistory
				WHERE tagid = ? AND counttypeid = ? AND runid = ?
				AND count >= 0
			'''
			params = [tagID, countTypeID, runID]
			debugPrint("Using run-based query with RunID: %s" % runID)
		else:
			query = '''
				SELECT SUM(count) FROM counthistory
				WHERE tagid = ? AND counttypeid = ? 
				AND "TimeStamp" BETWEEN ? AND ?
				AND count >= 0
			'''
			params = [tagID, countTypeID, startTime, endTime]
			debugPrint("Using time-based query from %s to %s" % (startTime, endTime))
		
		data = system.db.runPrepQuery(query, params, db)
		
		badCount = 0
		for row in data:
			badCount = row[0] if row[0] is not None else 0

		system.tag.writeBlocking([badCountPath], [badCount])
		debugPrint("Bad count: %s" % badCount)
		return badCount
		
	except Exception as e:
		debugPrint("Error getting bad count: %s" % str(e))
		logger.error("getBadCount error: %s" % str(e))
		system.tag.writeBlocking([badCountPath], [0])
		return 0

def calcTargetCount(runTimePath, standardRatePath, targetCountPath):
	"""Calculate target count based on run time and standard rate"""
	debugPrint("Calculating target count")
	debugPrint("Paths - RunTime: %s, StandardRate: %s, Target: %s" % (runTimePath, standardRatePath, targetCountPath))
	
	try:
		runTime = system.tag.readBlocking([runTimePath])[0].value
		standardRate = system.tag.readBlocking([standardRatePath])[0].value
		
		debugPrint("Values - RunTime: %s, StandardRate: %s" % (runTime, standardRate))
		
		if runTime is None or standardRate is None or standardRate == 0:
			debugPrint("WARNING: RunTime or StandardRate is None/0, setting target count to 0")
			system.tag.writeBlocking([targetCountPath], [0])
			return 0
		
		# Target = (RunTime in seconds / 3600) * StandardRate (per hour)
		targetCount = (runTime / 3600.0) * standardRate
		
		system.tag.writeBlocking([targetCountPath], [targetCount])
		debugPrint("Target Count calculated: %s" % targetCount)
		return targetCount
		
	except Exception as e:
		debugPrint("Error calculating target count: %s" % str(e))
		logger.error("calcTargetCount error: %s" % str(e))
		system.tag.writeBlocking([targetCountPath], [0])
		return 0

def resetStartTime(parentPath):
	"""Reset the line start time to current time"""
	debugPrint("Resetting start time for: %s" % parentPath)
	
	try:
		linePath = parentPath + '/Line'
		startTimePath = linePath + '/Start Time'
		
		currentTime = system.date.now().getTime()
		system.tag.writeBlocking([startTimePath], [currentTime])
		
		debugPrint("Start time reset to: %s" % currentTime)
		debugPrint("Date/Time: %s" % system.date.format(system.date.now(), "yyyy-MM-dd HH:mm:ss"))
		return currentTime
		
	except Exception as e:
		debugPrint("Error resetting start time: %s" % str(e))
		logger.error("resetStartTime error: %s" % str(e))
		return None
