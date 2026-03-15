def getRelationshipTypes(namespaceUri=None, elementIds=None):
	log = system.util.getLogger("i3x.relationshiptypes")
	
	ret = []
	
	relationships = {
		"HasParent":{
			"elementId": "HasParent",
			"displayName": "HasParent",
			"namespaceUri": "https://cesmii.org/i3x",
			"reverseOf": "HasChildren"
		},
		"HasChildren":{
			"elementId": "HasChildren",
			"displayName": "HasChildren",
			"namespaceUri": "https://cesmii.org/i3x",
			"reverseOf": "HasParent"
		},
		"HasComponent":{
			"elementId": "HasComponent",
			"displayName": "HasComponent",
			"namespaceUri": "https://cesmii.org/i3x",
			"reverseOf": "ComponentOf"
		},
		"ComponentOf":{
			"elementId": "ComponentOf",
			"displayName": "ComponentOf",
			"namespaceUri": "https://cesmii.org/i3x",
			"reverseOf": "HasComponent"
		},
		"InheritedBy":{
			"elementId": "InheritedBy",
			"displayName": "InheritedBy",
			"namespaceUri": "https://cesmii.org/i3x",
			"reverseOf": "InheritsFrom"
		},
		"InheritsFrom":{
			"elementId": "InheritsFrom",
			"displayName": "InheritsFrom",
			"namespaceUri": "https://cesmii.org/i3x",
			"reverseOf": "InheritedBy"
		},
		"HasAlarm":{
			"elementId": "HasAlarm",
			"displayName": "HasAlarm",
			"namespaceUri": i3x.ignition.IgnitionNamespaceUri,
			"reverseOf": "AlarmOf"
		},
		"AlarmOf":{
			"elementId": "AlarmOf",
			"displayName": "AlarmOf",
			"namespaceUri": i3x.ignition.IgnitionNamespaceUri,
			"reverseOf": "HasAlarm"
		}
	}
	
	if elementIds == None:
		for relationship in relationships:
			obj = relationships[relationship]
			dtNamespaceUri = relationships[relationship]["namespaceUri"]
			if namespaceUri == None or namespaceUri == dtNamespaceUri:
				ret.append(obj)
	else:
		for elementId in elementIds:
			if elementId != None:
				if elementId in relationships:
					obj = relationships[elementId]
					ret.append(obj)
		
	return {'json': system.util.jsonEncode(ret)}
	
def getNamespaces():
	import urlparse
	
	log = system.util.getLogger("i3x.namespaces")
	
	ret = []
	namespaces = []

	tagProviders = i3x.ignition.getTagProviders()
	
	for tagProvider in tagProviders:
		for row in i3x.ignition.getUdtDefs(tagProvider):
			dtNamespaceUri = i3x.utils.getNamespaceUriParam(row)
			if dtNamespaceUri not in namespaces:
				namespaces.append(dtNamespaceUri)
	
	coreUAFound = False
	for namespaceUri in namespaces:
		prefix = ""
		if namespaceUri.startswith("https://inductiveautomation.com/"):
			prefix = "Ignition "
			
		if namespaceUri == i3x.ignition.UaCoreUri:
			coreUAFound = True
			
		ret.append({"uri":namespaceUri, "displayName":prefix+" ".join([word.capitalize() if word.islower() else word for word in urlparse.urlparse(namespaceUri).path[1:].replace("/", " ").split()])})
	
	if not coreUAFound:
		ret.append({"uri":i3x.ignition.UaCoreUri, "displayName":"UA"})
	
	return {'json': system.util.jsonEncode(ret)}

