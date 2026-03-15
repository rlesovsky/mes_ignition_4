def doPost(request, session):
	requestData = request["postData"]
	remainingPath = request["remainingPath"]
	callType = "create"
	subscriptionId = None
	if remainingPath != None and remainingPath != "" and remainingPath.endswith("/register"):
		callType = "register"
		subscriptionId = remainingPath.replace("/register", "")[1:]
	elif remainingPath != None and remainingPath != "" and remainingPath.endswith("/unregister"):
		callType = "unregister"
		subscriptionId = remainingPath.replace("/unregister", "")[1:]
	elif remainingPath != None and remainingPath != "" and remainingPath.endswith("/sync"):
		callType = "sync"
		subscriptionId = remainingPath.replace("/sync", "")[1:]
	return i3x.handlers.getSubscriptions(request["servletResponse"], callType, subscriptionId, requestData)