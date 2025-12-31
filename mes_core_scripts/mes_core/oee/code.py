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
Optimized MES Core OEE Calculation Library
- Fixed run-based filtering
- Added proper error handling
- Added debug capability
- Maintains original function signatures
- Batched system.tag.readBlocking calls for performance
'''

import inspect 

# Global variables
db = 'mes_core'
DEBUG_MODE = False  # Set to True for debugging

def setDebugMode(enabled):
    """Enable or disable debug mode"""
    global DEBUG_MODE
    DEBUG_MODE = enabled
    if DEBUG_MODE:
        print("Debug mode enabled")

def debugPrint(message, functionName=None):
    """Print debug messages when debug mode is enabled"""
    if DEBUG_MODE:
        if functionName is None:
            functionName = inspect.stack()[1][3]
        print("[%s] %s" % (functionName, message))
    # Always log to MES Core
    mes_core.logging.log('MES Core OEE: %s' % message, 'info')

def calcQuality(totalCountPath, goodCountPath, oeeQualityPath):
    debugPrint("Starting quality calculation")
    debugPrint("Paths - Total: %s, Good: %s, OEE: %s" % (totalCountPath, goodCountPath, oeeQualityPath))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([totalCountPath, goodCountPath])
        totalCount = tagResults[0].value
        goodCount = tagResults[1].value
        
        debugPrint("Values - Total: %s, Good: %s" % (totalCount, goodCount))
        
        if totalCount is None or totalCount == 0:
            quality = 1.0
        else:
            quality = float(goodCount if goodCount is not None else 0) / float(totalCount)
        
        system.tag.writeBlocking([oeeQualityPath], [quality])
        debugPrint("Quality calculated: %s" % quality)
        return quality
        
    except Exception as e:
        debugPrint("Error in calcQuality: %s" % str(e))
        system.tag.writeBlocking([oeeQualityPath], [1.0])
        return 1.0

def calcAvailability(runTimePath, totalTimePath, oeeAvailabilityPath):
    debugPrint("Starting availability calculation")
    debugPrint("Paths - Runtime: %s, Total: %s, OEE: %s" % (runTimePath, totalTimePath, oeeAvailabilityPath))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([runTimePath, totalTimePath])
        runTime = tagResults[0].value
        totalTime = tagResults[1].value
        
        debugPrint("Values - Runtime: %s, Total: %s" % (runTime, totalTime))
        
        if totalTime is None or totalTime == 0:
            availability = 1.0
        else:
            availability = float(runTime if runTime is not None else 0) / float(totalTime)
        
        system.tag.writeBlocking([oeeAvailabilityPath], [availability])
        debugPrint("Availability calculated: %s" % availability)
        return availability
        
    except Exception as e:
        debugPrint("Error in calcAvailability: %s" % str(e))
        system.tag.writeBlocking([oeeAvailabilityPath], [1.0])
        return 1.0

def calcPerformance(totalCountPath, targetCountPath, oeePerformancePath):
    debugPrint("Starting performance calculation")
    debugPrint("Paths - Total: %s, Target: %s, OEE: %s" % (totalCountPath, targetCountPath, oeePerformancePath))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([totalCountPath, targetCountPath])
        totalCount = tagResults[0].value
        targetCount = tagResults[1].value
        
        debugPrint("Values - Total: %s, Target: %s" % (totalCount, targetCount))
        
        if targetCount is None or targetCount == 0:
            performance = 1.0
        else:
            performance = float(totalCount if totalCount is not None else 0) / float(targetCount)
        
        system.tag.writeBlocking([oeePerformancePath], [performance])
        debugPrint("Performance calculated: %s" % performance)
        return performance
        
    except Exception as e:
        debugPrint("Error in calcPerformance: %s" % str(e))
        system.tag.writeBlocking([oeePerformancePath], [1.0])
        return 1.0

def getTagIDs(db, lineID):
    debugPrint("Getting tag IDs for line: %s" % lineID)
    
    try:
        listOfTags = []
        id = system.tag.readBlocking([lineID])[0].value
        
        query = 'SELECT id FROM counttag WHERE parentid = ?'
        data = system.db.runPrepQuery(query, [id], db)
        
        for row in data:
            tagID = row[0]
            listOfTags.append(tagID)
        
        debugPrint("Found tag IDs: %s" % str(listOfTags))
        return listOfTags
        
    except Exception as e:
        debugPrint("Error getting tag IDs: %s" % str(e))
        return []

def getGoodCount(goodCountPath, startTimePath, endTimePath, tagID, countTypeID, runID=None, db=db):
    debugPrint("Getting good count - Tag: %s, Type: %s, Run: %s" % (tagID, countTypeID, runID))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([startTimePath, endTimePath])
        startTime = tagResults[0].value
        endTime = tagResults[1].value
        
        # Choose query based on whether we have a runID
        if runID is not None:
            query = '''
                SELECT SUM(count) FROM counthistory
                WHERE tagid = ? AND counttypeid = ? AND runid = ?
            '''
            data = system.db.runPrepQuery(query, [tagID, countTypeID, runID], db)
            debugPrint("Using run-based query with RunID: %s" % runID)
        else:
            query = '''
                SELECT SUM(count) FROM counthistory
                WHERE tagid = ? AND counttypeid = ? 
                AND "TimeStamp" BETWEEN ? AND ?
            '''
            data = system.db.runPrepQuery(query, [tagID, countTypeID, startTime, endTime], db)
            debugPrint("Using time-based query from %s to %s" % (startTime, endTime))
        
        goodCount = 0
        for row in data:
            goodCount = row[0] if row[0] is not None else 0
            
        system.tag.writeBlocking([goodCountPath], [goodCount])
        debugPrint("Good count: %s" % goodCount)
        return goodCount
        
    except Exception as e:
        debugPrint("Error getting good count: %s" % str(e))
        system.tag.writeBlocking([goodCountPath], [0])
        return 0

def getBadCount(badCountPath, startTimePath, endTimePath, tagID, countTypeID, runID=None, db=db):
    debugPrint("Getting bad count - Tag: %s, Type: %s, Run: %s" % (tagID, countTypeID, runID))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([startTimePath, endTimePath])
        startTime = tagResults[0].value
        endTime = tagResults[1].value
        
        # Choose query based on whether we have a runID
        if runID is not None:
            query = '''
                SELECT SUM(count) FROM counthistory
                WHERE tagid = ? AND counttypeid = ? AND runid = ?
            '''
            data = system.db.runPrepQuery(query, [tagID, countTypeID, runID], db)
            debugPrint("Using run-based query with RunID: %s" % runID)
        else:
            query = '''
                SELECT SUM(count) FROM counthistory
                WHERE tagid = ? AND counttypeid = ? 
                AND "TimeStamp" BETWEEN ? AND ?
            '''
            data = system.db.runPrepQuery(query, [tagID, countTypeID, startTime, endTime], db)
            debugPrint("Using time-based query from %s to %s" % (startTime, endTime))
        
        badCount = 0
        for row in data:
            badCount = row[0] if row[0] is not None else 0

        system.tag.writeBlocking([badCountPath], [badCount])
        debugPrint("Bad count: %s" % badCount)
        return badCount
        
    except Exception as e:
        debugPrint("Error getting bad count: %s" % str(e))
        system.tag.writeBlocking([badCountPath], [0])
        return 0

def getTotalCount(db, lineID, totalCountPath, startTimePath, endTimePath, runID=None):
    debugPrint("Getting total count for line: %s, Run: %s" % (lineID, runID))
    
    try:
        tagIDs = getTagIDs(db, lineID)
        if not tagIDs:
            debugPrint("No tags found for line")
            system.tag.writeBlocking([totalCountPath], [0])
            return 0
        
        # Create parameter placeholders for the IN clause
        placeholders = ','.join(['?' for _ in tagIDs])
        
        # Batched tag read
        tagResults = system.tag.readBlocking([startTimePath, endTimePath])
        startTime = tagResults[0].value
        endTime = tagResults[1].value
        
        # Choose query based on whether we have a runID
        if runID is not None:
            query = '''
                SELECT SUM(count) FROM counthistory
                WHERE counttypeid != 2 AND runid = ? AND tagid IN (%s)
            ''' % placeholders
            params = [runID] + tagIDs
            debugPrint("Using run-based query with RunID: %s" % runID)
        else:
            query = '''
                SELECT SUM(count) FROM counthistory
                WHERE counttypeid != 2 AND "TimeStamp" BETWEEN ? AND ? AND tagid IN (%s)
            ''' % placeholders
            params = [startTime, endTime] + tagIDs
            debugPrint("Using time-based query from %s to %s" % (startTime, endTime))
        
        data = system.db.runPrepQuery(query, params, db)
        
        totalCount = 0
        for row in data:
            totalCount = row[0] if row[0] is not None else 0
        
        system.tag.writeBlocking([totalCountPath], [totalCount])
        debugPrint("Total count: %s" % totalCount)
        return totalCount
        
    except Exception as e:
        debugPrint("Error getting total count: %s" % str(e))
        system.tag.writeBlocking([totalCountPath], [0])
        return 0

def getUnplannedDowntimeSeconds(db, startTimePath, unplannedDowntimePath, lineID, runID=None):
    debugPrint("Getting unplanned downtime for line: %s, Run: %s" % (lineID, runID))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([startTimePath, lineID])
        startTime = tagResults[0].value
        id = tagResults[1].value
        
        # Choose query based on whether we have a runID
        if runID is not None:
            query = '''
                SELECT SUM(EXTRACT(EPOCH FROM (
                    COALESCE(s.enddatetime, NOW()) - s.startdatetime
                ))) as TotalSeconds
                FROM statehistory s
                LEFT JOIN statereason st ON s.statereasonid = st.id
                WHERE st.recorddowntime = TRUE 
                AND s.lineid = ? 
                AND s.runid = ?
            '''
            data = system.db.runPrepQuery(query, [id, runID], db)
            debugPrint("Using run-based downtime query with RunID: %s" % runID)
        else:
            # COALESCE handles ongoing events where enddatetime IS NULL
            query = '''
                SELECT SUM(EXTRACT(EPOCH FROM (
                    COALESCE(s.enddatetime, CURRENT_TIMESTAMP) - s.startdatetime
                ))) as TotalSeconds
                FROM statehistory s
                LEFT JOIN statereason st ON s.statereasonid = st.id
                WHERE st.recorddowntime = TRUE
                AND s.lineid = ?
                AND s.startdatetime > ?
            '''
            data = system.db.runPrepQuery(query, [id, startTime], db)
            debugPrint("Using time-based downtime query from: %s" % startTime)
        
        unplannedDowntime = 0
        for row in data:
            unplannedDowntime = row[0] if row[0] is not None else 0
        
        system.tag.writeBlocking([unplannedDowntimePath], [unplannedDowntime])
        debugPrint("Unplanned downtime: %s seconds" % unplannedDowntime)
        return unplannedDowntime
        
    except Exception as e:
        debugPrint("Error getting unplanned downtime: %s" % str(e))
        system.tag.writeBlocking([unplannedDowntimePath], [0])
        return 0

def getPlannedDowntimeSeconds(db, startTimePath, plannedDowntimePath, lineID, runID=None):
    debugPrint("Getting planned downtime for line: %s, Run: %s" % (lineID, runID))
    
    try:
        # Batched tag read
        tagResults = system.tag.readBlocking([startTimePath, lineID])
        startTime = tagResults[0].value
        id = tagResults[1].value
        
        # Choose query based on whether we have a runID
        if runID is not None:
            query = '''
                SELECT SUM(EXTRACT(EPOCH FROM (
                    COALESCE(s.enddatetime, NOW()) - s.startdatetime
                ))) as TotalSeconds
                FROM statehistory s
                LEFT JOIN statereason st ON s.statereasonid = st.id
                WHERE st.planneddowntime = TRUE 
                AND s.lineid = ? 
                AND s.runid = ?
            '''
            data = system.db.runPrepQuery(query, [id, runID], db)
            debugPrint("Using run-based planned downtime query with RunID: %s" % runID)
        else:
            # COALESCE handles ongoing events where enddatetime IS NULL
            query = '''
                SELECT SUM(EXTRACT(EPOCH FROM (
                    COALESCE(s.enddatetime, CURRENT_TIMESTAMP) - s.startdatetime
                ))) as TotalSeconds
                FROM statehistory s
                LEFT JOIN statereason st ON s.statereasonid = st.id
                WHERE st.planneddowntime = TRUE
                AND s.lineid = ?
                AND s.startdatetime > ?
            '''
            data = system.db.runPrepQuery(query, [id, startTime], db)
            debugPrint("Using time-based planned downtime query from: %s" % startTime)
        
        plannedDowntime = 0
        for row in data:
            plannedDowntime = row[0] if row[0] is not None else 0
            
        system.tag.writeBlocking([plannedDowntimePath], [plannedDowntime])
        debugPrint("Planned downtime: %s seconds" % plannedDowntime)
        return plannedDowntime
        
    except Exception as e:
        debugPrint("Error getting planned downtime: %s" % str(e))
        system.tag.writeBlocking([plannedDowntimePath], [0])
        return 0

def getCurrentRunID(lineID, db=db):
    """Get the current active run ID for a line"""
    try:
        query = '''
            SELECT r.id 
            FROM run r
            INNER JOIN schedule s ON r.scheduleid = s.id
            WHERE s.lineid = ? 
            AND (r.closed IS NULL OR r.closed = FALSE)
            AND r.runstartdatetime IS NOT NULL
            AND (r.runstopdatetime IS NULL)
            ORDER BY r.runstartdatetime DESC
            LIMIT 1
        '''
        
        data = system.db.runPrepQuery(query, [lineID], db)
        
        if len(data) > 0:
            runID = data[0][0]
            debugPrint("Found active run ID %s for line %s" % (runID, lineID))
            return runID
        else:
            debugPrint("No active run found for line %s" % lineID)
            return None
            
    except Exception as e:
        debugPrint("Error getting current run ID for line %s: %s" % (lineID, str(e)))
        return None

def getOee(parentPath, runID=None):
    """
    Main OEE calculation function - now supports run-based filtering
    
    Args:
        parentPath: Base tag path for the line (e.g., '[PLC]Line1')
        runID: Optional run ID to filter calculations by specific run
    """
    debugPrint("Starting OEE calculation for: %s" % parentPath)
    debugPrint("Run ID parameter: %s" % runID)
    
    try:
        # Define all tag paths
        lineID = parentPath + '/OEE/ID'
        unplannedDowntimePath = parentPath + '/OEE/Unplanned Downtime'
        totalTimePath = parentPath + '/OEE/Total Time'
        totalCountPath = parentPath + '/OEE/Total Count'
        targetCountPath = parentPath + '/OEE/Target Count'
        startTimePath = parentPath + '/OEE/Start Time'
        runTimePath = parentPath + '/OEE/Run Time'
        plannedDowntimePath = parentPath + '/OEE/Planned Downtime'
        oeeQualityPath = parentPath + '/OEE/OEE Quality'
        oeePerformancePath = parentPath + '/OEE/OEE Performance'
        oeeAvailabilityPath = parentPath + '/OEE/OEE Availability'
        goodCountPath = parentPath + '/OEE/Good Count'
        currentTimePath = parentPath + '/OEE/Current Time'
        badCountPath = parentPath + '/OEE/Bad Count'
        runIDPath = parentPath + '/OEE/RunID'
        goodCountIDPath = parentPath + '/Dispatch/OEE Outfeed/TagID'
        badCountIDPath = parentPath + '/Dispatch/OEE Waste/TagID'
        endTimePath = currentTimePath
        
        # Batched tag read for initial values
        tagResults = system.tag.readBlocking([goodCountIDPath, badCountIDPath, lineID])
        goodCountID = tagResults[0].value
        badCountID = tagResults[1].value
        lineIDValue = tagResults[2].value
        
        # If no runID provided, try to get current active run
        currentRunID = runID
        if currentRunID is None:
            currentRunID = getCurrentRunID(lineIDValue, db)
            debugPrint("Auto-detected current run ID: %s" % currentRunID)
        
        # Write the run ID to the tag if we have one
        if currentRunID is not None:
            system.tag.writeBlocking([runIDPath], [currentRunID])
        
        # Call all functions with runID parameter
        getUnplannedDowntimeSeconds(db, startTimePath, unplannedDowntimePath, lineID, currentRunID)
        getPlannedDowntimeSeconds(db, startTimePath, plannedDowntimePath, lineID, currentRunID)
        getGoodCount(goodCountPath, startTimePath, endTimePath, goodCountID, 3, currentRunID, db)
        getBadCount(badCountPath, startTimePath, endTimePath, badCountID, 4, currentRunID, db)
        getTotalCount(db, lineID, totalCountPath, startTimePath, endTimePath, currentRunID)
        calcQuality(totalCountPath, goodCountPath, oeeQualityPath)
        calcAvailability(runTimePath, totalTimePath, oeeAvailabilityPath)
        calcPerformance(totalCountPath, targetCountPath, oeePerformancePath)
        
        debugPrint("Completed OEE calculation for: %s" % parentPath)
        
    except Exception as e:
        debugPrint("Error in getOee: %s" % str(e))
        raise

# Legacy function for backward compatibility
def getRunOee(parentPath, runID):
    """Calculate OEE for a specific run"""
    return getOee(parentPath, runID)

debugPrint("Optimized MES Core OEE Library loaded successfully")
