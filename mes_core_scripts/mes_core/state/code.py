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
REFACTORED: PostgreSQL compatibility
This function takes two arguments from the tag event -- the reasonCode and the lineID.  When called from the tag event,
this function will fill in the end time of the previous state history entry and create a new entry for the current state.

'''

def storeStateHistory(reasonCode,lineID):
	import system
	from datetime import datetime
	
	db = 'mes_core'
	stamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
	data = system.db.runPrepQuery('SELECT id,reasonname FROM statereason WHERE reasoncode = ? AND parentid = ?',[reasonCode,lineID],db)
	
	for row in data:
		reasonID = row[0]
		reasonName = row[1]
	
	endQuery = 'UPDATE statehistory SET enddatetime = ? WHERE lineid = ? AND enddatetime IS NULL'
	query = 'INSERT INTO statehistory(statereasonid,reasonname,lineid,reasoncode,startdatetime) VALUES(?,?,?,?,?)'
	system.db.runSFPrepUpdate(endQuery,[stamp,lineID],[db])
	system.db.runSFPrepUpdate(query,[reasonID,reasonName,lineID,reasonCode,stamp],[db])