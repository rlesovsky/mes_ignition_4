NAMESPACE = "{http://opcfoundation.org/UA/2011/03/UANodeSet.xsd}"

def BuildNS(key):
	return "%s%s" % (NAMESPACE, key)

class UriTable:
	def __init__(self, xmlNode):
		self.UriList = []
		
		if xmlNode != None:
			for uriObj in xmlNode.findall(BuildNS("Uri")):
				self.UriList.append(uriObj.text)
				
	def indexOf(self, Uri):
		if Uri in self.UriList:
			return self.UriList.index(Uri) + 1
		
		return len(self.UriList) + 1
		
	def indexOfAppend(self, Uri):
		if Uri not in self.UriList:
			self.UriList.append(Uri)
		return self.indexOf(Uri)

class RolePermission(CESMII.BaseTypes.NodeId):
	def __init__(self, xmlNode, uaNodeSet):
		CESMII.BaseTypes.NodeId.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.Permissions = 0
		
		if xmlNode != None:
			self.Permissions = CESMII.TypeUtils.toInt(xmlNode.attrib.get("Permissions", "0"))	

class ListOfRolePermissions:
	def __init__(self, xmlNode, uaNodeSet):
		self.RolePermissionList = []
		
		if xmlNode != None:
			for permission in xmlNode.findall(BuildNS("RolePermission")):
				self.RolePermissionList.append(RolePermission(permission, uaNodeSet))
				
	def fixNodeIds(self, Aliases):
		for rp in self.RolePermissionList:
			rp.fix(Aliases)

class ModelTableEntry:
	def __init__(self, xmlNode, uaNodeSet):
		self.RolePermissions = None
		self.RequiredModel = []
		self.ModelUri = None
		self.XmlSchemaUri = None
		self.Version = None
		self.PublicationDate = None
		self.ModelVersion = None
		self.AccessRestrictions = CESMII.BaseTypes.AccessRestriction(0)
		
		if xmlNode != None:
			self.RolePermissions = ListOfRolePermissions(xmlNode.find(BuildNS("RolePermissions")), uaNodeSet)
			for requiredModel in xmlNode.findall(BuildNS("RequiredModel")):
				self.RequiredModel.append(ModelTableEntry(requiredModel, uaNodeSet))
			
			self.ModelUri = xmlNode.attrib.get("ModelUri", None)
			self.XmlSchemaUri = xmlNode.attrib.get("XmlSchemaUri", None)
			self.Version = xmlNode.attrib.get("Version", None)
			self.PublicationDate = CESMII.TypeUtils.toDate(xmlNode.attrib.get("PublicationDate", None))
			self.ModelVersion = CESMII.BaseTypes.ModelVersion(xmlNode)
			self.AccessRestrictions = CESMII.BaseTypes.AccessRestriction(xmlNode=xmlNode, defaultValue=0)

class ModelTable:
	def __init__(self, xmlNode, uaNodeSet):
		self.Model = []
		
		if xmlNode != None:
			for model in xmlNode.findall(BuildNS("Model")):
				self.Model.append(ModelTableEntry(model, uaNodeSet))
				
class NodeIdAlias(CESMII.BaseTypes.NodeId):
	def __init__(self, xmlNode, uaNodeSet):
		CESMII.BaseTypes.NodeId.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.Alias = None
		
		if xmlNode != None:
			self.Alias = xmlNode.attrib.get("Alias", None)

