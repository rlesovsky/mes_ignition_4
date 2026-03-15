VERSION = "1.0.5"

def showErrorMessage(title, message):
	params = {
		"color":"#AC0000",
		"icon": "error_outline",
		"title": title,
		"message": message
	}
	system.perspective.openPopup("message", "CESMII/Message", title="Error", params=params, showCloseIcon=False, draggable=True, resizable=True, modal=True, overlayDismiss=True)
	
def showInfoMessage(title, message):
	params = {
		"color":"",
		"icon": "message",
		"title": title,
		"message": message
	}
	system.perspective.openPopup("message", "CESMII/Message", title="Message", params=params, showCloseIcon=False, draggable=True, resizable=True, modal=True, overlayDismiss=True)

def importPopup(name, tags):
	params = {
		"name": name,
		"tags": system.util.jsonEncode(tags)
	}
	system.perspective.openPopup("profile-import", "CESMII/Profile Import", title="Import", params=params, showCloseIcon=False, draggable=True, resizable=True, modal=False, overlayDismiss=False)

def downloadAllRequiredModels(session, visitedModels, requiredModels):
	models = {}
	
	for model in requiredModels:
		if model["namespaceUri"] not in visitedModels:
			modelRes = CESMII.UALibraryRESTService.download(session, model["availableModel"]["identifier"])
			models[model["namespaceUri"]] = {"version":model["availableModel"]["version"], "identifier": model["availableModel"]["identifier"], "xml": CESMII.UALibraryRESTService.getXML(modelRes)}
			visitedModels.append(model["namespaceUri"])
			models.update(downloadAllRequiredModels(session, visitedModels, modelRes["nodeset"]["requiredModels"]))
	
	return models

def findAllRequiredModels(ModelIdentifier, Model, MainUANodeSet, session):
	import xml.etree.ElementTree as ET
	
	res = CESMII.UALibraryRESTService.download(session, ModelIdentifier)
	
	namespaces = {Model.ModelUri:MainUANodeSet.NamespaceUris.indexOf(Model.ModelUri)}
	requiredModels = downloadAllRequiredModels(session, [ModelIdentifier], res["nodeset"]["requiredModels"])
	for namespaceUri in requiredModels:		
		if namespaceUri == "http://opcfoundation.org/UA/":
			actualIndex = 0
		else:
			actualIndex = MainUANodeSet.NamespaceUris.indexOfAppend(namespaceUri)
		namespaces[namespaceUri] = actualIndex
		
	models = {}
	models[MainUANodeSet.NamespaceUris.indexOf(Model.ModelUri)] = {"NamespaceUri":Model.ModelUri, "ModelTagName":getModelTagName(Model.ModelUri), "Version":Model.Version, "Identifier":ModelIdentifier, "UANodeSet":MainUANodeSet, "IsLocal":True, "Tags":[]}
	
	for namespaceUri in requiredModels:
		modelXML = requiredModels[namespaceUri]["xml"]
		if namespaceUri == "http://opcfoundation.org/UA/":
			actualIndex = 0
		else:
			actualIndex = MainUANodeSet.NamespaceUris.indexOf(namespaceUri)
		UANodeSet = CESMII.UANodeSet.UANodeSet(ET.fromstring(modelXML), namespaces)
		models[actualIndex] = {"NamespaceUri":namespaceUri, "ModelTagName":getModelTagName(namespaceUri), "Version":requiredModels[namespaceUri]["version"], "Identifier":requiredModels[namespaceUri]["identifier"], "UANodeSet":UANodeSet, "IsLocal":False, "Tags":[]}
	
	return models

def getIdentifierForModel(Model, Namespaces, session):
	if Model.ModelUri not in Namespaces:
		raise Exception("Model %s not found" % Model.ModelUri)
		
	identifers = Namespaces[Model.ModelUri]
	if len(identifers) == 1:
		res = CESMII.UALibraryRESTService.download(session, identifers[0])
		return (res["title"], identifers[0])
	else:
		# We have found multiple identifiers. We need to download each one to check the version
		for identifier in identifers:
			res = CESMII.UALibraryRESTService.download(session, identifier)
			if res["nodeset"]["version"] == Model.Version:
				return (res["title"], identifier)
	
	raise Exception("Model %s version %s not found" % (Model.ModelUri, Model.Version))

