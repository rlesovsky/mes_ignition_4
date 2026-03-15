def doDelete(request, session):
	remainingPath = request["remainingPath"]
	callType = "delete"
	subscriptionId = None
	if remainingPath != None and remainingPath != "":
		subscriptionId = remainingPath[1:]
	return i3x.handlers.getSubscriptions(request["servletResponse"], callType, subscriptionId)