class UANodeSet:
	def __init__(self, xmlNode, parentNamespaceUris=None):
		self.ParentNamespaceUris = parentNamespaceUris
		self.NamespaceUris = None
		self.Models = None
		self.Aliases = {}
		self.UANodes = {}
		self.LastModified = None
			
		if xmlNode != None:
			self.LastModified = CESMII.TypeUtils.toDate(xmlNode.attrib.get("LastModified", None))
			self.NamespaceUris = UriTable(xmlNode.find(BuildNS("NamespaceUris")))
			self.Models = ModelTable(xmlNode.find(BuildNS("Models")), self)
			
			# Find all of the Aliases
			aliases = xmlNode.find(BuildNS("Aliases"))
			if aliases != None:
				for alias in aliases.findall(BuildNS("Alias")):
					aliasObj = NodeIdAlias(alias, self)
					self.Aliases[aliasObj.Alias] = aliasObj
			
			# Find all of the UAObject nodes
			for node in xmlNode.findall(BuildNS("UAObject")):
				nodeObj = UAObject(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
				
			# Find all of the UAVariable nodes
			for node in xmlNode.findall(BuildNS("UAVariable")):
				nodeObj = UAVariable(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
				
			# Find all of the UAMethod nodes
			for node in xmlNode.findall(BuildNS("UAMethod")):
				nodeObj = UAMethod(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
								
			# Find all of the UAView nodes
			for node in xmlNode.findall(BuildNS("UAView")):
				nodeObj = UAView(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
				
			# Find all of the UAObjectType nodes
			for node in xmlNode.findall(BuildNS("UAObjectType")):
				nodeObj = UAObjectType(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
				
			# Find all of the UAVariableType nodes
			for node in xmlNode.findall(BuildNS("UAVariableType")):
				nodeObj = UAVariableType(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
				
			# Find all of the UADataType nodes
			for node in xmlNode.findall(BuildNS("UADataType")):
				nodeObj = UADataType(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
							
			# Find all of the UAReferenceType nodes
			for node in xmlNode.findall(BuildNS("UAReferenceType")):
				nodeObj = UAReferenceType(node, self)
				self.UANodes[nodeObj.NodeId.Value] = nodeObj
				self.Aliases[nodeObj.BrowseName.Value] = nodeObj.NodeId
			
			self.fixAllNodeIds()
	
	def fixAllNodeIds(self):
		for UANodeId in self.UANodes:
			UANode = self.UANodes[UANodeId]
			UANode.fixNodeIds(self.Aliases)

class UANode:
	def __init__(self, xmlNode, uaNodeSet):
		self.DisplayName = []
		self.Description = []
		self.Category = []
		self.Documentation = None
		self.References = None
		self.RolePermissions = None
		self.NodeId = None
		self.BrowseName = None
		self.WriteMask = CESMII.BaseTypes.WriteMask(0)
		self.UserWriteMask = CESMII.BaseTypes.WriteMask(0)
		self.AccessRestrictions = CESMII.BaseTypes.AccessRestriction(0)
		self.HasNoPermissions = False
		self.SymbolicName = None
		self.ReleaseStatus = CESMII.BaseTypes.ReleaseStatus.Released
		
		self.IsFolder = False
		self.IsEnum = False
		self.IsOptional = False
			
		if xmlNode != None:
			# Find all of the DisplayName elements
			for dn in xmlNode.findall(BuildNS("DisplayName")):
				self.DisplayName.append(CESMII.BaseTypes.LocalizedText(dn))
				
			# Find all of the Description elements
			for desc in xmlNode.findall(BuildNS("Description")):
				self.Description.append(CESMII.BaseTypes.LocalizedText(desc))
				
			# Find all of the Category elements
			for cat in xmlNode.findall(BuildNS("Category")):
				self.Category.append(cat.text)
			
			valueObj = xmlNode.find(BuildNS("Documentation"))
			self.Documentation = None if valueObj == None else valueObj.text
			
			self.References = ListOfReferences(xmlNode.find(BuildNS("References")), uaNodeSet)
			self.RolePermissions = ListOfRolePermissions(xmlNode.find(BuildNS("RolePermissions")), uaNodeSet)
			self.NodeId = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="NodeId", uaNodeSet=uaNodeSet)
			self.BrowseName = CESMII.BaseTypes.QualifiedName(xmlNode=xmlNode, xmlAttrib="BrowseName")
			self.WriteMask = CESMII.BaseTypes.WriteMask(xmlNode=xmlNode, defaultValue=0)
			self.UserWriteMask = CESMII.BaseTypes.WriteMask(xmlNode=xmlNode, xmlAttrib="UserWriteMask", defaultValue=0)
			self.AccessRestrictions = CESMII.BaseTypes.AccessRestriction(xmlNode=xmlNode, defaultValue=0)
			self.HasNoPermissions = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("HasNoPermissions", False))
			self.SymbolicName = CESMII.BaseTypes.SymbolicName(xmlNode=xmlNode)
			self.ReleaseStatus = CESMII.BaseTypes.ReleaseStatus.getStatus(xmlNode)
			
			for ref in self.References.ReferenceList:
				if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_TYPE_DEFINITION and ref.IsForward:
					if ref.Value in CESMII.BaseTypes.FOLDER:
						self.IsFolder = True
						
				if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_SUBTYPE and not ref.IsForward:
					if ref.Value in CESMII.BaseTypes.ENUMERATION:
						self.IsEnum = True
												
				if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_MODELING_RULE and ref.IsForward:
					if ref.Value in CESMII.BaseTypes.OPTIONAL_PLACEHOLDER or ref.Value in CESMII.BaseTypes.OPTIONAL:
						self.IsOptional = True
						
	def getTypeDefinition(self):
		for ref in self.References.ReferenceList:
			if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_TYPE_DEFINITION and ref.IsForward:
				return ref
		
		return None
	
	def typeDefIsParent(self):
		return False
	
	def fixNodeIds(self, Aliases):
		self.NodeId.fix(Aliases)
		self.References.fixNodeIds(Aliases)
		self.RolePermissions.fixNodeIds(Aliases)
		
	def getSubTypeNodeId(self):
		for ref in self.References.ReferenceList:
			if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_SUBTYPE and not ref.IsForward:
				return ref
		return None
	
	def hasPropertiesOrComponents(self):
		for ref in self.References.ReferenceList:
			if (ref.ReferenceType.Value in CESMII.BaseTypes.ORGANIZES or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_PROPERTY or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_COMPONENT or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_ORDERED_COMPONENT or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_STRUCTURED_COMPONENT) and ref.IsForward:
				return True
		
		return False
		
	def getPropertiesAndComponents(self):
		ret = []
		
		for ref in self.References.ReferenceList:
			if (ref.ReferenceType.Value in CESMII.BaseTypes.ORGANIZES or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_PROPERTY or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_COMPONENT or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_ORDERED_COMPONENT or 
				ref.ReferenceType.Value in CESMII.BaseTypes.HAS_STRUCTURED_COMPONENT) and ref.IsForward:
				ret.append(ref)
		
		return ret
						
class UAInstance(UANode):
	def __init__(self, xmlNode, uaNodeSet):
		UANode.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.ParentNodeId = None
		
		if xmlNode != None:
			self.ParentNodeId = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="ParentNodeId", uaNodeSet=uaNodeSet)
	
	def typeDefIsParent(self):
		return UANode.getTypeDefinition(self) == self.ParentNodeId
	
	def fixNodeIds(self, Aliases):
		UANode.fixNodeIds(self, Aliases)
		self.ParentNodeId.fix(Aliases)
		
class UAObject(UAInstance):
	def __init__(self, xmlNode, uaNodeSet):
		UAInstance.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.EventNotifier = CESMII.BaseTypes.EventNotifier(0)
		
		if xmlNode != None:
			self.EventNotifier = CESMII.BaseTypes.EventNotifier(xmlNode=xmlNode, defaultValue=0)

	def getTypeDefinition(self):
		if self.hasPropertiesOrComponents():
			return self.NodeId
		else:
			for ref in self.References.ReferenceList:
				if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_TYPE_DEFINITION and ref.IsForward:
					return ref
		
		return None
									
	def getSubTypeNodeId(self):
		for ref in self.References.ReferenceList:
			if ref.ReferenceType.Value in CESMII.BaseTypes.HAS_TYPE_DEFINITION and ref.IsForward:
				return ref
		
		return None
			
class UAView(UAInstance):
	def __init__(self, xmlNode, uaNodeSet):
		UAInstance.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.ContainsNoLoops = False
		self.EventNotifier = CESMII.BaseTypes.EventNotifier(0)
		
		if xmlNode != None:
			self.ContainsNoLoops = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("ContainsNoLoops", False))
			self.EventNotifier = CESMII.BaseTypes.EventNotifier(xmlNode=xmlNode, defaultValue=0)
		
class UAVariable(UAInstance):
	def __init__(self, xmlNode, uaNodeSet):
		UAInstance.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.Value = None
		self.DataType = CESMII.BaseTypes.NodeId("i=24")
		self.ValueRank = CESMII.BaseTypes.ValueRank(-1)
		self.ArrayDimensions = CESMII.BaseTypes.ArrayDimensions("")
		self.AccessLevel = CESMII.BaseTypes.AccessLevel(1)
		self.UserAccessLevel = CESMII.BaseTypes.AccessLevel(1)
		self.MinimumSamplingInterval = CESMII.BaseTypes.Duration(0)
		self.Historizing = False
		self.ExtensionObject = []
		
		if xmlNode != None:
			valueObj = xmlNode.find(BuildNS("Value"))
			self.Value = None if valueObj == None else valueObj.text
			
			extObj = None if valueObj == None else valueObj.find(BuildNS("ListOfExtensionObject"))
			if extObj != None:
				for obj in extObj.findall(BuildNS("ExtensionObject")):
					self.ExtensionObject.append(obj.find(BuildNS("Body")).text)
			
			self.DataType = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="DataType", uaNodeSet=uaNodeSet)
			self.ValueRank = CESMII.BaseTypes.ValueRank(xmlNode=xmlNode, defaultValue=-1)
			self.ArrayDimensions = CESMII.BaseTypes.ArrayDimensions(xmlNode=xmlNode, defaultValue="")
			self.AccessLevel = CESMII.BaseTypes.AccessLevel(xmlNode=xmlNode, defaultValue=1)
			self.UserAccessLevel = CESMII.BaseTypes.AccessLevel(xmlNode=xmlNode, xmlAttrib="UserAccessLevel", defaultValue=1)
			self.MinimumSamplingInterval = CESMII.BaseTypes.Duration(xmlNode=xmlNode, xmlAttrib="MinimumSamplingInterval", defaultValue=0)
			self.Historizing = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("Historizing", False))
			
	def fixNodeIds(self, Aliases):
		UAInstance.fixNodeIds(self, Aliases)
		self.DataType.fix(Aliases)

class UAMethodArgument:
	def __init__(self, xmlNode, uaNodeSet):
		self.Name = None
		self.Description = []
			
		if xmlNode != None:
			nameObj = xmlNode.find(BuildNS("Name"))
			self.Name = None if nameObj == None else nameObj.text
			
			# Find all of the Description elements
			for desc in xmlNode.findall(BuildNS("Description")):
				self.Description.append(CESMII.BaseTypes.LocalizedText(desc))
				
class UAMethod(UAInstance):
	def __init__(self, xmlNode, uaNodeSet):
		UAInstance.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.ArgumentDescription = []
		self.Executable = True
		self.UserExecutable = True
		self.MethodDeclarationId = None
		
		if xmlNode != None:
			for desc in xmlNode.findall(BuildNS("ArgumentDescription")):
				self.ArgumentDescription.append(UAMethodArgument(desc, uaNodeSet))
							
			self.Executable = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("Executable", True))
			self.UserExecutable = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("UserExecutable", True))
			self.MethodDeclarationId = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="MethodDeclarationId", uaNodeSet=uaNodeSet)		
			
	def fixNodeIds(self, Aliases):
		UAInstance.fixNodeIds(self, Aliases)
		self.MethodDeclarationId.fix(Aliases)
		
