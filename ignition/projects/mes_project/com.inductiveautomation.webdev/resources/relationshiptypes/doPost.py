def doPost(request, session):
	requestData = request["postData"]
	elementIds = requestData.get("elementIds", None)
	return i3x.handlers.getRelationshipTypes(None, elementIds)