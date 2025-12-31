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

''''
Script: store_count_history.py
Purpose: Logs count delta from Ignition tag events to counthistory table.
Context: Used in tag change events for MES production tracking.
Parameters:
   - currentCount: Float/Int, current tag count.
   - lastCount: Float/Int, previous tag count.
   - tagID: Int, counttag ID.
   - countTypeID: Int, count type ID.
   - db: String, database connection name (e.g., 'mes_core').
   - debug: Bool, enables logging and console output (default: False).
 Returns:
   - currentCount if inserted, None otherwise.
   '''

def storeCountHistory(currentCount, lastCount, tagID, countTypeID, debug=False):
    import system
    logger = system.util.getLogger("MES_CountHistory")
    
    db = "mes_core"
    
    try:
        countDelta = currentCount - lastCount
        if abs(countDelta) >= 1:
            system.db.runNamedQuery("InsertCountHistory", {'tagID': tagID, 'countTypeID': countTypeID, 'count': countDelta}, db)
            if debug:
                logger.info("Inserted delta %s for tagID=%s" % (countDelta, tagID))
                system.util.sendLogMessage("MES: Delta %s for tagID=%s" % (countDelta, tagID), "MES_CountHistory")
            return currentCount
        elif debug:
            logger.debug("Delta %s too small for tagID=%s" % (countDelta, tagID))
            system.util.sendLogMessage("MES: Delta %s too small for tagID=%s" % (countDelta, tagID), "MES_CountHistory")
        return None
        
    except Exception as e:
        logger.error("Error for tagID=%s: %s" % (tagID, str(e)))
        if debug:
            system.util.sendLogMessage("MES: Error for tagID=%s: %s" % (tagID, str(e)), "MES_CountHistory")
        return None

# Example usage:
# currentCount = value.getValue()
# lastCount = system.tag.readBlocking(["[default]Line1/LastCount"])[0].value
# result = storeCountHistory(currentCount, lastCount, 1, 2, "mes_core", debug=False)
# if result is not None:
#     system.tag.writeBlocking(["[default]Line1/LastCount"], [result])