class UAType(UANode):
	def __init__(self, xmlNode, uaNodeSet):
		UANode.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.IsAbstract = False
		
		if xmlNode != None:
			self.IsAbstract = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("IsAbstract", False))
		
class UAObjectType(UAType):
	def __init__(self, xmlNode, uaNodeSet):
		UAType.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
	def getTypeDefinition(self):
		ret = UAType.getTypeDefinition(self)
		if ret == None:
			ret = self.NodeId
		return ret
		
class UAVariableType(UAType):
	def __init__(self, xmlNode, uaNodeSet):
		UAType.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.Value = None
		self.DataType = CESMII.BaseTypes.NodeId("i=24")
		self.ValueRank = CESMII.BaseTypes.ValueRank(-1)
		self.ArrayDimensions = CESMII.BaseTypes.ArrayDimensions("")
		
		if xmlNode != None:
			valueObj = xmlNode.find(BuildNS("Value"))
			self.Value = None if valueObj == None else valueObj.text
			self.DataType = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="DataType", uaNodeSet=uaNodeSet)
			self.ValueRank = CESMII.BaseTypes.ValueRank(xmlNode=xmlNode, defaultValue=-1)
			self.ArrayDimensions = CESMII.BaseTypes.ArrayDimensions(xmlNode=xmlNode, defaultValue="")
	
	def fixNodeIds(self, Aliases):
		UAType.fixNodeIds(self, Aliases)
		self.DataType.fix(Aliases)

