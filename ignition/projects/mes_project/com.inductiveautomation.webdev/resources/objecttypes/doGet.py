def doGet(request, session):
	params = request["params"]
	namespaceUri = params.get("namespaceUri", None)
	return i3x.handlers.getObjectTypes(namespaceUri)