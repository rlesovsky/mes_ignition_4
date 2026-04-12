"""
MaintainX API Client
=====================
Ignition Gateway Script Library: maintainx.client

Core HTTP client wrapper for all MaintainX API calls.
Handles authentication, request/response processing, error decoding,
pagination, and logging.

All other modules (workorders, workrequests) call through this client.

Usage from Script Console:
    import maintainx.client as client
    result = client.get("/workorders", {"limit": 5})
    print result
"""

import maintainx.config as config

# =============================================================================
# LOGGER
# =============================================================================

logger = system.util.getLogger("MaintainX.Client")

# =============================================================================
# INTERNAL HELPERS
# =============================================================================

def _getHeaders():
	"""Build the standard request headers with Bearer auth."""
	return {
		"Content-Type": "application/json",
		"Accept": "application/json",
		"Authorization": "Bearer %s" % config.API_KEY
	}


def _buildUrl(endpoint, params=None):
	"""
	Build the full URL from an endpoint path and optional query params.
	
	Args:
		endpoint (str): API path, e.g. "/workorders" or "/workorders/12345"
		params (dict): Optional query parameters, e.g. {"limit": 10, "status": "OPEN"}
	
	Returns:
		str: Full URL with query string
	"""
	# Strip leading slash if present to avoid double slash
	if endpoint.startswith("/"):
		endpoint = endpoint[1:]
	
	url = "%s/%s" % (config.BASE_URL, endpoint)
	
	if params:
		# Filter out None values
		cleanParams = {k: v for k, v in params.items() if v is not None}
		if cleanParams:
			queryParts = []
			for key, value in cleanParams.items():
				# Handle list values (e.g. expand=assignees&expand=asset)
				if isinstance(value, list):
					for item in value:
						queryParts.append("%s=%s" % (key, item))
				else:
					queryParts.append("%s=%s" % (key, value))
			url = "%s?%s" % (url, "&".join(queryParts))
	
	return url


def _decodeResponseBody(response):
	"""
	Decode the response body, handling the byte array issue.
	
	MaintainX error responses come back as byte arrays in Jython.
	This safely decodes them to a readable string.
	
	Args:
		response: The JythonHttpResponse object
	
	Returns:
		str: Decoded response body
	"""
	body = response.body
	
	if body is None:
		return ""
	
	# Handle byte array responses
	if hasattr(body, 'tostring'):
		return body.tostring()
	
	return str(body)


def _parseJsonResponse(response):
	"""
	Parse a successful JSON response.
	
	Args:
		response: The JythonHttpResponse object
	
	Returns:
		dict: Parsed JSON data
	"""
	try:
		return response.json
	except Exception as e:
		logger.error("Failed to parse JSON response: %s" % str(e))
		return {}

# =============================================================================
# PUBLIC API METHODS
# =============================================================================

def get(endpoint, params=None):
	"""
	Make a GET request to the MaintainX API.
	
	Args:
		endpoint (str): API path, e.g. "/workorders" or "/workorders/12345"
		params (dict): Optional query parameters
	
	Returns:
		dict: {
			"success": bool,
			"statusCode": int,
			"data": dict (parsed JSON) or None,
			"error": str or None
		}
	"""
	url = _buildUrl(endpoint, params)
	headers = _getHeaders()
	
	logger.debug("GET %s" % url)
	
	try:
		client = system.net.httpClient()
		response = client.get(url, headers=headers)
		
		statusCode = response.statusCode
		logger.debug("GET %s -> %d" % (endpoint, statusCode))
		
		if response.good:
			data = _parseJsonResponse(response)
			logger.info("GET %s -> %d (OK)" % (endpoint, statusCode))
			return {
				"success": True,
				"statusCode": statusCode,
				"data": data,
				"error": None
			}
		else:
			errorBody = _decodeResponseBody(response)
			logger.error("GET %s -> %d: %s" % (endpoint, statusCode, errorBody))
			return {
				"success": False,
				"statusCode": statusCode,
				"data": None,
				"error": errorBody
			}
	
	except Exception as e:
		logger.error("GET %s -> Exception: %s" % (endpoint, str(e)))
		return {
			"success": False,
			"statusCode": 0,
			"data": None,
			"error": str(e)
		}


def post(endpoint, body):
	"""
	Make a POST request to the MaintainX API.
	
	Args:
		endpoint (str): API path, e.g. "/workorders" or "/workrequests"
		body (dict): JSON body to send
	
	Returns:
		dict: {
			"success": bool,
			"statusCode": int,
			"data": dict (parsed JSON) or None,
			"error": str or None
		}
	"""
	url = _buildUrl(endpoint)
	headers = _getHeaders()
	
	logger.debug("POST %s" % url)
	
	try:
		client = system.net.httpClient()
		response = client.post(url, data=body, headers=headers)
		
		statusCode = response.statusCode
		logger.debug("POST %s -> %d" % (endpoint, statusCode))
		
		if response.good:
			data = _parseJsonResponse(response)
			logger.info("POST %s -> %d (OK)" % (endpoint, statusCode))
			return {
				"success": True,
				"statusCode": statusCode,
				"data": data,
				"error": None
			}
		else:
			errorBody = _decodeResponseBody(response)
			logger.error("POST %s -> %d: %s" % (endpoint, statusCode, errorBody))
			return {
				"success": False,
				"statusCode": statusCode,
				"data": None,
				"error": errorBody
			}
	
	except Exception as e:
		logger.error("POST %s -> Exception: %s" % (endpoint, str(e)))
		return {
			"success": False,
			"statusCode": 0,
			"data": None,
			"error": str(e)
		}


