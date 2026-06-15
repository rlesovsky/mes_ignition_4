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
MES Core Product/WorkOrder Management - PostgreSQL Version

MySQL to PostgreSQL conversions:
- ON DUPLICATE KEY UPDATE -> ON CONFLICT ... DO UPDATE
- values(column) -> EXCLUDED.column
- now() -> CURRENT_TIMESTAMP
- Mixed case columns -> lowercase
- insert table(...) -> INSERT INTO table(...)
'''

from mes_core.model import getLineID

db = 'mes_core'
logger = system.util.getLogger("MES_Order")


def addProductCode(productCode, description, disable=False, db=db):
	"""
	Insert or update a product code.
	
	PostgreSQL uses ON CONFLICT with EXCLUDED to reference the would-be inserted values.
	Requires a UNIQUE constraint on productcode column.
	"""
	query = """
		INSERT INTO productcode (productcode, description, disable, "TimeStamp")
		VALUES (?, ?, ?, CURRENT_TIMESTAMP)
		ON CONFLICT (productcode) DO UPDATE SET
			description = EXCLUDED.description,
			disable = EXCLUDED.disable,
			"TimeStamp" = CURRENT_TIMESTAMP
		RETURNING id
	"""
	
	# Use runPrepQuery to get the returned ID
	result = system.db.runPrepQuery(query, [productCode, description, disable], db)
	
	if len(result) > 0:
		return result[0][0]
	return None


def updateProductCodeLineStatus(productCode, modelPath, enable=True, db=db):
	"""
	Enable/disable a product code for a specific line.
	"""
	try:
		# Get ProductCode ID
		productCodeID = system.db.runScalarPrepQuery("""
			SELECT id FROM productcode WHERE productcode = ?
		""", [productCode], db)
		
		if productCodeID is None:
			return 0
		
		# Get Line ID
		lineID = getLineID(modelPath)
		
		# Check if record exists
		pclID = system.db.runScalarPrepQuery("""
			SELECT id FROM productcodeline 
			WHERE productcodeid = ? AND lineid = ?
		""", [productCodeID, lineID], db)
		
		if pclID:
			# Update existing record
			system.db.runPrepUpdate("""
				UPDATE productcodeline 
				SET enable = ?, "TimeStamp" = CURRENT_TIMESTAMP
				WHERE productcodeid = ? AND lineid = ?
			""", [enable, productCodeID, lineID], db)
		else:
			# Insert new record
			system.db.runPrepUpdate("""
				INSERT INTO productcodeline (productcodeid, lineid, enable, "TimeStamp")
				VALUES (?, ?, ?, CURRENT_TIMESTAMP)
			""", [productCodeID, lineID, enable], db)
		
		return 1
		
	except Exception as e:
		logger.error("updateProductCodeLineStatus error: %s" % str(e))
		return 0


def addWorkOrderEntry(workOrder, productCode, quantity, db=db):
	"""
	Insert or update a work order.
	
	Note: Fixed bug - original code had 'productcode' instead of 'productCode' variable.
	"""
	# Get ProductCode ID
	pcID = system.db.runScalarPrepQuery("""
		SELECT id FROM productcode WHERE productcode = ?
	""", [productCode], db)  # Fixed: was 'productcode' (lowercase variable)
	
	query = """
		INSERT INTO workorder (workorder, quantity, closed, hide, "TimeStamp", productcodeid, productcode)
		VALUES (?, ?, false, false, CURRENT_TIMESTAMP, ?, ?)
		ON CONFLICT (workorder) DO UPDATE SET
			quantity = EXCLUDED.quantity,
			productcodeid = EXCLUDED.productcodeid,
			productcode = EXCLUDED.productcode,
			"TimeStamp" = CURRENT_TIMESTAMP
	"""
	
	system.db.runPrepUpdate(query, [workOrder, quantity, pcID, productCode], db)


def updateWorkOrderEntry(oldWorkOrderID, newWorkOrder, productCode, quantity, db=db):
	"""
	Update an existing work order by ID.
	"""
	# Get ProductCode ID
	pcID = system.db.runScalarPrepQuery("""
		SELECT id FROM productcode WHERE productcode = ?
	""", [productCode], db)
	
	query = """
		UPDATE workorder 
		SET workorder = ?, 
			quantity = ?, 
			productcodeid = ?, 
			productcode = ?,
			"TimeStamp" = CURRENT_TIMESTAMP
		WHERE id = ?
	"""
	
	system.db.runPrepUpdate(query, [newWorkOrder, quantity, pcID, productCode, oldWorkOrderID], db)
	
	
def setProductRate(productCodeId, standardRate, theoreticalRate, db=db):
    """Insert or update the standard/theoretical rate for a product code."""
    try:
        query = '''
            INSERT INTO productcoderate (productcodeid, standard_rate, theoretical_rate, "TimeStamp")
            VALUES (?, ?, ?, CURRENT_TIMESTAMP)
            ON CONFLICT (productcodeid) DO UPDATE SET
                standard_rate    = EXCLUDED.standard_rate,
                theoretical_rate = EXCLUDED.theoretical_rate,
                "TimeStamp"      = CURRENT_TIMESTAMP
        '''
        system.db.runPrepUpdate(query, [productCodeId, standardRate, theoreticalRate], db)
        return 1
    except Exception as e:
        logger.error("setProductRate error for product %s: %s" % (productCodeId, str(e)))
        return 0