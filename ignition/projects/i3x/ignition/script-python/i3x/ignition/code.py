IgnitionNamespaceUri = "https://inductiveautomation.com/UDT"
UaCoreUri = "http://opcfoundation.org/UA/"
DATE_FORMAT = "yyyy-MM-dd'T'HH:mm:ss.SSS'Z'"

def getTagProviders():
	tagProviders = []
	res = system.tag.browse("")
	for row in res.getResults():
		tagProviders.append(row["name"])
	return tagProviders

def getUdtDefs(tagProvider, elementId=None):
	query = {
	  "options": {
	    "includeUdtMembers": True,
	    "includeUdtDefinitions": True
	  },
	  "condition": {
	    "tagType": "UdtType",
	    "attributes": {
	      "values": [],
	      "requireAll": True
	    }
	  },
	  "returnProperties": [
	    "tooltip",
	    "documentation",
	    "parameters",
	    "tagType",
	    "quality"
	  ]
	}
	
	if elementId != None:
		query["condition"]["path"] = elementId
	
	return system.tag.query(tagProvider, query)
	
def getUdtInstancesForTagProvider(tagProvider):
	query = {
	  "options": {
	    "includeUdtMembers": True,
	    "includeUdtDefinitions": False
	  },
	  "condition": {
	    "tagType": "UdtInstance",
	    "attributes": {
	      "values": [],
	      "requireAll": True
	    }
	  },
	  "returnProperties": [
	    "tooltip",
	    "documentation",
	    "parameters",
	    "tagType",
	    "quality"
	  ]
	}
	
	return system.tag.query(tagProvider, query)

def addFolders(tagProvider, udtInstances, parentPath):
	if parentPath != "":
		parentPathParts = parentPath.split("/")
		for i in range(len(parentPathParts)):
			path = "/".join(parentPathParts[0:i+1])
			if path not in udtInstances:
				parentParentPath = "/".join(path.split("/")[:-1])
				if parentParentPath == "":
					parentParentPath = "[%s]" % tagProvider
				name = path.split("/")[-1]
				if "[%s]" % tagProvider in name:
					name = name.replace("[%s]" % tagProvider, "")
				udtInstances[path] = {"path":path, "elementId":i3x.utils.pathToElementId(path), "type":"folder", "tagProvider":tagProvider, "parentPath":parentParentPath, "parentUdt":None, "childrenUdts":[], "alarms":[], "namespaceUri":i3x.ignition.UaCoreUri, "typeId":"folder-type", "name":name, "parameters":{}, "alarmObj":{}}
	
def findUdtParent(udtInstances, udtInstancePath, udtInstance):
	parentPath = udtInstance["parentPath"]
	
	if parentPath != "":
		if udtInstances[parentPath]["type"] == "udt":
			udtInstance["parentUdt"] = parentPath
			if udtInstance["typeId"] == "ignition-alarm":
				udtInstances[parentPath]["alarms"].append(udtInstancePath)
			else:
				udtInstances[parentPath]["childrenUdts"].append(udtInstancePath)
		else:
			parentPath = udtInstances[parentPath]["parentPath"]
			found = False
			while parentPath != "":
				if udtInstances[parentPath]["type"] == "udt":
					udtInstance["parentUdt"] = parentPath
					if udtInstance["typeId"] == "ignition-alarm":
						udtInstances[parentPath]["alarms"].append(udtInstancePath)
					else:
						udtInstances[parentPath]["childrenUdts"].append(udtInstancePath)
						
					found = True
					break
				
				parentPath = udtInstances[parentPath]["parentPath"]
			
			if not found and udtInstance["parentPath"] != "":
				if udtInstance["typeId"] == "ignition-alarm":
					udtInstances[udtInstance["parentPath"]]["alarms"].append(udtInstancePath)
				else:
					udtInstances[udtInstance["parentPath"]]["childrenUdts"].append(udtInstancePath)

def getAlarmDetails(row, key):
	if key == "ackData":
		obj = row.getAckData()
	elif key == "clearedData":
		obj = row.getClearedData()
	else:
		obj = row.getActiveData()
	
	data = dict(obj.getRawValueMap()) if obj != None else {}
	newData = {}
	for k, v in data.items():
		if str(k) == "ackUser":
			val = v.toString()
		elif str(k) == "eventTime":
			val = system.date.format(v, DATE_FORMAT)
		else:
			val = v
		newData[str(k)] = val
	if "mode" in newData:
		del newData["mode"]
	return newData

