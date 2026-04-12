"""
MaintainX Work Requests
========================
Ignition Gateway Script Library: maintainx.workrequests

Functions for listing, retrieving, and creating work requests
in MaintainX via the REST API.

Work Requests vs Work Orders:
  - Work Requests go through an approval flow before becoming Work Orders.
  - Use this module when you want a human (admin) to review and approve
    before the task is assigned.
  - Use maintainx.workorders for direct task creation (no approval needed).

Typical flow:
  1. Operator submits a work request from Perspective
  2. MaintainX admin reviews and approves
  3. MaintainX converts the request into a work order
  4. Work order is assigned and completed

Usage:
    import maintainx.workrequests as wr
    
    # Create a maintenance request
    result = wr.create(
        title = "Line 2 Filler - Leak on discharge valve",
        description = "Product buildup causing slow leak",
        priority = "MEDIUM"
    )
    
    # List all pending requests
    requests = wr.list()
    
    # Get details on a specific request
    request = wr.get(10933675)
"""

import maintainx.client as client
import maintainx.config as config

# =============================================================================
# LOGGER
# =============================================================================

logger = system.util.getLogger("MaintainX.WorkRequests")

# =============================================================================
# CONSTANTS
# =============================================================================

ENDPOINT = "/workrequests"
LIST_KEY = "workRequests"
DETAIL_KEY = "workRequest"

# =============================================================================
# LIST WORK REQUESTS
# =============================================================================

def list(limit=None, cursor=None):
	"""
	List work requests.
	
	Args:
		limit (int): Number of records per page (default from config)
		cursor (str): Pagination cursor for next page
	
	Returns:
		dict: {
			"success": bool,
			"workRequests": list of work request dicts,
			"nextCursor": str or None,
			"error": str or None
		}
	"""
	params = {
		"limit": limit or config.DEFAULT_LIMIT,
		"cursor": cursor
	}
	
	logger.debug("Listing work requests")
	
	result = client.get(ENDPOINT, params)
	
	if result["success"]:
		data = result["data"]
		workRequests = data.get(LIST_KEY, [])
		nextCursor = data.get("nextCursor", None)
		
		logger.info("Listed %d work requests" % len(workRequests))
		
		return {
			"success": True,
			"workRequests": workRequests,
			"nextCursor": nextCursor,
			"error": None
		}
	else:
		return {
			"success": False,
			"workRequests": [],
			"nextCursor": None,
			"error": result["error"]
		}


def listAll():
	"""
	List ALL work requests, automatically paginating through all pages.
	
	Returns:
		dict: {
			"success": bool,
			"workRequests": list of all work request dicts,
			"totalCount": int,
			"error": str or None
		}
	"""
	logger.info("Fetching all work requests")
	
	result = client.getAll(ENDPOINT, LIST_KEY)
	
	return {
		"success": result["success"],
		"workRequests": result["data"],
		"totalCount": result["totalCount"],
		"error": result["error"]
	}


# =============================================================================
# GET SINGLE WORK REQUEST
# =============================================================================

def get(workRequestId):
	"""
	Get a single work request by ID.
	
	Args:
		workRequestId (int/str): The work request ID
	
	Returns:
		dict: {
			"success": bool,
			"workRequest": dict with work request details or None,
			"error": str or None
		}
	"""
	endpoint = "%s/%s" % (ENDPOINT, workRequestId)
	
	logger.debug("Getting work request %s" % workRequestId)
	
	result = client.get(endpoint)
	
	if result["success"]:
		data = result["data"]
		workRequest = data.get(DETAIL_KEY, data)
		
		logger.info("Retrieved work request %s: %s" % (
			workRequestId, workRequest.get("title", "N/A")
		))
		
		return {
			"success": True,
			"workRequest": workRequest,
			"error": None
		}
	else:
		return {
			"success": False,
			"workRequest": None,
			"error": result["error"]
		}


