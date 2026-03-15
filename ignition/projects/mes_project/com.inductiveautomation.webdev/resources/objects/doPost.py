def doPost(request, session):
	requestData = request["postData"]
	elementIds = requestData.get("elementIds", [])
	callType = "list"
	remainingPath = request["remainingPath"]
	if remainingPath != None and remainingPath != "" and remainingPath.endswith("/related"):
		callType = "related"
	elif remainingPath != None and remainingPath != "" and remainingPath.endswith("/value"):
		callType = "value"
	elif remainingPath != None and remainingPath != "" and remainingPath.endswith("/history"):
		callType = "history"
	
	includeMetadata = requestData.get("includeMetadata", False)
	relationshipType = requestData.get("relationshiptype", None)
	maxDepth = requestData.get("maxDepth", 1)
	startTime = requestData.get("startTime", None)
	endTime = requestData.get("endTime", None)
	
	return i3x.handlers.getObjects(None, includeMetadata, elementIds, callType, relationshipType, maxDepth, startTime, endTime)