def findAllObjectTypes(UANode, RequiredModels, OnlyParents=True):
	ObjectTypes = []
	
	if not OnlyParents:
		ObjectTypes.append({"Object":UANode, "IsLocal":RequiredModels[UANode.NodeId.Index]["IsLocal"], "HasProps":UANode.hasPropertiesOrComponents()})
	
	ObjectNodeId = UANode.getSubTypeNodeId()
	
	if ObjectNodeId != None and ObjectNodeId != UANode.NodeId:
		Object = RequiredModels[ObjectNodeId.Index]["UANodeSet"].UANodes[ObjectNodeId.Value]
		HasProps = Object.hasPropertiesOrComponents()
		ObjectTypes.append({"Object":Object, "IsLocal":RequiredModels[ObjectNodeId.Index]["IsLocal"], "HasProps":HasProps})		
		ObjectTypes.extend(findAllObjectTypes(Object, RequiredModels))
		
	HasPropsLastIndex = None
	for i in range(len(ObjectTypes)):
		if ObjectTypes[i]["HasProps"]:
			HasPropsLastIndex = i
		
	if HasPropsLastIndex != None:
		for i in range(HasPropsLastIndex):
			ObjectTypes[i]["HasProps"] = True
				
	return ObjectTypes
	
def addDependentObjects(ObjectTypes, DependentObjects):
	for i in range(len(ObjectTypes)):
		ObjectType = ObjectTypes[i]
		Object = ObjectType["Object"]
		if ObjectType["HasProps"]:
			if not ObjectType["IsLocal"] and Object.NodeId.getNamespaceNodeId() not in DependentObjects:
				DependentObjects[Object.NodeId.getNamespaceNodeId()] = Object
	
def isComplex(ObjectTypes):
	Found = False
	for i in range(len(ObjectTypes)):
		ObjectType = ObjectTypes[i]
		Object = ObjectType["Object"]
		if ObjectType["HasProps"]:
			Found = True
			break
	
	if Found and not ObjectTypes[0]["Object"].IsEnum:
		return ObjectTypes[0]["Object"]
					
	return None

def buildEnumExpression(TagName, DataType):
	expression = "switch({[.]%s}," % TagName
	
	intValues = []
	strValues = []	
	for value in DataType.EnumValues:
		intValues.append(str(value))
		strValues.append("\"%s\"" % DataType.EnumValues[value])
		
	expression += "%s,%s,\"Unknown\")" % (",".join(intValues), ",".join(strValues))	
	return expression

