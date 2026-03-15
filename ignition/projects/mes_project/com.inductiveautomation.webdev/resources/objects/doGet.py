def doGet(request, session):
	params = request["params"]
	typeId = params.get("typeId", None)
	includeMetadata = params.get("includeMetadata", "false").lower() == "true"
	return i3x.handlers.getObjects(typeId, includeMetadata)