class UAReferenceType(UAType):
	def __init__(self, xmlNode, uaNodeSet):
		UAType.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.InverseName = []
		self.Symmetric = False
		
		if xmlNode != None:
			# Find all of the InverseName elements
			for inObj in xmlNode.findall(BuildNS("InverseName")):
				self.InverseName.append(CESMII.BaseTypes.LocalizedText(inObj))
			
			self.Symmetric = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("Symmetric", False))
			
class UADataType(UAType):
	def __init__(self, xmlNode, uaNodeSet):
		UAType.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.Definition = None
		self.Purpose = CESMII.BaseTypes.DataTypePurpose.Normal
		self.EnumValues = {}
		
		if xmlNode != None:
			self.Definition = DataTypeDefinition(xmlNode.find(BuildNS("Definition")), uaNodeSet=uaNodeSet)
			self.Purpose = CESMII.BaseTypes.DataTypePurpose.getStatus(xmlNode)
			
			if self.IsEnum:
				for field in self.Definition.Field:
					self.EnumValues[field.Value] = field.Name
	
	def fixNodeIds(self, Aliases):
		UAType.fixNodeIds(self, Aliases)
		self.Definition.fixNodeIds(Aliases)
		
	def hasPropertiesOrComponents(self):
		return UANode.hasPropertiesOrComponents(self) or len(self.Definition.Field) > 0
		
	def getPropertiesAndComponents(self):
		ret = UANode.getPropertiesAndComponents()
		for field in self.Definition.Field:
			ret.append(field)
		
