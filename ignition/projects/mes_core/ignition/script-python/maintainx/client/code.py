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

from java.net import URLEncoder

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


def _encode(value):
	"""URL-encode a query key or value (UTF-8) so special characters in filter
	values can't break or inject into the query string."""
	return URLEncoder.encode("%s" % value, "UTF-8")


def _client():
	"""HTTP client with the configured CONNECTION timeout.

	The httpClient() constructor's `timeout` is the connection timeout only and
	has no read_timeout argument. The per-request READ timeout is applied
	separately on each verb call (get/post/patch/delete) as their documented
	`timeout` parameter, so a hung MaintainX endpoint can't block the caller."""
	return system.net.httpClient(timeout=config.CONNECT_TIMEOUT_MS)


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
						queryParts.append("%s=%s" % (_encode(key), _encode(item)))
				else:
					queryParts.append("%s=%s" % (_encode(key), _encode(value)))
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
# REQUEST EXECUTION (shared retry + result normalization)
# =============================================================================

def _handle(method, endpoint, call):
	"""Execute an HTTP call, retry on HTTP 429 with linear backoff, and
	normalize the outcome to the standard {success, statusCode, data, error}
	dict used by every public method.

	`call` is a zero-arg callable returning the JythonHttpResponse, so the
	request can be re-issued on retry. Backoff uses the previously-unused
	config.MAX_RETRIES / config.RETRY_DELAY_MS settings.
	"""
	attempt = 0
	while True:
		try:
			response = call()
		except Exception as e:
			logger.error("%s %s -> Exception: %s" % (method, endpoint, str(e)))
			return {"success": False, "statusCode": 0, "data": None, "error": str(e)}

		statusCode = response.statusCode
		logger.debug("%s %s -> %d" % (method, endpoint, statusCode))

		# Retry on HTTP 429 (rate limited) with linear backoff.
		if statusCode == 429 and attempt < config.MAX_RETRIES:
			attempt += 1
			delay = config.RETRY_DELAY_MS * attempt
			logger.warn("%s %s -> 429 rate limited; retry %d/%d after %d ms"
				% (method, endpoint, attempt, config.MAX_RETRIES, delay))
			system.util.sleep(delay)
			continue

		if response.good:
			data = _parseJsonResponse(response)
			logger.info("%s %s -> %d (OK)" % (method, endpoint, statusCode))
			return {"success": True, "statusCode": statusCode, "data": data, "error": None}

		errorBody = _decodeResponseBody(response)
		logger.error("%s %s -> %d: %s" % (method, endpoint, statusCode, errorBody))
		return {"success": False, "statusCode": statusCode, "data": None, "error": errorBody}


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
	return _handle("GET", endpoint, lambda: _client().get(url, headers=headers, timeout=config.READ_TIMEOUT_MS))


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
	return _handle("POST", endpoint, lambda: _client().post(url, data=body, headers=headers, timeout=config.READ_TIMEOUT_MS))


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
	return _handle("PATCH", endpoint, lambda: _client().patch(url, data=body, headers=headers, timeout=config.READ_TIMEOUT_MS))


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
	return _handle("DELETE", endpoint, lambda: _client().delete(url, headers=headers, timeout=config.READ_TIMEOUT_MS))


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
	
	# Copy so the cursor/limit mutations below don't leak back into the
	# caller's dict (cursor-injection side effect on repeated calls).
	if params is None:
		params = {}
	else:
		params = dict(params)

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