# TODO: Access permissions, bit mask, write mask, role permissions
# TODO: UAMethod - call OPC-UA method in script function? system.opcua.callMethod(connectionName, objectId, methodId, inputs)
# TODO: UAVariable - handle when array of complex objects, the list will give you each of the names. Possibly handle default value?
def addTag(UANode, Context, ParentPath, IsList):
	RequiredModels = Context["RequiredModels"]
	DependentObjects = Context["DependentObjects"]
	
	Documentation = ""
	if isinstance(UANode, (CESMII.UANodeSet.DataTypeField)):
		TagName = UANode.Name
		DataTypeNodeId = UANode.DataType
		ValueRank = UANode.ValueRank.Value
		Tooltip = ",".join([CESMII.TypeUtils.coalesce(obj.Value, "") for obj in UANode.Description])
		IsFolder = False
	else:
		if UANode.typeDefIsParent():
			return []
	
		if UANode.ReleaseStatus != CESMII.BaseTypes.ReleaseStatus.Released:
			return []
		
		TagName = UANode.BrowseName.Value
		
		if isinstance(UANode, (CESMII.UANodeSet.UAVariable)):
			DataTypeNodeId = UANode.DataType
			TypeDefNodeId = UANode.getTypeDefinition()
			VariableDataType = RequiredModels[TypeDefNodeId.Index]["UANodeSet"].UANodes[TypeDefNodeId.Value]
			if VariableDataType.DataType == DataTypeNodeId:
				DataTypeNodeId = TypeDefNodeId
		else:
			DataTypeNodeId = UANode.getTypeDefinition()
		
		ValueRank = -1
		if isinstance(UANode, (CESMII.UANodeSet.UAVariable)):
			ValueRank = UANode.ValueRank.Value
		Documentation = CESMII.TypeUtils.coalesce(UANode.Documentation, "")
		Tooltip = ",".join([CESMII.TypeUtils.coalesce(obj.Value, "") for obj in UANode.Description])
		IsFolder = UANode.IsFolder
		
	TagName = sanitizeName(TagName)
	
	if IsFolder:
		ChildTags = [
			{
				"name": TagName,
				"tagType": "Folder",
				"tags": addTags(UANode, Context, "%s/%s" % (ParentPath, TagName) if ParentPath != "" else TagName, "List" in TagName or UANode.IsOptional)
			}
		]
		
		if len(ChildTags[0]["tags"]) == 0:
			ChildTags = []
	elif isinstance(UANode, (CESMII.UANodeSet.UAMethod)):
		ChildTags = []
	else:
		DataType = RequiredModels[DataTypeNodeId.Index]["UANodeSet"].UANodes[DataTypeNodeId.Value]	
		DataTypes = findAllObjectTypes(DataType, RequiredModels, False)
		addDependentObjects(DataTypes, DependentObjects)
		ComplexDataType = isComplex(DataTypes)		
		TagType = "UdtInstance" if ComplexDataType != None else "AtomicTag"
		ComplexModel = None
		ComplexModelTagName = None
		
		if ComplexDataType != None:
			ComplexModel = RequiredModels[ComplexDataType.NodeId.Index]
			ComplexModelTagName = ComplexModel["ModelTagName"]
		
		ChildTags = []
		Tag = {
			"name": TagName,
			"tagType": TagType,
			"documentation": Documentation,
			"tooltip": Tooltip,
			"readOnly": False
		}
		
		if TagType == "UdtInstance":
			if ValueRank == 1 or (IsList and UANode.IsOptional):
				# We have an array of complex objects, need to ask the user
				if isinstance(UANode, (CESMII.UANodeSet.UAVariable)) and len(UANode.ExtensionObject) > 0:
					Tag.update({"list":{"count":len(UANode.ExtensionObject), "names":["%s%d" % (TagName, i) for i in range(len(UANode.ExtensionObject))], "complete":False}})
				else:				
					Tag.update({"list":{"count":1, "names":[TagName], "complete":False}})
						
			Tag.update({"typeId": "%s/%s" % (ComplexModelTagName, sanitizeName(ComplexDataType.BrowseName.Value))})
			Tag.update({
				"parameters": {
					"UAPrefix": {
						"dataType": "String",
						"value": {
							"bindType": "parameter",
							"binding": "{UAPrefix}/%s%s" % ("%s/" % ParentPath if ParentPath != "" else "", TagName)
						}
					},
					"UAServer": {
						"dataType": "String",
						"value": {
							"bindType": "parameter",
							"binding": "{UAServer}"
						}
					}
				}
			})
			ChildTags.append(Tag)
		else:
			Tag.update({
				"opcItemPath": {
					"bindType": "parameter",
					"binding": "{UAPrefix}/%s%s" % ("%s/" % ParentPath if ParentPath != "" else "", TagName)
				},
				"valueSource": "opc",
				"opcServer": {
					"bindType": "parameter",
					"binding": "{UAServer}"
				},
				"dataType": CESMII.BaseTypes.mapDataType(DataType, ValueRank)
			})
			
			ChildTags.append(Tag)
			if DataType.IsEnum:
				Tag["name"] += "Enum"
				ChildTags.append({
					"name": TagName,
					"tagType": "AtomicTag",
					"valueSource": "expr",
					"documentation": Documentation,
					"tooltip": Tooltip,
					"dataType": "String",
					"expression": buildEnumExpression(Tag["name"], DataType)
				})
			
	return ChildTags