class Reference(CESMII.BaseTypes.NodeId):
	def __init__(self, xmlNode, uaNodeSet):
		CESMII.BaseTypes.NodeId.__init__(self, xmlNode=xmlNode, uaNodeSet=uaNodeSet)
		
		self.ReferenceType = None
		self.IsForward = True
		
		if xmlNode != None:
			self.ReferenceType = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="ReferenceType", uaNodeSet=uaNodeSet)
			self.IsForward = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("IsForward", True))
			
	def fix(self, Aliases):
		CESMII.BaseTypes.NodeId.fix(self, Aliases)
		self.ReferenceType.fix(Aliases)
		
class ListOfReferences:
	def __init__(self, xmlNode, uaNodeSet):
		self.ReferenceList = []
		
		if xmlNode != None:
			for reference in xmlNode.findall(BuildNS("Reference")):
				self.ReferenceList.append(Reference(reference, uaNodeSet=uaNodeSet))
	
	def fixNodeIds(self, Aliases):
		for ref in self.ReferenceList:
			ref.fix(Aliases)
	
class DataTypeField:
	def __init__(self, xmlNode, uaNodeSet):
		self.DisplayName = []
		self.Description = []
		self.Name = None
		self.SymbolicName = None
		self.DataType = CESMII.BaseTypes.NodeId("i=24")
		self.ValueRank = CESMII.BaseTypes.ValueRank(-1)
		self.ArrayDimensions = CESMII.BaseTypes.ArrayDimensions("")
		self.MaxStringLength = 0
		self.Value = -1
		self.IsOptional = False
		self.AllowSubTypes = False
		
		if xmlNode != None:
			# Find all of the DisplayName elements
			for dn in xmlNode.findall(BuildNS("DisplayName")):
				self.DisplayName.append(CESMII.BaseTypes.LocalizedText(dn))
				
			# Find all of the Description elements
			for desc in xmlNode.findall(BuildNS("Description")):
				self.Description.append(CESMII.BaseTypes.LocalizedText(desc))
				
			self.Name = xmlNode.attrib.get("Name", None)
			self.SymbolicName = CESMII.BaseTypes.SymbolicName(xmlNode=xmlNode)
			self.DataType = CESMII.BaseTypes.NodeId(xmlNode=xmlNode, xmlAttrib="DataType", defaultValue=CESMII.BaseTypes.INTEGER[0], uaNodeSet=uaNodeSet)
			self.ValueRank = CESMII.BaseTypes.ValueRank(xmlNode=xmlNode, defaultValue=-1)
			self.ArrayDimensions = CESMII.BaseTypes.ArrayDimensions(xmlNode=xmlNode, defaultValue="")
			self.MaxStringLength = CESMII.TypeUtils.toInt(xmlNode.attrib.get("MaxStringLength", 0))
			self.Value = CESMII.TypeUtils.toInt(xmlNode.attrib.get("Value", -1))
			self.IsOptional = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("IsOptional", False))
			self.AllowSubTypes = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("AllowSubTypes", False))
	
	def fixNodeIds(self, Aliases):
		self.DataType.fix(Aliases)
	
class DataTypeDefinition:
	def __init__(self, xmlNode, uaNodeSet):
		self.Field = []
		self.Name = None
		self.SymbolicName = None
		self.IsUnion = False
		self.IsOptionSet = False
		self.BaseType = CESMII.BaseTypes.QualifiedName("")
			
		if xmlNode != None:
			for dtf in xmlNode.findall(BuildNS("Field")):
				self.Field.append(DataTypeField(dtf, uaNodeSet))
				
			self.Name = CESMII.BaseTypes.QualifiedName(xmlNode=xmlNode, xmlAttrib="Name")
			self.SymbolicName = CESMII.BaseTypes.SymbolicName(xmlNode=xmlNode)
			self.IsUnion = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("IsUnion", False))
			self.IsOptionSet = CESMII.TypeUtils.toBoolean(xmlNode.attrib.get("IsOptionSet", False))		
			self.BaseType = CESMII.BaseTypes.QualifiedName(xmlNode=xmlNode, xmlAttrib="BaseType", defaultValue="")
	
	def fixNodeIds(self, Aliases):
		for dtf in self.Field:
			dtf.fixNodeIds(Aliases)