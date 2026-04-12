"""
MaintainX Work Orders
======================
Ignition Gateway Script Library: maintainx.workorders

Functions for listing, retrieving, creating, and updating work orders
in MaintainX via the REST API.

Note: The MaintainX list endpoint does NOT support server-side filtering
by status or priority. Filtering is done client-side after fetching.

Usage:
    import maintainx.workorders as wo
    
    # List open work orders
    orders = wo.list(status="OPEN")
    
    # Get a specific work order with expanded details
    order = wo.get(93084623, expand=["assignees", "asset", "location"])
    
    # Create a new work order
    result = wo.create(
        title = "PM - Filler 1 Inspection",
        description = "Monthly vibration check",
        priority = "HIGH",
        assetId = 15967534,
        locationId = 4605031,
        assignees = [{"id": 1301453, "type": "USER"}],
        categories = ["Inspection"]
    )
"""

import maintainx.client as client
import maintainx.config as config

logger = system.util.getLogger("MaintainX.WorkOrders")

ENDPOINT = "/workorders"
LIST_KEY = "workOrders"
DETAIL_KEY = "workOrder"

def list(limit=None, cursor=None, status=None, priority=None, locationId=None, assetId=None):
	"""
	List work orders with optional client-side filters.
	
	Note: MaintainX API does not support server-side filtering by status,
	priority, locationId, or assetId. All filtering is done client-side.
	
	Args:
		limit (int): Number of records per page (default from config)
		cursor (str): Pagination cursor for next page
		status (str): Client-side filter - "OPEN", "IN_PROGRESS", "ON_HOLD", "DONE"
		priority (str): Client-side filter - "NONE", "LOW", "MEDIUM", "HIGH"
		locationId (int): Client-side filter by location ID
		assetId (int): Client-side filter by asset ID
	
	Returns:
		dict: {
			"success": bool,
			"workOrders": list of work order dicts,
			"nextCursor": str or None,
			"error": str or None
		}
	"""
	# Only pass API-supported params (limit, cursor)
	params = {
		"limit": limit or config.DEFAULT_LIMIT,
		"cursor": cursor
	}
	
	logger.debug("Listing work orders (status=%s, priority=%s, locationId=%s)" % (status, priority, locationId))
	
	result = client.get(ENDPOINT, params)
	
	if result["success"]:
		data = result["data"]
		workOrders = data.get(LIST_KEY, [])
		nextCursor = data.get("nextCursor", None)
		
		# Client-side filtering
		if status:
			workOrders = [wo for wo in workOrders if wo.get("status") == status]
		if priority:
			workOrders = [wo for wo in workOrders if wo.get("priority") == priority]
		if locationId:
			workOrders = [wo for wo in workOrders if wo.get("locationId") == locationId]
		if assetId:
			workOrders = [wo for wo in workOrders if wo.get("assetId") == assetId]
		
		logger.info("Listed %d work orders (after filters)" % len(workOrders))
		
		return {
			"success": True,
			"workOrders": workOrders,
			"nextCursor": nextCursor,
			"error": None
		}
	else:
		return {
			"success": False,
			"workOrders": [],
			"nextCursor": None,
			"error": result["error"]
		}

def listAll(status=None, priority=None, locationId=None, assetId=None):
	"""
	List ALL work orders, automatically paginating through all pages.
	Client-side filtering applied after fetching all pages.
	"""
	logger.info("Fetching all work orders")
	
	result = client.getAll(ENDPOINT, LIST_KEY)
	
	workOrders = result["data"]
	
	# Client-side filtering
	if status:
		workOrders = [wo for wo in workOrders if wo.get("status") == status]
	if priority:
		workOrders = [wo for wo in workOrders if wo.get("priority") == priority]
	if locationId:
		workOrders = [wo for wo in workOrders if wo.get("locationId") == locationId]
	if assetId:
		workOrders = [wo for wo in workOrders if wo.get("assetId") == assetId]
	
	return {
		"success": result["success"],
		"workOrders": workOrders,
		"totalCount": len(workOrders),
		"error": result["error"]
	}

def get(workOrderId, expand=None):
	endpoint = "%s/%s" % (ENDPOINT, workOrderId)
	params = {}
	if expand:
		params["expand"] = expand
	logger.debug("Getting work order %s (expand=%s)" % (workOrderId, expand))
	result = client.get(endpoint, params)
	if result["success"]:
		data = result["data"]
		workOrder = data.get(DETAIL_KEY, data)
		logger.info("Retrieved work order %s: %s" % (workOrderId, workOrder.get("title", "N/A")))
		return {"success": True, "workOrder": workOrder, "error": None}
	else:
		return {"success": False, "workOrder": None, "error": result["error"]}

def create(title, description="", priority="NONE", assetId=None, locationId=None,
           assignees=None, categories=None, estimatedTime=None, procedure=None):
	body = {"title": title, "description": description, "priority": priority}
	if assetId is not None:
		body["assetId"] = assetId
	if locationId is not None:
		body["locationId"] = locationId
	if assignees is not None:
		body["assignees"] = assignees
	if categories is not None:
		body["categories"] = categories
	if estimatedTime is not None:
		body["estimatedTime"] = estimatedTime
	if procedure is not None:
		body["procedure"] = procedure
	logger.info("Creating work order: %s (priority=%s)" % (title, priority))
	result = client.post(ENDPOINT, body)
	if result["success"]:
		data = result["data"]
		workOrder = data.get(DETAIL_KEY, data)
		workOrderId = workOrder.get("id", data.get("id", None))
		logger.info("Created work order %s: %s" % (workOrderId, title))
		return {"success": True, "workOrderId": workOrderId, "workOrder": workOrder, "error": None}
	else:
		logger.error("Failed to create work order '%s': %s" % (title, result["error"]))
		return {"success": False, "workOrderId": None, "workOrder": None, "error": result["error"]}

def update(workOrderId, **kwargs):
	endpoint = "%s/%s" % (ENDPOINT, workOrderId)
	body = {k: v for k, v in kwargs.items() if v is not None}
	if not body:
		logger.warn("Update called with no fields to change for WO %s" % workOrderId)
		return {"success": False, "workOrder": None, "error": "No fields provided to update"}
	logger.info("Updating work order %s: %s" % (workOrderId, list(body.keys())))
	result = client.patch(endpoint, body)
	if result["success"]:
		data = result["data"]
		workOrder = data.get(DETAIL_KEY, data)
		logger.info("Updated work order %s" % workOrderId)
		return {"success": True, "workOrder": workOrder, "error": None}
	else:
		logger.error("Failed to update work order %s: %s" % (workOrderId, result["error"]))
		return {"success": False, "workOrder": None, "error": result["error"]}

def updateStatus(workOrderId, status):
	return update(workOrderId, status=status)

def close(workOrderId):
	logger.info("Closing work order %s" % workOrderId)
	return updateStatus(workOrderId, config.WOStatus.DONE)

def getOpen(limit=None, locationId=None):
	return list(limit=limit, status=config.WOStatus.OPEN, locationId=locationId)

def getHighPriority(limit=None, locationId=None):
	return list(limit=limit, priority=config.Priority.HIGH, locationId=locationId)