def getAlarmObj(row):
	alarmObj = {}
	alarmObj["source"] = str(row.getSource())
	alarmObj["name"] = row.getName()
	alarmObj["eventId"] = str(row.eventId)
	alarmObj["displayPath"] = row.getDisplayPath().toString()
	alarmObj["count"] = row.getCount()
	alarmObj["label"] = row.getLabel()
	alarmObj["lastEventState"] = row.getLastEventState().name()
	alarmObj["notes"] = row.getNotes() 
	alarmObj["priority"] = row.getPriority().name()
	alarmObj["state"] = row.getState().name() 
	alarmObj["isActive"] = row.isActive
	alarmObj["isAcked"] = row.isAcked()
	alarmObj["isCleared"] = row.isCleared()
	alarmObj["isShelved"] = row.isShelved()
	alarmObj["ackData"] = getAlarmDetails(row, "ackData")
	alarmObj["clearedData"] = getAlarmDetails(row, "clearedData")
	alarmObj["activeData"] = getAlarmDetails(row, "activeData")
	
	eventTime = None
	if row.getState().name() == "ActiveUnacked":
		eventTime = alarmObj["activeData"]["eventTime"]
	elif row.getState().name() == "ActiveAcked":
		eventTime = alarmObj["ackData"]["eventTime"]
	elif row.getState().name() == "ClearUnacked":
		eventTime = alarmObj["clearedData"]["eventTime"]
	elif row.getState().name() == "ClearAcked":
		eventTime = alarmObj["ackData"]["eventTime"]
		
	alarmObj["eventTime"] = eventTime
		
	return alarmObj

def parseAlarms(res):
	alarms = {}
	for row in res:
		source = str(row.getSource())
		tagPath = i3x.utils.tagPathGen2ToGen1(str(row.getSource()))
		tagProvider = i3x.utils.getTagProviderFromPath(tagPath)
		name = row.getName()
		alarmObj = getAlarmObj(row)
		rowObj = {"path":source, "elementId":i3x.utils.pathToElementId(source), "type":"udt", "tagProvider":tagProvider, "parentPath":tagPath, "parentUdt":None, "childrenUdts":[], "alarms":[], "namespaceUri":i3x.ignition.IgnitionNamespaceUri, "typeId":"ignition-alarm", "name":name, "parameters":{}, "alarmObj":alarmObj}
		
		if source not in alarms:
			alarms[source] = rowObj
		elif system.date.isAfter(system.date.parse(alarmObj["eventTime"], DATE_FORMAT), system.date.parse(alarms[source]["alarmObj"]["eventTime"], DATE_FORMAT)):
			alarms[source] = rowObj
	return alarms

def getAlarms(tagProvider):
	res = system.alarm.queryStatus(provider=[tagProvider])
	alarms = parseAlarms(res)
	return alarms
	
def getAlarmFromSource(source):
	res = system.alarm.queryStatus(source=[source])
	alarms = parseAlarms(res)		
	return alarms[source]