def getObjectTypes(namespaceUri=None, elementIds=None):
	import urllib
	
	log = system.util.getLogger("i3x.objecttypes")
	
	folderObj = {"elementId":"folder-type", "displayName":"Folder", "namespaceUri":i3x.ignition.UaCoreUri, "schema":{"type":"object", "description":"Represents a folder", "!related":{"relationshipType":"HasChildren"}}}
	tagProviderObj = {"elementId":"ignition-tag-provider", "displayName":"Tag Provider", "namespaceUri":i3x.ignition.IgnitionNamespaceUri, "schema":{"type":"object", "description":"Represents an Ignition tag provider", "!related":{"relationshipType":"HasChildren"}}}
	alarmObj = {"elementId":"ignition-alarm", "displayName":"Alarm", "namespaceUri":i3x.ignition.IgnitionNamespaceUri, "schema":{"type":"object", "description":"Represents an Ignition alarm", "!related":{"relationshipType":"AlarmOf"}, "properties":{
		"source": {
			"type": "string"
		},
		"name": {
			"type": "string"
		},
		"eventId": {
			"type": "string"
		},
		"displayPath": {
			"type": "string"
		},
		"count": {
			"type": "integer"
		},
		"label": {
			"type": "string"
		},
		"lastEventState": {
			"type": "string"
		},
		"notes": {
			"type": "string"
		},
		"priority": {
			"type": "string"
		},
		"state": {
			"type": "string"
		},
		"isActive": {
			"type": "boolean"
		},
		"isAcked": {
			"type": "boolean"
		},
		"isCleared": {
			"type": "boolean"
		},
		"isShelved": {
			"type": "boolean"
		},
		"activeData": {
			"type": "object"
		},
		"clearedData": {
			"type": "object"
		},
		"ackData": {
			"type": "object"
		}
	}}}

	tagProviders = i3x.ignition.getTagProviders()
	
	if elementIds != None:
		ret = []
		if "folder-type" in elementIds:
			ret.append(folderObj)
		if "ignition-tag-provider" in elementIds:
			ret.append(tagProviderObj)
		if "ignition-alarm" in elementIds:
			ret.append(alarmObj)
	else:
		elementIds = [None]
		ret = []
		if namespaceUri == None or namespaceUri == i3x.ignition.UaCoreUri:
			ret.append(folderObj)	
		
		if namespaceUri == None or namespaceUri == i3x.ignition.IgnitionNamespaceUri:
			ret.append(tagProviderObj)
		
		if namespaceUri == None or namespaceUri == i3x.ignition.IgnitionNamespaceUri:
			ret.append(alarmObj)
	
	for elementId in elementIds:
		udtDef = None
		udtDefTagProvider = None
		if elementId != None:
			if elementId in ["folder-type", "ignition-tag-provider", "ignition-alarm"]:
				continue
				
			udtDef = i3x.utils.elementIdToPath(elementId)
			udtDefTagProvider = i3x.utils.getTagProviderFromPath(udtDef)
		
		for tagProvider in tagProviders:
			if udtDefTagProvider != None and tagProvider != udtDefTagProvider:
				continue
			
			res = i3x.ignition.getUdtDefs(tagProvider, udtDef)
			for row in res:
				dtNamespaceUri = i3x.utils.getNamespaceUriParam(row)
				dtElementId = i3x.utils.pathToElementId(str(row["fullPath"]))
				
				if namespaceUri == None or namespaceUri == dtNamespaceUri:
					obj = {"elementId":dtElementId, "displayName":row["name"], "namespaceUri":dtNamespaceUri, "schema":i3x.ignition.buildSchema(row, tagProvider, dtNamespaceUri)}
					ret.append(obj)
	
	return {'json': system.util.jsonEncode(ret)}
	