def addTags(UANode, Context, ParentPath="", IsList=False):
	RequiredModels = Context["RequiredModels"]

	ChildTags = []
	
	if isinstance(UANode, CESMII.UANodeSet.UADataType):
		for field in UANode.Definition.Field:
			ChildTags.extend(addTag(field, Context, ParentPath, IsList))
	else:
		if UANode.hasPropertiesOrComponents():
			for NodeId in UANode.getPropertiesAndComponents():
				ChildUANode = RequiredModels[NodeId.Index]["UANodeSet"].UANodes[NodeId.Value]					
				ChildTags.extend(addTag(ChildUANode, Context, ParentPath, IsList))
				
	return ChildTags

def checkTypeConflicts(UDT, Parent, Context):	
	if Parent != None:
		ParentTags = addTags(Parent, Context)
		HasConflict = False
		
		MissingTags = []
		for ParentTag in ParentTags:
			Found = False
			for UDTTag in UDT["tags"]:
				if ParentTag["name"] == UDTTag["name"]:
					Found = True
					
					if ParentTag.get("typeId", "") != UDTTag.get("typeId", ""):
						HasConflict = True
						
					break
					
			if not Found:
				MissingTags.append(ParentTag)
		
		if HasConflict:
			UDT["typeId"] = ""
			UDT["tags"].extend(MissingTags)

def addType(UANode, Context):
	if UANode.ReleaseStatus != CESMII.BaseTypes.ReleaseStatus.Released:
		return
		
	RequiredModels = Context["RequiredModels"]
	DependentObjects = Context["DependentObjects"]
	ObjectsAdded = Context["ObjectsAdded"]
	Model = RequiredModels[UANode.NodeId.Index]
	
	if isinstance(UANode, (CESMII.UANodeSet.UAObjectType, CESMII.UANodeSet.UADataType, CESMII.UANodeSet.UAVariableType, CESMII.UANodeSet.UAObject)):
		if isinstance(UANode, (CESMII.UANodeSet.UAObject)) and (UANode.IsFolder or not UANode.hasPropertiesOrComponents()):
			return
		
		if not UANode.IsEnum and UANode.NodeId.getNamespaceNodeId() not in ObjectsAdded:
			ParentTypes = findAllObjectTypes(UANode, RequiredModels)
			addDependentObjects(ParentTypes, DependentObjects)
			Parent = isComplex(ParentTypes)
			ParentModel = None
			ParentModelTagName = None
			
			if Parent != None:
				ParentModel = RequiredModels[Parent.NodeId.Index]
				ParentModelTagName = ParentModel["ModelTagName"]
						
			Documentation = CESMII.TypeUtils.coalesce(UANode.Documentation, "")
			Tooltip = ",".join([CESMII.TypeUtils.coalesce(obj.Value, "") for obj in UANode.Description])
			
			UDT = {
				"name": sanitizeName(UANode.BrowseName.Value),
				"typeId": "" if Parent == None else "%s/%s" % (ParentModelTagName, sanitizeName(Parent.BrowseName.Value)),
				"tagType": "UdtType",
				"documentation": Documentation,
				"tooltip": Tooltip,
				"parameters": {
					"UAPrefix": {
			    		"dataType": "String"
			    	},
					"UAServer": {
						"dataType": "String"
					}
				},
				"tags": addTags(UANode, Context, "", "List" in UANode.BrowseName.Value)
			}
			
			# If a UDT inherits from another UDT, UDT instances inside must have the same type as the parent. If there is a conflict, we must not inherit.
			checkTypeConflicts(UDT, Parent, Context)
			
			Model["Tags"].append(UDT)
			ObjectsAdded.append(UANode.NodeId.getNamespaceNodeId())

def sanitizeName(name):
	import re
	
	if name == None or len(name) == 0:
		return "Unknown"
	
	if len(name) > 255:
		name = name[:255]
		
	newName = ""		
	for c in name:
		if c.isdigit() or c.isalpha() or c == "_" or c == " " or c == "(" or c == ")" or c == "'" or c == "-" or c == ":":
			newName += c
		else:
			newName += "_"
			
	newName = newName.strip("_")
		
	return newName
	