def getUdtInstances():
	ret = {}
	
	tagProviders = getTagProviders()	
	for tagProvider in tagProviders:
		tpPath = "[%s]" % tagProvider
		tpTypes = "[%s]_types_/" % tagProvider
		udtInstances = {}
		udtInstances[tpPath] = {"path":tpPath, "elementId":i3x.utils.pathToElementId(tpPath), "type":"folder", "tagProvider":tagProvider, "parentPath":"", "parentUdt":None, "childrenUdts":[], "alarms":[], "namespaceUri":i3x.ignition.IgnitionNamespaceUri, "typeId":"ignition-tag-provider", "name":tagProvider, "parameters":{}, "alarmObj":{}}
		
		alarms = getAlarms(tagProvider)
		for alarmTagPath in alarms:
			alarm = alarms[alarmTagPath]
			udtInstances[alarm["path"]] = alarm
		
		res = i3x.ignition.getUdtInstancesForTagProvider(tagProvider)
		for row in res:
			udtPath = str(row["fullPath"])
			pathParts = udtPath.split("/")
			parentPath = "/".join(pathParts[:-1])
			if parentPath == "":
				parentPath = "[%s]" % tagProvider
			elementId = i3x.utils.pathToElementId(udtPath)
			dtTypeId = "%s%s" % (tpTypes, row["typeId"])
			
			parameters = {}
			if "parameters" in row and row["parameters"] != None and len(row["parameters"]) > 0:
				for param in row["parameters"]:
					paramValue = row["parameters"][param]
					parameters[param] = paramValue if isinstance(paramValue, basestring) else paramValue.value
			
			udtInstances[udtPath] = {"path":udtPath, "elementId":elementId, "type":"udt", "tagProvider":tagProvider, "parentPath":parentPath, "parentUdt":None, "childrenUdts":[], "alarms":[], "namespaceUri":i3x.utils.getNamespaceUriParam(row), "typeId":dtTypeId, "name":row["name"], "parameters":parameters, "alarmObj":{}}
		
		# We need to expand to all of the folders from the path
		for udtInstancePath in udtInstances:
			udtInstance = udtInstances[udtInstancePath]
			addFolders(tagProvider, udtInstances, udtInstance["parentPath"])
		
		# We need to find the UDT parent if exists
		for udtInstancePath in udtInstances:
			udtInstance = udtInstances[udtInstancePath]
			findUdtParent(udtInstances, udtInstancePath, udtInstance)
		
		# We need to update all of the relationships
		for udtInstancePath in udtInstances:
			udtInstance = udtInstances[udtInstancePath]
			
			if udtInstance["parentUdt"] != None:
				parentId = i3x.utils.pathToElementId(udtInstance["parentUdt"])
			else:
				parentId = "/" if udtInstance["parentPath"] == "" else i3x.utils.pathToElementId(udtInstance["parentPath"])
				
			relationships = {}
			
			if udtInstance["typeId"] == "ignition-alarm":
				relationships["AlarmOf"] = parentId
			else:
				relationships["HasParent"] = parentId
			
			if udtInstance["type"] == "folder" and len(udtInstance["childrenUdts"]) > 0:
				relationships["HasChildren"] = [i3x.utils.pathToElementId(path) for path in udtInstance["childrenUdts"]]
			elif udtInstance["type"] == "udt" and len(udtInstance["childrenUdts"]) > 0:
				relationships["HasComponent"] = [i3x.utils.pathToElementId(path) for path in udtInstance["childrenUdts"] if not (udtInstances[path]["typeId"] == "folder-type" and udtInstances[path]["parentUdt"] != None)]
				
			if len(udtInstance["alarms"]) > 0:
				relationships["HasAlarm"] = [i3x.utils.pathToElementId(path) for path in udtInstance["alarms"]]
			
			if udtInstance["type"] == "udt" and udtInstance["parentPath"] != "" and udtInstances[udtInstance["parentPath"]]["type"] == "udt":
				relationships["ComponentOf"] = i3x.utils.pathToElementId(udtInstance["parentPath"])
			
			udtInstance["parentId"] = parentId
			udtInstance["relationships"] = relationships
			udtInstance["isComposition"] = udtInstance["type"] == "udt" and len(udtInstance["childrenUdts"]) > 0
		
		ret.update(udtInstances)
					
	return ret

# =============================================================================
# PATCHED: parseTags - uses browse results instead of getConfiguration
# =============================================================================
# Fixed to use system.tag.browse() to walk UDT definitions one level at a
# time, avoiding the StackOverflowError caused by
# system.tag.getConfiguration(path, True) in Ignition 8.3.x with nested UDTs.
# =============================================================================
def parseTags(path, tags, visited=None):
	if visited is None:
		visited = set()
	
	tagProvider = path.split("/")[0]
	DATA_TYPE_MAPPINGS = {"Int1":"integer", "Int2":"integer", "Int4":"integer", "Int8":"integer", "Float4":"number", "Float8":"number", "Boolean":"boolean", "String":"string", "DateTime":"string", "Int1Array":"array", "Int2Array":"array", "Int4Array":"array", "Int8Array":"array", "Float4Array":"array", "Float8Array":"array", "StringArray":"array", "DateTimeArray":"array", "ByteArray":"array", "DataSet":"object", "Document":"object"}
	
	types = []
	tagProps = {}
	
	for row in tags:
		name = row["name"]
		tagType = str(row["tagType"])
		newPath = "%s/%s" % (path, name)
		
		if tagType == "AtomicTag":
			tag = {"type":DATA_TYPE_MAPPINGS.get(row.get("dataType", "Int4"), "string")}
			
			if "tooltip" in row and row["tooltip"] != None and row["tooltip"] != "":
				tag["description"] = str(row["tooltip"])
			
			if "value" in row and row["value"] != None:
				# PATCHED: Unwrap QualifiedValue objects from browse results
				rawValue = row["value"]
				if hasattr(rawValue, 'getValue'):
					rawValue = rawValue.getValue()
				if row.get("dataType", "Int4") == "DateTime":
					try:
						tag["default"] = system.date.format(rawValue, DATE_FORMAT)
					except:
						tag["default"] = str(rawValue)
				else:
					# Convert Java types to plain Python types for JSON serialization
					if hasattr(rawValue, 'toString'):
						try:
							# Try to keep numeric types as-is
							if isinstance(rawValue, (int, long, float, bool)):
								tag["default"] = rawValue
							else:
								tag["default"] = rawValue.toString()
						except:
							tag["default"] = str(rawValue)
					else:
						tag["default"] = rawValue
				
			if "engUnit" in row and row["engUnit"] != None:
				engUnit = row["engUnit"]
				tag["engUnit"] = engUnit.toString() if hasattr(engUnit, 'toString') else str(engUnit)
				
			if "engLow" in row and row["engLow"] != None:
				engLow = row["engLow"]
				tag["engLow"] = engLow.getValue() if hasattr(engLow, 'getValue') else engLow
				
			if "engHigh" in row and row["engHigh"] != None:
				engHigh = row["engHigh"]
				tag["engHigh"] = engHigh.getValue() if hasattr(engHigh, 'getValue') else engHigh
			
			tagProps[name] = tag
			
		elif tagType == "Folder":
			subTags = system.tag.browse(newPath).getResults()
			(subTypes, subTagProps) = parseTags(newPath, subTags, visited)
			tag = {
				"type":"object",
				"properties":subTagProps
			}
			
			if "tooltip" in row and row["tooltip"] != None and row["tooltip"] != "":
				tag["description"] = row["tooltip"]
			
			tagProps[name] = tag
			
			for subType in subTypes:
				if subType not in types:
					types.append(subType)
					
		elif tagType == "UdtInstance":
			dtNamespaceUri = i3x.utils.getNamespaceUriParam(row)
			typeId = str(row.get("typeId", ""))
			dtPath = i3x.utils.pathToElementId("%s/%s" % (tagProvider, typeId))
			types.append("%s:%s" % (dtNamespaceUri, dtPath))
			
			tag = {"$ref":"#/types/%s" % (dtPath)}
			
			if "tooltip" in row and row["tooltip"] != None and row["tooltip"] != "":
				tag["description"] = row["tooltip"]
			
			tagProps["!%s" % name] = tag
			
	return types, tagProps

