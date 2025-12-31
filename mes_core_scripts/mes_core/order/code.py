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
'''

from shared.mes_core.model import getLineID

db = 'mes_core'

#come back to this
def addProductCode(productCode, description, disable=False, db=db):
	query = """
		INSERT INTO productcode(productcode,description,disable,"TimeStamp")
		VALUES(?,?,?,now())
		ON CONFLICT (productcode) DO UPDATE SET
		productcode = EXCLUDED.productcode,
		description = EXCLUDED.description,
		disable = EXCLUDED.disable,
		"TimeStamp" = now()
	
	"""
	
	key = system.db.runPrepUpdate(query, [productCode, description, disable], db, getKey=1)
	return key
	
def updateProductCodeLineStatus(productCode, modelPath, enable=True, db=db):
	try:
		productCodeID = system.db.runScalarPrepQuery("""
			SELECT id FROM productcode
			WHERE productcode = ?
		""",[productCode],db)
		
		lineID = getLineID(modelPath)
		
		pclID = system.db.runScalarPrepQuery("""
			SELECT id FROM productcodeline
			WHERE productcodeid =?
			AND lineid = ?
		""", [productCodeID, lineID], db)
		
		if pclID:
			system.db.runPrepUpdate("""
				UPDATE productcodeline
				SET enable = ?, "TimeStamp" = now()
				WHERE productcodeid = ?
				AND lineid = ?
			""", [enable,productCodeID,lineID],db)
			
		else:
			system.db.runPrepUpdate("""
				INSERT INTO productcodeline(productcodeid, lineid, enable, "TimeStamp")
				VALUES(?,?,?,now())
			""", [productCodeID, lineID, enable], db)
			
		return 1
	
	except:
		return 0
		
def addWorkOrderEntry(workOrder, productCode, quantity, db=db):
	pcID = system.db.runScalarPrepQuery("""
		SELECT id FROM productcode 
		WHERE productcode = ?
	""",[productCode], db)
	
	query = """
	INSERT INTO workorder(workorder,quantity,closed,hide,"TimeStamp",productcodeid,productcode)
	VALUES(?,?,FALSE,FALSE,now(),?,?)
	ON CONFLICT (workorder) DO UPDATE SET
	quantity = EXCLUDED.quantity,
	productcodeid = EXCLUDED.productcodeid,
	productcode = EXCLUDED.productcode,
	"TimeStamp" = now()
	"""
	system.db.runPrepUpdate(query,[workOrder, quantity, pcID, productCode], db)
	
		
def updateWorkOrderEntry(oldWorkOrderID, newWorkOrder, productCode, quantity, db=db):
	pcID = system.db.runScalarPrepQuery("""
		SELECT id
		FROM productcode
		WHERE productcode = ?
		""", [productCode], db)
	
	query = """
		UPDATE workorder
		SET workorder = ?
		,	quantity = ?
		,	productcodeid = ?
		,	productcode = ?
		WHERE id = ?	
	"""
	system.db.runPrepUpdate(query, [newWorkOrder, quantity, pcID, productCode, oldWorkOrderID], db)
