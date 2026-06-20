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
Script: mes_filter.py
Purpose: Queries and filters MES objects (Enterprise, Site, Area, Line, Cell) from the database for Ignition MES systems.
Context: Retrieves hierarchical object data (ID, Name, EquipmentPath) for production tracking.
Dependencies: Requires 'mes_core' database with matching schema.
'''

import re
import system

from mes_core import config

class _ResultEntry(object):
    # Purpose: Represents a single row with dynamic getters and dictionary access.
    # Public interface (relied on by callers): iterate -> values, entry.getId()/getName()/
    # getEquipmentpath(), entry['ID'] (by name), entry[0] (by index).
    def __init__(self, headers, values):
        self._headers = headers
        self._values  = list(values)
        self._byName  = dict(zip(headers, self._values))
        # Default-arg capture fixes late binding (every getter would otherwise return the last column).
        for name in headers:
            setattr(self, 'get' + name.capitalize(), (lambda v=self._byName[name]: v))

    def __iter__(self):
        return iter(self._values)

    def __getitem__(self, key):
        # Support index (int) or column-name access.
        return self._values[key] if isinstance(key, int) else self._byName.get(key)

    def __repr__(self):
        return str(self._byName)

class MESFilterResults(object):
    # Purpose: Converts database query results into a list of accessor objects with getter
    # methods and dictionary-like access.
    # Parameters:
    #   - queryResults: Ignition dataset from system.db.runPrepQuery.
    def __init__(self, queryResults):
        # Extract column names as headers
        headers = [str(c) for c in queryResults.getUnderlyingDataset().getColumnNames()]
        self.results = [_ResultEntry(headers, [row[i] for i in range(len(headers))])
                        for row in queryResults]

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
        WHERE e.disable = false
    ''',
    'Site': '''
        SELECT s.id AS ID, s.name AS Name, CONCAT_WS('/', e.name, s.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        WHERE e.disable = false AND s.disable = false
    ''',
    'Area': '''
        SELECT a.id AS ID, a.name AS Name, CONCAT_WS('/', e.name, s.name, a.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        INNER JOIN area AS a ON s.id = a.parentid
        WHERE e.disable = false AND s.disable = false AND a.disable = false
    ''',
    'Line': '''
        SELECT l.id AS ID, l.name AS Name, CONCAT_WS('/', e.name, s.name, a.name, l.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        INNER JOIN area AS a ON s.id = a.parentid
        INNER JOIN line AS l ON a.id = l.parentid
        WHERE e.disable = false AND s.disable = false AND a.disable = false AND l.disable = false
    ''',
    'Cell': '''
        SELECT c.id AS ID, c.name AS Name, CONCAT_WS('/', e.name, s.name, a.name, l.name, c.name) AS EquipmentPath
        FROM enterprise AS e
        INNER JOIN site AS s ON e.id = s.parentid
        INNER JOIN area AS a ON s.id = a.parentid
        INNER JOIN line AS l ON a.id = l.parentid
        INNER JOIN cell AS c ON l.id = c.parentid
        WHERE e.disable = false AND s.disable = false AND a.disable = false AND l.disable = false AND c.disable = false
    '''
}

# Table alias used inside each query above (the tables are aliased, so a single-object
# filter must qualify the name column by alias, not by the table name).
_ALIAS = {'Enterprise': 'e', 'Site': 's', 'Area': 'a', 'Line': 'l', 'Cell': 'c'}

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
        query = loadMESObjectsQueries[mesObjectType] + ' AND %s.name = ?' % _ALIAS[mesObjectType]
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

# Hierarchy levels in order, with the SQL table + alias used to resolve each.
_LEVELS = ['Enterprise', 'Site', 'Area', 'Line', 'Cell']
_TABLES = ['enterprise', 'site', 'area', 'line', 'cell']
_ALIASES = ['e', 's', 'a', 'l', 'c']

