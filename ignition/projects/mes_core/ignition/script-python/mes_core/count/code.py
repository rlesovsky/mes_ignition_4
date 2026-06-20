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
Script: store_count_history.py
Purpose: Logs count delta from Ignition tag events to counthistory table.
Context: Used in tag change events for MES production tracking.
Parameters:
   - currentCount: Float/Int, current tag count.
   - lastCount: Float/Int, previous tag count.
   - tagID: Int, counttag ID.
   - countTypeID: Int, count type ID.
   - runID: Int, current run ID (optional, but recommended).
   - debug: Bool, enables logging and console output (default: False).
 
Returns:
   - currentCount if inserted, None otherwise.
   
'''

from mes_core import config


def storeCountHistory(currentCount, lastCount, tagID, countTypeID, runID=None, debug=False):
	logger = system.util.getLogger("MES_CountHistory")

	db = config.DB
	
	try:
		# Validate inputs
		if currentCount is None or lastCount is None:
			if debug:
				logger.debug("Skipping - currentCount or lastCount is None")
			return None
		
		countDelta = currentCount - lastCount
		
		if abs(countDelta) >= 1:
			# Scope-independent prepped insert: this runs in gateway scope (tag-change
			# event), where runNamedQuery's first positional must be a project name and
			# there is no datasource arg. A prepped update keeps the `db` connection and
			# avoids the project dependency entirely.
			system.db.runPrepUpdate(
				'INSERT INTO counthistory (tagid, counttypeid, count, runid, "TimeStamp") '
				'VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)',
				[tagID, countTypeID, int(countDelta), runID], db)

			if debug:
				logger.info("Inserted delta %s for tagID=%s, runID=%s" % (countDelta, tagID, runID))
			
			return currentCount
			
		elif debug:
			logger.debug("Delta %s too small for tagID=%s" % (countDelta, tagID))
		
		return None
		
	except Exception as e:
		logger.error("Error for tagID=%s: %s" % (tagID, str(e)))
		if debug:
			import traceback
			logger.error("Traceback: %s" % traceback.format_exc())
		return None