# =============================================================================
# PATCHED: buildSchema - uses browse instead of getConfiguration(path, True)
# =============================================================================
# Fixed to use system.tag.browse() to get the top-level members of a UDT
# definition, then passes them to the patched parseTags which continues
# browsing one level at a time for any nested Folders.
# =============================================================================
def buildSchema(row, tagProvider, dtNamespaceUri):
	tpTypes = "[%s]_types_/" % tagProvider
	fullPath = str(row["fullPath"])
	
	# PATCHED: browse one level instead of recursive getConfiguration
	tags = system.tag.browse(fullPath).getResults()
	(types, tagProps) = parseTags(fullPath, tags)
	
	schema = {
		"type":"object",
		"properties":tagProps
	}
	
	if "tooltip" in row and row["tooltip"] != None and row["tooltip"] != "":
		schema["description"] = row["tooltip"]
		
	query = {
	  "options": {
	    "includeUdtMembers": True,
	    "includeUdtDefinitions": True
	  },
	  "condition": {
	    "hierarchy": {
	      "typeId": fullPath,
	      "relationship": "SubType"
	    },
	    "tagType": "UdtType",
	    "attributes": {
	      "values": [],
	      "requireAll": True
	    }
	  }
	}
	
	relatedSchema = {}
	res = system.tag.query(tagProvider, query)
	if len(res):
		if "!related" not in relatedSchema:
			relatedSchema["!related"] = {}
		
		subTypes = []
		for subType in res:
			subTypes.append("%s:%s" % (dtNamespaceUri, i3x.utils.pathToElementId(str(subType["fullPath"]))))
			
		relatedSchema["!related"]["InheritedBy"] = subTypes
		
	if "typeId" in row and row["typeId"] != None and row["typeId"] != "":
		if "!related" not in relatedSchema:
			relatedSchema["!related"] = {}
			
		relatedSchema["!related"]["InheritsFrom"] = "%s:%s" % (dtNamespaceUri, i3x.utils.pathToElementId("%s%s" % (tpTypes, row["typeId"])))
	
	if len(types):
		if "!related" not in relatedSchema:
			relatedSchema["!related"] = {}
			
		relatedSchema["!related"]["HasComponent"] = types
		
	if "!related" in relatedSchema and "HasComponent" in relatedSchema["!related"]:
		schema["!related"] = {"relationshipType":"HasComponent", "types":relatedSchema["!related"]["HasComponent"]}
		
	if "parameters" in row and row["parameters"] != None and len(row["parameters"]) > 0:
		schema["parameters"] = {}
		for param in row["parameters"]:
			paramValue = row["parameters"][param]
			schema["parameters"][param] = paramValue if isinstance(paramValue, basestring) else paramValue.value
	
	return schema
	
def getTagValue(udtInstance, value):
	if value != None:
		children = i3x.utils.getChildrenObjectNames(udtInstance, "HasComponent")
		objValue = value.value.toDict()
		childrenValues = i3x.utils.removeChildren(objValue, children)
		quality = value.quality.toString().upper()
		timestamp = system.date.format(value.timestamp, i3x.ignition.DATE_FORMAT)
		return {"value":{"value":objValue, "quality":quality, "timestamp":timestamp}, "childrenValues":childrenValues}
	
	return None