def _resolveID(depth, modelPath, db, debug):
    # Purpose: Shared ID resolver for Enterprise..Cell (depth 1..5).
    # Builds the JOIN chain down to the requested level and matches each name
    # segment. Enterprise (depth 1) enforces the 'OF'-only rule and is never
    # auto-prepended; deeper levels prepend the 'OF' root when the caller omits
    # it. Verbatim consolidation of the five former get*ID functions, so the
    # generated SQL and the raised ValueErrors are unchanged.
    level = _LEVELS[depth - 1]
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if depth == 1:
            # Enterprise: only 'OF' is supported and it is never auto-prepended.
            if not modelParts or modelParts[0] != config.ENTERPRISE_ROOT:
                raise ValueError('Only Enterprise "%s" is supported: %s' % (config.ENTERPRISE_ROOT, modelPath))
        else:
            if not modelParts:
                raise ValueError('Invalid model path: %s' % modelPath)
            if modelParts[0] != config.ENTERPRISE_ROOT:
                modelParts = [config.ENTERPRISE_ROOT] + modelParts

        aliases = _ALIASES[:depth]
        joins = ''
        for ix in range(1, depth):
            joins += ' INNER JOIN %s AS %s ON %s.parentid = %s.id' % (
                _TABLES[ix], aliases[ix], aliases[ix], aliases[ix - 1])
        where = ' AND '.join('%s.name = ?' % a for a in aliases)
        query = 'SELECT %s.id FROM %s AS %s%s WHERE %s' % (
            aliases[depth - 1], _TABLES[0], aliases[0], joins, where)

        results = system.db.runPrepQuery(query, modelParts[:depth], db)
        if not results:
            raise ValueError('%s %s not found' % (level, modelPath))
        if debug:
            logger.info('Got %s ID %d for %s' % (level, results[0][0], modelPath))
            system.util.sendLogMessage('MES: Got %s ID %d for %s' % (level, results[0][0], modelPath), 'MES')
        return results[0][0]
    except Exception as e:
        logger.error('Error getting %s ID for %s: %s' % (level, modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting %s ID for %s: %s' % (level, modelPath, str(e)), 'MES')
        raise

def getEnterpriseID(modelPath, db=config.DB, debug=False):
    # Retrieves Enterprise ID from a model path. Only Enterprise 'OF' is supported.
    return _resolveID(1, modelPath, db, debug)

def getSiteID(modelPath, db=config.DB, debug=False):
    # Retrieves Site ID from a model path (e.g., 'OF/Site1').
    return _resolveID(2, modelPath, db, debug)

def getAreaID(modelPath, db=config.DB, debug=False):
    # Retrieves Area ID from a model path (e.g., 'OF/Site1/Area1').
    return _resolveID(3, modelPath, db, debug)

def getLineID(modelPath, db=config.DB, debug=False):
    # Retrieves Line ID from a model path (e.g., 'OF/Site1/Area1/Line1').
    return _resolveID(4, modelPath, db, debug)

def getCellID(modelPath, db=config.DB, debug=False):
    # Retrieves Cell ID from a model path (e.g., 'OF/Site1/Area1/Line1/Cell1').
    return _resolveID(5, modelPath, db, debug)

def getID(modelPath, db=config.DB, debug=False):
    # Purpose: Retrieves the ID of an MES object based on model path depth.
    logger = system.util.getLogger('MES')
    try:
        modelParts = modelPathPattern.findall(modelPath)
        if not modelParts:
            raise ValueError('Invalid model path: %s' % modelPath)
        depth = len(modelParts)
        if depth < 1 or depth > 5:
            raise ValueError('Model path with %d parts not supported' % depth)
        result = _resolveID(depth, modelPath, db, debug)
        if debug:
            logger.info('Got ID %d for path %s' % (result, modelPath))
            system.util.sendLogMessage('MES: Got ID %d for path %s' % (result, modelPath), 'MES')
        return result
    except Exception as e:
        logger.error('Error getting ID for %s: %s' % (modelPath, str(e)))
        if debug:
            system.util.sendLogMessage('MES: Error getting ID for %s: %s' % (modelPath, str(e)), 'MES')
        raise