# =============================================================================
# CREATE WORK REQUEST
# =============================================================================

def create(title, description="", priority="NONE", assetId=None, locationId=None):
	"""
	Create a new work request in MaintainX.
	
	This creates a request that must be approved by an admin before it
	becomes a work order. Use maintainx.workorders.create() if you want
	to skip the approval step.
	
	Note: If providing both assetId and locationId, the asset must belong
	to the specified location or MaintainX will return a 400 error.
	
	Args:
		title (str): Work request title (required)
		description (str): Detailed description of the issue
		priority (str): "NONE", "LOW", "MEDIUM", "HIGH"
		assetId (int): Asset ID to attach (optional)
		locationId (int): Location ID (optional)
	
	Returns:
		dict: {
			"success": bool,
			"workRequestId": int or None,
			"workRequest": dict with details (fetched after create) or None,
			"error": str or None
		}
	"""
	# Build the request body - only include non-None fields
	body = {
		"title": title,
		"description": description,
		"priority": priority
	}
	
	if assetId is not None:
		body["assetId"] = assetId
	if locationId is not None:
		body["locationId"] = locationId
	
	logger.info("Creating work request: %s (priority=%s)" % (title, priority))
	
	result = client.post(ENDPOINT, body)
	
	if result["success"]:
		data = result["data"]
		
		# POST /workrequests returns {"id": ...} only
		workRequestId = data.get("id", None)
		
		logger.info("Created work request %s: %s" % (workRequestId, title))
		
		# Fetch the full details since the POST only returns the ID
		fullDetails = None
		if workRequestId:
			detailResult = get(workRequestId)
			if detailResult["success"]:
				fullDetails = detailResult["workRequest"]
				logger.debug("Fetched full details for work request %s" % workRequestId)
			else:
				logger.warn("Created work request %s but could not fetch details: %s" % (
					workRequestId, detailResult["error"]
				))
		
		return {
			"success": True,
			"workRequestId": workRequestId,
			"workRequest": fullDetails,
			"error": None
		}
	else:
		logger.error("Failed to create work request '%s': %s" % (title, result["error"]))
		return {
			"success": False,
			"workRequestId": None,
			"workRequest": None,
			"error": result["error"]
		}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

def createSimple(title, description="", priority="MEDIUM"):
	"""
	Create a simple work request with just title, description, and priority.
	No asset or location required.
	
	This is the easiest way to submit a maintenance request from a
	Perspective operator screen.
	
	Args:
		title (str): What needs to be done
		description (str): Additional details
		priority (str): "NONE", "LOW", "MEDIUM", "HIGH"
	
	Returns:
		dict: Same as create()
	
	Example:
		import maintainx.workrequests as wr
		result = wr.createSimple(
		    "Conveyor belt squeaking on Line 1",
		    "Noise started this morning, getting louder",
		    "HIGH"
		)
		if result["success"]:
		    print "Request submitted: %s" % result["workRequestId"]
	"""
	return create(
		title=title,
		description=description,
		priority=priority
	)


def createForAsset(title, assetId, locationId, description="", priority="MEDIUM"):
	"""
	Create a work request tied to a specific asset and location.
	
	Make sure the asset belongs to the location or you'll get a 400 error.
	
	Args:
		title (str): What needs to be done
		assetId (int): The asset ID from MaintainX
		locationId (int): The location ID (asset must belong to this location)
		description (str): Additional details
		priority (str): "NONE", "LOW", "MEDIUM", "HIGH"
	
	Returns:
		dict: Same as create()
	
	Example:
		import maintainx.workrequests as wr
		result = wr.createForAsset(
		    "Filler 1 - Check seals",
		    assetId = 15967534,
		    locationId = 4605031,
		    description = "Operator noticed dripping near the fill head",
		    priority = "HIGH"
		)
	"""
	return create(
		title=title,
		description=description,
		priority=priority,
		assetId=assetId,
		locationId=locationId
	)