def getModelTagName(model):
	if model.endswith("/"):
		model = model[:-1]
	
	parts = model.split("/")
	return "/".join([sanitizeName(part) for part in parts[3:]])

def convert_UANodeSet_to_Ignition(nodesetXML, session):
	import traceback
	import re
	import xml.etree.ElementTree as ET
	
	log = system.util.getLogger("SMProfile")
	
	if nodesetXML != None:
		try:
			offline = session.custom.settings.noCredentials
			Namespaces = {} if offline else CESMII.UALibraryRESTService.namespaces(session)
			UANodeSet = None
			RequiredModels = {}
			ModelName = None
			
			if isinstance(nodesetXML, list):
				# We found a list of nodeset XML files				
				UANodeSets = {}
				for xmlFile in nodesetXML:
					xmlFile = xmlFile["xml"].strip()
					if xmlFile.find("<?xml") > 0:
						xmlFile = xmlFile[xmlFile.find("<?xml"):]
					root = ET.fromstring(xmlFile)
					
					tmpUANodeSet = CESMII.UANodeSet.UANodeSet(root)
					for Model in tmpUANodeSet.Models.Model:
						UANodeSets[Model.ModelUri] = {"UANodeSet":tmpUANodeSet, "xmlNode":root}
				
				# Check for required models		
				for tmpModelUri in UANodeSets:
					tmpUANodeSet = UANodeSets[tmpModelUri]["UANodeSet"]
					for Model in tmpUANodeSet.Models.Model:
						if Model.ModelUri == tmpModelUri:
							for RequiredModel in Model.RequiredModel:
								if RequiredModel.ModelUri not in UANodeSets:
									raise Exception("Required model '%s' not found in uploaded files" % (RequiredModel.ModelUri))
							break
							
				# Find root NodeSet
				for tmpModelUri1 in UANodeSets:
					tmpUANodeSet1 = UANodeSets[tmpModelUri1]["UANodeSet"]
					found = False
					
					for tmpModelUri2 in UANodeSets:
						tmpUANodeSet2 = UANodeSets[tmpModelUri2]["UANodeSet"]
						
						for Model in tmpUANodeSet2.Models.Model:
							for RequiredModel in Model.RequiredModel:
								if RequiredModel.ModelUri == tmpModelUri1:
									found = True
									break
							
							if found:
								break
						
						if found:
							break
							
					if not found:
						UANodeSet = tmpUANodeSet1
						ModelName = tmpModelUri1
			
				if UANodeSet == None:
					raise Exception("No NodeSet found in uploaded files")
				
				def addRequiredModels(MainUANodeSet, Model, UANodeSets, namespaces, RequiredModels, IsLocal):
					if Model.ModelUri == "http://opcfoundation.org/UA/":
						actualIndex = 0
					else:
						actualIndex = MainUANodeSet.NamespaceUris.indexOf(Model.ModelUri)
					
					UANodeSet = CESMII.UANodeSet.UANodeSet(UANodeSets[Model.ModelUri]["xmlNode"], namespaces)
					RequiredModels[actualIndex] = {"NamespaceUri":Model.ModelUri, "ModelTagName":getModelTagName(Model.ModelUri), "Version":Model.Version, "Identifier":None, "UANodeSet":UANodeSet, "IsLocal":IsLocal, "Tags":[]}
					for RequiredModel in Model.RequiredModel:
						RequiredUANodeSet = UANodeSets[RequiredModel.ModelUri]["UANodeSet"]
						for SubModel in RequiredUANodeSet.Models.Model:
							addRequiredModels(MainUANodeSet, SubModel, UANodeSets, namespaces, RequiredModels, False)
				
				# Add required models
				namespaces = {}
				for Model in UANodeSet.Models.Model:
					if Model.ModelUri == "http://opcfoundation.org/UA/":
						actualIndex = 0
					else:
						actualIndex = UANodeSet.NamespaceUris.indexOf(Model.ModelUri)
					namespaces[Model.ModelUri] = actualIndex
					
					for RequiredModel in Model.RequiredModel:
						if RequiredModel.ModelUri == "http://opcfoundation.org/UA/":
							actualIndex = 0
						else:
							actualIndex = UANodeSet.NamespaceUris.indexOf(RequiredModel.ModelUri)
						namespaces[RequiredModel.ModelUri] = actualIndex
				
				for Model in UANodeSet.Models.Model:
					addRequiredModels(UANodeSet, Model, UANodeSets, namespaces, RequiredModels, True)
			else:
				nodesetXML = nodesetXML.strip()
				if nodesetXML.find("<?xml") > 0:
					nodesetXML = nodesetXML[nodesetXML.find("<?xml"):]
				root = ET.fromstring(nodesetXML)
				
				UANodeSet = CESMII.UANodeSet.UANodeSet(root)
				for Model in UANodeSet.Models.Model:			
					(ModelTitle, ModelIdentifier) = getIdentifierForModel(Model, Namespaces, session)
					RequiredModels.update(findAllRequiredModels(ModelIdentifier, Model, UANodeSet, session))
					
					if ModelName == None:
						ModelName = ModelTitle
			
			Context = {
				"ObjectsAdded": [],
				"DependentObjects": {},
				"RequiredModels": RequiredModels
			}
				
			# Now let's build out each UDT definition
			for UANodeId in UANodeSet.UANodes:
				UANode = UANodeSet.UANodes[UANodeId]
				addType(UANode, Context)
				
			# Now let's build out all dependent types (inheritance and composition)
			ObjectsToAdd = len(Context["DependentObjects"]) > 0
			while ObjectsToAdd:
				DependentObjects = Context["DependentObjects"]
				Context["DependentObjects"] = {}
				for UANodeId in DependentObjects:
					UANode = DependentObjects[UANodeId]
					addType(UANode, Context)
				ObjectsToAdd = len(Context["DependentObjects"]) > 0
				
			UDTs = {
				"tags": []
			}
			for ModelIndex in range(len(RequiredModels)):
				Model = RequiredModels[ModelIndex]
				ModelTagName = Model["ModelTagName"]
				Parts = ModelTagName.split("/")
				
				if len(Model["Tags"]) > 0:
					UDTRoot = UDTs
					for Part in Parts:
						Found = False
						for Tag in UDTRoot["tags"]:
							if Tag["name"] == Part:
								UDTRoot = Tag
								Found = True
								break
						
						if not Found:
							Tag = {
								"name": Part,
								"tags": [],
								"tagType": "Folder"
							}
							UDTRoot["tags"].append(Tag)
							UDTRoot = Tag
							
					UDTRoot["tags"].extend(Model["Tags"])
			
			return (True, None, ModelName, UDTs)
		except:
			log.error("Failed parsing XML: %s" % traceback.format_exc())
			return (False, "Failed parsing XML. See logs for details.", None, None)
	else:
		return (False, "File '%s' doesn't exist" % filePath)

def popListFromTags(parent):
	if "tags" in parent:
		for tag in parent["tags"]:
			if "list" in tag:
				tag.pop("list")
			else:
				popListFromTags(tag)

def importUDTs(name, provider, tags):
	import traceback
	try:
		popListFromTags(tags)
		json = system.util.jsonEncode(tags)
		filePath = system.file.getTempFile("json")
		system.file.writeFile(filePath, json)
		system.tag.importTags(filePath, "[%s]" % provider, "i")
		showInfoMessage("Import Success", "Import successful for profile %s" % name)
		system.perspective.closePopup("profile-import")
	except:
		showErrorMessage("Import Error", "Error importing UDTs: %s" % traceback.format_exc())

def exportUDTs(name, tags):
	import traceback
	try:
		popListFromTags(tags)
		json = system.util.jsonEncode(tags)
		system.perspective.download("%s.json" % name, json, "application/json")
	except:
		showErrorMessage("Download Error", "Error downloading UDTs: %s" % traceback.format_exc())