def patch(endpoint, body):
	"""
	Make a PATCH request to the MaintainX API (for updates).
	
	Args:
		endpoint (str): API path, e.g. "/workorders/12345"
		body (dict): JSON body with fields to update
	
	Returns:
		dict: Same format as get() and post()
	"""
	url = _buildUrl(endpoint)
	headers = _getHeaders()
	
	logger.debug("PATCH %s" % url)
	
	try:
		client = system.net.httpClient()
		response = client.patch(url, data=body, headers=headers)
		
		statusCode = response.statusCode
		logger.debug("PATCH %s -> %d" % (endpoint, statusCode))
		
		if response.good:
			data = _parseJsonResponse(response)
			logger.info("PATCH %s -> %d (OK)" % (endpoint, statusCode))
			return {
				"success": True,
				"statusCode": statusCode,
				"data": data,
				"error": None
			}
		else:
			errorBody = _decodeResponseBody(response)
			logger.error("PATCH %s -> %d: %s" % (endpoint, statusCode, errorBody))
			return {
				"success": False,
				"statusCode": statusCode,
				"data": None,
				"error": errorBody
			}
	
	except Exception as e:
		logger.error("PATCH %s -> Exception: %s" % (endpoint, str(e)))
		return {
			"success": False,
			"statusCode": 0,
			"data": None,
			"error": str(e)
		}


def delete(endpoint):
	"""
	Make a DELETE request to the MaintainX API.
	
	Args:
		endpoint (str): API path, e.g. "/workorders/12345"
	
	Returns:
		dict: Same format as get() and post()
	"""
	url = _buildUrl(endpoint)
	headers = _getHeaders()
	
	logger.debug("DELETE %s" % url)
	
	try:
		client = system.net.httpClient()
		response = client.delete(url, headers=headers)
		
		statusCode = response.statusCode
		logger.debug("DELETE %s -> %d" % (endpoint, statusCode))
		
		if response.good:
			data = _parseJsonResponse(response)
			logger.info("DELETE %s -> %d (OK)" % (endpoint, statusCode))
			return {
				"success": True,
				"statusCode": statusCode,
				"data": data,
				"error": None
			}
		else:
			errorBody = _decodeResponseBody(response)
			logger.error("DELETE %s -> %d: %s" % (endpoint, statusCode, errorBody))
			return {
				"success": False,
				"statusCode": statusCode,
				"data": None,
				"error": errorBody
			}
	
	except Exception as e:
		logger.error("DELETE %s -> Exception: %s" % (endpoint, str(e)))
		return {
			"success": False,
			"statusCode": 0,
			"data": None,
			"error": str(e)
		}


# =============================================================================
# PAGINATION HELPER
# =============================================================================

def getAll(endpoint, listKey, params=None):
	"""
	Paginate through all results for a list endpoint.
	
	Uses cursor-based pagination. MaintainX returns a 'nextCursor' field
	in list responses. We keep fetching until nextCursor is None.
	
	Args:
		endpoint (str): API path, e.g. "/workorders"
		listKey (str): The key in the response that contains the array,
		               e.g. "workOrders" for the /workorders endpoint
		params (dict): Optional query parameters (limit, status, etc.)
	
	Returns:
		dict: {
			"success": bool,
			"data": list of all records,
			"totalCount": int,
			"error": str or None
		}
	"""
	allRecords = []
	pageCount = 0
	cursor = None
	
	if params is None:
		params = {}
	
	# Set default limit if not specified
	if "limit" not in params:
		params["limit"] = config.DEFAULT_LIMIT
	
	logger.info("Paginating %s (listKey=%s)" % (endpoint, listKey))
	
	while pageCount < config.MAX_PAGES:
		# Add cursor to params if we have one
		if cursor:
			params["cursor"] = cursor
		elif "cursor" in params:
			del params["cursor"]
		
		result = get(endpoint, params)
		
		if not result["success"]:
			logger.error("Pagination failed on page %d: %s" % (pageCount + 1, result["error"]))
			return {
				"success": False,
				"data": allRecords,
				"totalCount": len(allRecords),
				"error": "Failed on page %d: %s" % (pageCount + 1, result["error"])
			}
		
		data = result["data"]
		records = data.get(listKey, [])
		allRecords.extend(records)
		pageCount += 1
		
		logger.debug("Page %d: got %d records (total: %d)" % (pageCount, len(records), len(allRecords)))
		
		# Check for next page
		cursor = data.get("nextCursor", None)
		if not cursor:
			break
		
		# Rate limit protection
		if config.PAGE_DELAY_MS > 0:
			system.util.sleep(config.PAGE_DELAY_MS)
	
	logger.info("Pagination complete: %d records across %d pages" % (len(allRecords), pageCount))
	
	return {
		"success": True,
		"data": allRecords,
		"totalCount": len(allRecords),
		"error": None
	}