def getObjects(typeId=None, includeMetadata=False, elementIds=None, callType="list", relationshipType=None, maxDepth=1, startTime=None, endTime=None):
	import urllib
	
	log = system.util.getLogger("i3x.objects")
		
	if typeId != None:
		typeId = i3x.utils.elementIdToPath(typeId)

	udtInstances = i3x.ignition.getUdtInstances()
	
	if callType in ["value", "history"]:
		ret = {}
	elif elementIds != None:
		ret = []
	else:
		elementIds = [None]
		ret = []
	
	for elementId in elementIds:
		found = False
	
		for udtInstancePath in udtInstances:
			udtInstance = udtInstances[udtInstancePath]
			dtElementId = udtInstance["elementId"]
			dtTypeId = udtInstance["typeId"]
			
			if typeId == None or typeId == dtTypeId:
				if udtInstance["type"] == "folder" and udtInstance["parentUdt"] != None:
					continue
				
				obj = i3x.utils.buildUdtInstanceObj(udtInstance, includeMetadata)
				if elementId != None:
					if elementId == dtElementId:					
						if callType == "related":
							ret.extend(i3x.utils.getRelatedObjects(relationshipType, "HasParent", udtInstance, udtInstances, includeMetadata))
							ret.extend(i3x.utils.getRelatedObjects(relationshipType, "AlarmOf", udtInstance, udtInstances, includeMetadata))
							ret.extend(i3x.utils.getRelatedObjects(relationshipType, "ComponentOf", udtInstance, udtInstances, includeMetadata))
							ret.extend(i3x.utils.getRelatedObjects(relationshipType, "HasChildren", udtInstance, udtInstances, includeMetadata))
							ret.extend(i3x.utils.getRelatedObjects(relationshipType, "HasComponent", udtInstance, udtInstances, includeMetadata))
							ret.extend(i3x.utils.getRelatedObjects(relationshipType, "HasAlarm", udtInstance, udtInstances, includeMetadata))
						elif callType == "value":
							data = []
							elementObj = {"data":data}
							childrenValues = {}
							quality = None
							timestamp = None
							
							if udtInstance["typeId"] == "ignition-alarm":
								alarmObj = udtInstance["alarmObj"]
								quality = "GOOD"
								timestamp = alarmObj["eventTime"]
								data.append({"value":udtInstance["alarmObj"], "quality":quality, "timestamp":timestamp})
							elif udtInstance["typeId"] != "folder-type" and udtInstance["typeId"] != "ignition-tag-provider":
								value = system.tag.readBlocking([udtInstancePath])[0]			
								value = i3x.ignition.getTagValue(udtInstance, value)
								if value != None:
									data.append(value["value"])
									childrenValues = value["childrenValues"]
									quality = value["value"]["quality"]
									timestamp = value["value"]["timestamp"]
									
								i3x.utils.addChildrenValues(udtInstances, udtInstance, elementObj, childrenValues, quality, timestamp, 2, maxDepth)
								
							ret[dtElementId] = elementObj
						elif callType == "history":
							elementObj = {"data":[]}
							
							if udtInstance["typeId"] == "ignition-alarm":
								startTime = system.date.parse(startTime, i3x.ignition.DATE_FORMAT)
								endTime = system.date.parse(endTime, i3x.ignition.DATE_FORMAT)
								res = system.alarm.queryJournal(startTime, endTime, journalName="Journal", source=udtInstancePath)
								for row in res:
									alarmObj = i3x.ignition.getAlarmObj(row)
									elementObj["data"].append({"value":alarmObj, "quality":"GOOD", "timestamp":alarmObj["eventTime"]})
							elif udtInstance["typeId"] != "folder-type" and udtInstance["typeId"] != "ignition-tag-provider":
								startTime = i3x.utils.getLocalTime(startTime)
								endTime = i3x.utils.getLocalTime(endTime)
								children = i3x.utils.getChildrenObjectNames(udtInstance, "HasComponent")
								tagConfig = system.tag.getConfiguration(udtInstancePath, True)
								if len(tagConfig) and "tags" in tagConfig[0]:
									objs = {"tags":[], "objects":{}}
									tags = i3x.utils.getTags(udtInstancePath, objs, tagConfig[0]["tags"], 1, maxDepth)
									if len(tags):
										minutes = system.date.minutesBetween(startTime, endTime)
										res = system.historian.queryAggregatedPoints(paths=tags, startTime=startTime, endTime=endTime, aggregates=["LastValue"] * len(tags), fillModes=["PREV"] * len(tags), returnFormat="WIDE", returnSize=minutes, includeBounds=True)
										cols = res.getColumnNames()
										historyValues = []
										prevValues = None
										for row in res:
											timestamp = row[0]
											rowValues = {}
											allNull = True
											for i in range(1, len(cols)):
												rowValues[cols[i]] = row[i]
												if row[i] != None:
													allNull = False
												
											if rowValues != prevValues and not allNull:
												prevValues = dict(rowValues)
												rowValues["t_stamp"] = timestamp
												historyValues.append(rowValues)
										
										i3x.utils.addChildrenHistory(elementObj, objs, historyValues)
							
							ret[dtElementId] = elementObj
						else:
							ret.append(obj)
				else:
					ret.append(obj)
	
	return {'json': system.util.jsonEncode(ret)}
	
