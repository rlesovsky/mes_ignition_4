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
MES Core State History - PostgreSQL Version

This function takes two arguments from the tag event -- the reasonCode and the lineID.
When called from the tag event, this function will fill in the end time of the previous 
state history entry and create a new entry for the current state.

MySQL to PostgreSQL conversions:
- Column names: Mixed case -> lowercase
- runSFPrepUpdate -> runPrepUpdate (SF version deprecated)
- datetime strings -> pass timestamp directly
- Added RunID support
- Added proper error handling
'''

from mes_core import config

db = config.DB
logger = system.util.getLogger("MES_StateHistory")


def storeStateHistory(reasonCode, lineID, runID=None, debug=False):
	"""
	Store state history entry and close previous entry.
	
	Args:
		reasonCode: The state reason code from the PLC/tag
		lineID: The line ID (database ID, not tag path)
		runID: Optional run ID to associate with this state entry
		debug: Enable debug logging
	
	Returns:
		1 on success, 0 on failure
	"""
	try:
		timestamp = system.date.now()
		
		if debug:
			logger.info("storeStateHistory called - reasonCode: %s, lineID: %s, runID: %s" % (reasonCode, lineID, runID))
		
		# PostgreSQL: lowercase column names
		query = '''
			SELECT id, reasonname 
			FROM statereason 
			WHERE reasoncode = ? AND parentid = ?
		'''
		
		data = system.db.runPrepQuery(query, [reasonCode, lineID], db)
		
		if len(data) == 0:
			logger.warn("No state reason found for reasonCode: %s, lineID: %s" % (reasonCode, lineID))
			return 0
		
		reasonID = data[0][0]
		reasonName = data[0][1]
		
		if debug:
			logger.info("Found reasonID: %s, reasonName: %s" % (reasonID, reasonName))
		
		# Close previous state entry (set end time where end time is NULL)
		# PostgreSQL: lowercase columns, pass timestamp directly
		endQuery = '''
			UPDATE statehistory 
			SET enddatetime = ? 
			WHERE lineid = ? AND enddatetime IS NULL
		'''
		
		system.db.runPrepUpdate(endQuery, [timestamp, lineID], db)
		
		if debug:
			logger.info("Closed previous state entry")
		
		# Insert new state entry
		# PostgreSQL: lowercase columns
		if runID is not None:
			insertQuery = '''
				INSERT INTO statehistory (statereasonid, reasonname, lineid, reasoncode, startdatetime, runid)
				VALUES (?, ?, ?, ?, ?, ?)
			'''
			system.db.runPrepUpdate(insertQuery, [reasonID, reasonName, lineID, reasonCode, timestamp, runID], db)
		else:
			insertQuery = '''
				INSERT INTO statehistory (statereasonid, reasonname, lineid, reasoncode, startdatetime)
				VALUES (?, ?, ?, ?, ?)
			'''
			system.db.runPrepUpdate(insertQuery, [reasonID, reasonName, lineID, reasonCode, timestamp], db)
		
		if debug:
			logger.info("Inserted new state entry for reasonCode: %s" % reasonCode)
		
		return 1
		
	except Exception as e:
		logger.error("storeStateHistory error: %s" % str(e))
		import traceback
		logger.error("Traceback: %s" % traceback.format_exc())
		return 0


def storeStateHistoryWithPath(reasonCode, lineIDPath, runIDPath=None, debug=False):
	"""
	Store state history entry - reads lineID and runID from tag paths.
	
	Args:
		reasonCode: The state reason code from the PLC/tag
		lineIDPath: Tag path to the Line ID tag
		runIDPath: Optional tag path to the Run ID tag
		debug: Enable debug logging
	
	Returns:
		1 on success, 0 on failure
	"""
	try:
		# Read lineID from tag
		lineIDResult = system.tag.readBlocking([lineIDPath])[0]
		if not lineIDResult.quality.isGood():
			logger.error("Bad quality reading lineID from: %s" % lineIDPath)
			return 0
		
		lineID = lineIDResult.value
		
		# Read runID if path provided
		runID = None
		if runIDPath:
			runIDResult = system.tag.readBlocking([runIDPath])[0]
			if runIDResult.quality.isGood() and runIDResult.value is not None and runIDResult.value > 0:
				runID = runIDResult.value
		
		return storeStateHistory(reasonCode, lineID, runID, debug)
		
	except Exception as e:
		logger.error("storeStateHistoryWithPath error: %s" % str(e))
		return 0


def closeOpenStateEntries(lineID, debug=False):
	"""
	Close any open state entries for a line (useful when stopping a run).
	
	Args:
		lineID: The line ID
		debug: Enable debug logging
	
	Returns:
		Number of entries closed
	"""
	try:
		timestamp = system.date.now()
		
		query = '''
			UPDATE statehistory 
			SET enddatetime = ? 
			WHERE lineid = ? AND enddatetime IS NULL
		'''
		
		rowsAffected = system.db.runPrepUpdate(query, [timestamp, lineID], db)
		
		if debug:
			logger.info("Closed %s open state entries for lineID: %s" % (rowsAffected, lineID))
		
		return rowsAffected
		
	except Exception as e:
		logger.error("closeOpenStateEntries error: %s" % str(e))
		return 0