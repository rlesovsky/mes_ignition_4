def doGet(request, session):
	remainingPath = request["remainingPath"]
	callType = "list"
	subscriptionId = None
	if remainingPath != None and remainingPath != "" and remainingPath.endswith("/stream"):
		callType = "stream"
		subscriptionId = remainingPath.replace("/stream", "")[1:]
	elif remainingPath != None and remainingPath != "":
		callType = "get"
		subscriptionId = remainingPath[1:]
	return i3x.handlers.getSubscriptions(request["servletResponse"], callType, subscriptionId)