def getSubscriptions(servletResponse, callType, subscriptionId=None, requestData=None):
	import urllib
	from jakarta.servlet.http import HttpServletResponse
	
	log = system.util.getLogger("i3x.subscriptions")
	
	ret = {}
	
	subscriptionIds = i3x.utils.getSubscriptions()
	if callType == "list":
		subscriptions = []
		for subscriptionId in subscriptionIds:
			subscriptions.append({"subscriptionId":subscriptionId, "created":system.date.format(subscriptionIds[subscriptionId]["created"], i3x.ignition.DATE_FORMAT)})
		ret["subscriptionIds"] = subscriptions
	elif callType == "create":
		ret["subscriptionId"] = i3x.utils.createSubscription()
		ret["message"] = "Subscription created successfully"
	elif callType == "get":
		if subscriptionId == None or subscriptionId not in subscriptionIds:
			servletResponse.setStatus(HttpServletResponse.SC_NOT_FOUND)
			ret["detail"] = "Subscription not found"
		else:
			subscription = subscriptionIds[subscriptionId]
			ret["subscriptionId"] = subscriptionId
			ret["created"] = system.date.format(subscription["created"], i3x.ignition.DATE_FORMAT)
			ret["isStreaming"] = subscription["isStreaming"]
			ret["queuedUpdates"] = len(subscription["queuedUpdates"])
			ret["objects"] = subscription["elementIds"]
	elif callType == "delete":
		ret["message"] = "Unsubscribe processed."
		ret["unsubscribed"] = []
		ret["not_found"] = []
		if subscriptionId == None or subscriptionId not in subscriptionIds:
			ret["not_found"].append(subscriptionId)
		else:
			udtInstances = i3x.ignition.getUdtInstances()
			subscription = subscriptionIds[subscriptionId]
			for elementId in subscription["elementIds"]:
				tagPath = i3x.utils.elementIdToPath(elementId)
				udtInstance = udtInstances[tagPath]
				i3x.tag.unsubscribe(elementId, tagPath, udtInstance, subscription)
			
			i3x.utils.deleteSubscription(subscriptionId)
			ret["unsubscribed"].append(subscriptionId)
	elif callType == "register":
		if subscriptionId == None or subscriptionId not in subscriptionIds:
			servletResponse.setStatus(HttpServletResponse.SC_NOT_FOUND)
			ret["detail"] = "Subscription not found"
		else:
			invalid = []
			udtInstances = i3x.ignition.getUdtInstances()
			elementIds = [objValue["elementId"] for objKey, objValue in udtInstances.iteritems()]
			for elementId in requestData["elementIds"]:
				if elementId not in elementIds:
					invalid.append(elementId)
			
			if len(invalid) > 0:
				servletResponse.setStatus(HttpServletResponse.SC_NOT_FOUND)
				ret["detail"] = "Invalid elementIds: %s" % ",".join(invalid)
			else:
				subscription = subscriptionIds[subscriptionId]
				registered = 0
				for elementId in requestData["elementIds"]:
					if elementId not in subscription["elementIds"]:
						registered += 1
						subscription["elementIds"].append(elementId)
						tagPath = i3x.utils.elementIdToPath(elementId)
						udtInstance = udtInstances[tagPath]
						i3x.tag.subscribe(elementId, tagPath, udtInstance, subscription)
			
				ret["message"] = "Registered %d objects to subscription." % registered
				ret["totalObjects"] = len(subscription["elementIds"])
	elif callType == "unregister":
		if subscriptionId == None or subscriptionId not in subscriptionIds:
			servletResponse.setStatus(HttpServletResponse.SC_NOT_FOUND)
			ret["detail"] = "Subscription not found"
		else:
			subscription = subscriptionIds[subscriptionId]
			unregistered = 0
			udtInstances = i3x.ignition.getUdtInstances()
			for elementId in requestData["elementIds"]:
				if elementId in subscription["elementIds"]:
					unregistered += 1
					tagPath = i3x.utils.elementIdToPath(elementId)
					udtInstance = udtInstances[tagPath]
					i3x.tag.unsubscribe(elementId, tagPath, udtInstance, subscription)
					
			subscription["elementIds"] = [elementId for elementId in subscription["elementIds"] if elementId not in requestData["elementIds"]]					
			ret["message"] = "Unregistered %d objects from subscription." % unregistered
	elif callType == "sync":
		if subscriptionId == None or subscriptionId not in subscriptionIds:
			servletResponse.setStatus(HttpServletResponse.SC_NOT_FOUND)
			ret["detail"] = "Subscription not found"
		else:
			subscription = subscriptionIds[subscriptionId]
			ret = list(subscription["queuedUpdates"])
			subscriptionIds[subscriptionId]["queuedUpdates"].clear()
			
	return {'json': system.util.jsonEncode(ret)}