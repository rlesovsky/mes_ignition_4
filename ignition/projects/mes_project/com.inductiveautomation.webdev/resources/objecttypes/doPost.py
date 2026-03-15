def doPost(request, session):
	requestData = request["postData"]
	elementIds = requestData.get("elementIds", [])
	return i3x.handlers.getObjectTypes(None, elementIds)