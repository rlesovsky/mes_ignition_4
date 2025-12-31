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
Script: mes_filter.py
Purpose: Queries and filters MES objects (Enterprise, Site, Area, Line, Cell) from the database for Ignition MES systems.
Context: Retrieves hierarchical object data (ID, Name, EquipmentPath) for production tracking.
Dependencies: Requires 'mes_core' database with matching schema.
'''

import re
import system

class MESFilterResults:
    # Purpose: Converts database query results into a list of dynamic objects with getter methods and dictionary-like access.
    # Parameters:
    #   - queryResults: Ignition dataset from system.db.runPrepQuery.
    def __init__(self, queryResults):
        # Extract column names as headers
        self._headers = [str(c) for c in queryResults.getUnderlyingDataset().getColumnNames()]
        
        class ResultEntry:
            # Purpose: Represents a single row with dynamic getters and dictionary access.
            __slots__ = self._headers  # Optimize memory usage
            
            def __init__(self, *args):
                self._values = args
                # Map headers to values for dictionary access
                self.__dict__.update(zip(self.__slots__, args))
                # Create getter methods (e.g., getId, getName)
                for name in self.__slots__:
                    setattr(self, 'get' + name.capitalize(), lambda: self.__dict__.get(name))
            
            def __iter__(self):
                return iter(self._values)
            
            def __repr__(self):
                return str(dict(zip(self.__slots__, self._values)))
            
            def __getitem__(self, key):
                # Support index or column name access
                try:
                    return self._values[key]
                except (TypeError, IndexError):
                    return self.__dict__.get(key)
        
        # Convert dataset to list of ResultEntry objects (faster with list comprehension)
        self.results = [ResultEntry(*row) for row in queryResults]
    
    def __iter__(self):
        return iter(self.results)

class MESFilter:
    # Purpose: Defines a filter for querying MES objects by type and enable state.
    mesObjectTypes = ['Enterprise', 'Site', 'Area', 'Line', 'Cell']
    
    def __init__(self):
        self.enabled = True
        self.mesObjectType = None
    
    def setMESObjectTypeName(self, mesObjectType):
        # Purpose: Sets the MES object type for filtering.
        # Parameters:
        #   - mesObjectType: String, one of mesObjectTypes.
        mesObjectType = mesObjectType.capitalize()
        if mesObjectType not in self.mesObjectTypes:
            raise ValueError('Object type not in model schema: %s' % mesObjectType)
        self.mesObjectType = mesObjectType
    
    def setEnableStateName(self, state):
        # Purpose: Sets the enable state for filtering.
        # Parameters:
        #   - state: Bool or String ('ENABLED', 'DISABLED').
        if isinstance(state, bool):
            self.enabled = state
        elif state.upper() in ('ENABLED', 'DISABLED'):
            self.enabled = state.upper() == 'ENABLED'
        else:
            raise ValueError('Invalid state: %s' % state)

def createFilter():
    # Purpose: Creates a new MESFilter instance.
    # Returns: MESFilter object.
    return MESFilter()

# SQL queries for loading MES objects (kept inline as Named Queries not used)
loadMESObjectsQueries = {
    'Enterprise': '''
        SELECT e.id AS ID, e.name AS Name, CONCAT_WS('/', e.name) AS EquipmentPath
        FROM enterprise AS e
        WHERE e.disable = FALSE
    ''',
    'Site': '''
        SELECT s.id AS ID, s.name AS Name, CONCAT_WS('/', e.name, s.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        WHERE e.disable = FALSE AND s.disable = FALSE
    ''',
    'Area': '''
        SELECT a.id AS ID, a.name AS Name, CONCAT_WS('/', e.name, s.name, a.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        INNER JOIN area AS a ON s.id = a.parentid
        WHERE e.disable = FALSE AND s.disable = FALSE AND a.disable = FALSE
    ''',
    'Line': '''
        SELECT l.id AS ID, l.name AS Name, CONCAT_WS('/', e.name, s.name, a.name, l.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        INNER JOIN area AS a ON s.id = a.parentid
        INNER JOIN line AS l ON a.id = l.parentid
        WHERE e.disable = FALSE AND s.disable = FALSE AND a.disable = FALSE AND l.disable = FALSE
    ''',
    'Cell': '''
        SELECT c.id AS ID, c.name AS Name, CONCAT_WS('/', e.name, s.name, a.name, l.name, c.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        INNER JOIN area AS a ON s.id = a.parentid
        INNER JOIN line AS l ON a.id = l.parentid
        INNER JOIN cell AS c ON l.id = c.parentid
        WHERE e.disable = FALSE AND s.disable = FALSE AND a.disable = FALSE AND l.disable = FALSE AND c.disable = FALSE
    '''
}

def loadMESObjects(mesFilter, db='mes_core', debug=False):
    # Purpose: Queries MES objects based on the filter's object type.
    # Parameters:
    #   - mesFilter: MESFilter, specifies the object type.
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: MESFilterResults object.
    logger = system.util.getLogger('MES')
    try:
        if not mesFilter.mesObjectType:
            raise ValueError('MES object type not set')
        query = loadMESObjectsQueries[mesFilter.mesObjectType]
        results = system.db.runPrepQuery(query, [], db)
        if debug:
            logger.info('Loaded %d %s objects from %s' % (len(results), mesFilter.mesObjectType, db))
            system.util.sendLogMessage('MES: Loaded %d %s objects from %s' % (len(results), mesFilter.mesObjectType, db), 'MES')
        return MESFilterResults(results)
    except Exception as e:
        logger.error('Error loading %s objects: %s' % (mesFilter.mesObjectType or 'unknown', str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error loading %s objects: %s' % (mesFilter.mesObjectType or 'unknown', str(e)), 'MES')
        raise

def loadMESObject(name, mesObjectType, db='mes_core', debug=False):
    # Purpose: Queries a specific MES object by name and type.
    # Parameters:
    #   - name: String, object name.
    #   - mesObjectType: String, object type ('Enterprise', 'Site', etc.).
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: ResultEntry object (first result).
    logger = system.util.getLogger('MES')
    try:
        if not name or not isinstance(name, str):
            raise ValueError('Invalid name: %s' % name)
        mesObjectType = mesObjectType.capitalize()
        if mesObjectType not in MESFilter.mesObjectTypes:
            raise ValueError('Invalid object type: %s' % mesObjectType)
        query = loadMESObjectsQueries[mesObjectType] + ' AND %s.name = ?' % mesObjectType.lower()
        results = system.db.runPrepQuery(query, [name], db)
        if not results:
            raise ValueError('No %s found with name %s' % (mesObjectType, name))
        if debug:
            logger.info('Loaded %s: %s from %s' % (mesObjectType, name, db))
            system.util.sendLogMessage('MES: Loaded %s: %s from %s' % (mesObjectType, name, db), 'MES')
        return MESFilterResults(results).results[0]
    except Exception as e:
        logger.error('Error loading %s: %s: %s' % (mesObjectType, name, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error loading %s: %s: %s' % (mesObjectType, name, str(e)), 'MES')
        raise

# Cache regex pattern for performance
modelPathPattern = re.compile(r'([^/\\]+)', re.I)

def getEnterpriseID(modelPath, db='mes_core', debug=False):
    # Purpose: Retrieves Enterprise ID from a model path.
    # Parameters:
    #   - modelPath: String, path (e.g., 'OF').
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: Integer, Enterprise ID.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts or modelParts[0] != 'OF':
            raise ValueError('Only Enterprise "OF" is supported: %s' % modelPath)
        results = system.db.runPrepQuery('SELECT e.id FROM enterprise AS e WHERE e.name = ?', [modelParts[0]], db)
        if not results:
            raise ValueError('Enterprise %s not found' % modelPath)
        if debug:
            logger.info('Got Enterprise ID %d for %s' % (results[0][0], modelPath))
            system.util.sendLogMessage('MES: Got Enterprise ID %d for %s' % (results[0][0], modelPath), 'MES')
        return results[0][0]
    except Exception as e:
        logger.error('Error getting Enterprise ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting Enterprise ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise

def getSiteID(modelPath, db='mes_core', debug=False):
    # Purpose: Retrieves Site ID from a model path.
    # Parameters:
    #   - modelPath: String, path (e.g., 'OF/Site1').
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: Integer, Site ID.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts:
            raise ValueError('Invalid model path: %s' % modelPath)
        if modelParts[0] != 'OF':
            modelParts = ['OF'] + modelParts
        results = system.db.runPrepQuery(
            'SELECT s.id FROM enterprise AS e INNER JOIN site AS s ON s.parentid = e.id WHERE e.name = ? AND s.name = ?',
            modelParts[:2], db)
        if not results:
            raise ValueError('Site %s not found' % modelPath)
        if debug:
            logger.info('Got Site ID %d for %s' % (results[0][0], modelPath))
            system.util.sendLogMessage('MES: Got Site ID %d for %s' % (results[0][0], modelPath), 'MES')
        return results[0][0]
    except Exception as e:
        logger.error('Error getting Site ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting Site ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise

def getAreaID(modelPath, db='mes_core', debug=False):
    # Purpose: Retrieves Area ID from a model path.
    # Parameters:
    #   - modelPath: String, path (e.g., 'OF/Site1/Area1').
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: Integer, Area ID.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts:
            raise ValueError('Invalid model path: %s' % modelPath)
        if modelParts[0] != 'OF':
            modelParts = ['OF'] + modelParts
        results = system.db.runPrepQuery(
            'SELECT a.id FROM enterprise AS e INNER JOIN site AS s ON s.parentid = e.id INNER JOIN area AS a ON a.parentid = s.id WHERE e.name = ? AND s.name = ? AND a.name = ?',
            modelParts[:3], db)
        if not results:
            raise ValueError('Area %s not found' % modelPath)
        if debug:
            logger.info('Got Area ID %d for %s' % (results[0][0], modelPath))
            system.util.sendLogMessage('MES: Got Area ID %d for %s' % (results[0][0], modelPath), 'MES')
        return results[0][0]
    except Exception as e:
        logger.error('Error getting Area ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting Area ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise

def getLineID(modelPath, db='mes_core', debug=False):
    # Purpose: Retrieves Line ID from a model path.
    # Parameters:
    #   - modelPath: String, path (e.g., 'OF/Site1/Area1/Line1').
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: Integer, Line ID.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts:
            raise ValueError('Invalid model path: %s' % modelPath)
        if modelParts[0] != 'OF':
            modelParts = ['OF'] + modelParts
        results = system.db.runPrepQuery(
            'SELECT l.id FROM enterprise AS e INNER JOIN site AS s ON s.parentid = e.id INNER JOIN area AS a ON a.parentid = s.id INNER JOIN line AS l ON l.parentid = a.id WHERE e.name = ? AND s.name = ? AND a.name = ? AND l.name = ?',
            modelParts[:4], db)
        if not results:
            raise ValueError('Line %s not found' % modelPath)
        if debug:
            logger.info('Got Line ID %d for %s' % (results[0][0], modelPath))
            system.util.sendLogMessage('MES: Got Line ID %d for %s' % (results[0][0], modelPath), 'MES')
        return results[0][0]
    except Exception as e:
        logger.error('Error getting Line ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting Line ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise

def getCellID(modelPath, db='mes_core', debug=False):
    # Purpose: Retrieves Cell ID from a model path.
    # Parameters:
    #   - modelPath: String, path (e.g., 'OF/Site1/Area1/Line1/Cell1').
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: Integer, Cell ID.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts:
            raise ValueError('Invalid model path: %s' % modelPath)
        if modelParts[0] != 'OF':
            modelParts = ['OF'] + modelParts
        results = system.db.runPrepQuery(
            'SELECT c.id FROM enterprise AS e INNER JOIN site AS s ON s.parentid = e.id INNER JOIN area AS a ON a.parentid = s.id INNER JOIN line AS l ON l.parentid = a.id INNER JOIN cell AS c ON c.parentid = l.id WHERE e.name = ? AND s.name = ? AND a.name = ? AND l.name = ? AND c.name = ?',
            modelParts[:5], db)
        if not results:
            raise ValueError('Cell %s not found' % modelPath)
        if debug:
            logger.info('Got Cell ID %d for %s' % (results[0][0], modelPath))
            system.util.sendLogMessage('MES: Got Cell ID %d for %s' % (results[0][0], modelPath), 'MES')
        return results[0][0]
    except Exception as e:
        logger.error('Error getting Cell ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting Cell ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise

def getID(modelPath, db='mes_core', debug=False):
    # Purpose: Retrieves the ID of an MES object based on model path length.
    # Parameters:
    #   - modelPath: String, path (e.g., 'OF/Site1/Area1').
    #   - db: String, database connection name (default: 'mes_core').
    #   - debug: Bool, enables logging and console output (default: False).
    # Returns: Integer, object ID.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts:
            raise ValueError('Invalid model path: %s' % modelPath)
        modelLookup = {
            1: getEnterpriseID,
            2: getSiteID,
            3: getAreaID,
            4: getLineID,
            5: getCellID
        }
        if len(modelParts) not in modelLookup:
            raise ValueError('Model path with %d parts not supported' % len(modelParts))
        result = modelLookup[len(modelParts)](modelPath, db, debug)
        if debug:
            logger.info('Got ID %d for path %s' % (result, modelPath))
            system.util.sendLogMessage('MES: Got ID %d for path %s' % (result, modelPath), 'MES')
        return result
    except Exception as e:
        logger.error('Error getting ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise