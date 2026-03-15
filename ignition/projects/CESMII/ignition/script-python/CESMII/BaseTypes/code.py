ORGANIZES = ("i=35", "Organizes")
HAS_MODELING_RULE = ("i=37", "HasModellingRule")
HAS_ENCODING = ("i=38", "HasEncoding")
HAS_TYPE_DEFINITION = ("i=40", "HasTypeDefinition")
HAS_SUBTYPE = ("i=45", "HasSubtype")
HAS_PROPERTY = ("i=46", "HasProperty")
HAS_COMPONENT = ("i=47", "HasComponent")
HAS_ORDERED_COMPONENT = ("i=49", "HasOrderedComponent")
HAS_STRUCTURED_COMPONENT = ("i=24136", "HasStructuredComponent")
FOLDER = ("i=61", "FolderType")
OPTIONAL_PLACEHOLDER = ("i=11508", "OptionalPlaceholder")
OPTIONAL = ("i=80", "Optional")

BOOLEAN = ("i=1", "Boolean")
DATETIME = ("i=13", "DateTime")

# Decimals
DECIMAL = ("i=50", "Decimal")
FLOAT = ("i=10", "Float")
DOUBLE = ("i=11", "Double")
DURATION = ("i=290", "Duration")

# Integers
NUMBER = ("i=26", "Number")
INTEGER = ("i=27", "Integer")
INT16 = ("i=4", "Int16")
INT32 = ("i=6", "Int32")
INT64 = ("i=8", "Int64")
SBYTE = ("i=2", "SByte")
UINTEGER = ("i=38", "UInteger")
BYTE = ("i=3", "Byte")
UINT16 = ("i=5", "UInt16")
UINT32 = ("i=7", "UInt32")
UINT64 = ("i=9", "UInt64")
STATUSCODE = ("i=19", "StatusCode")
UTCTIME = ("i=294", "UtcTime")
ENUMERATION = ("i=29", "Enumeration")

# Strings
GUID = ("i=14", "Guid")
LOCALIZED_TEXT = ("i=21", "LocalizedText")
NODEID = ("i=17", "NodeId")
BYTE_STRING = ("i=15", "ByeString")
QUALIFIED_NAME = ("i=20", "QualifiedName")
STRING = ("i=12", "String")
LOCALE_ID = ("i=295", "LocaleId")
NORMALIZED_STRING = ("i=12877", "NormalizedString")
DECIMAL_STRING = ("i=12878", "DecimalString")
DURATION_STRING = ("i=12879", "DurationString")
TIME_STRING = ("i=12880", "TimeString")
DATE_STRING = ("i=12881", "DateString")
STRUCTURE = ("i=22", "Structure")
CURRENCY_UNIT_TYPE = ("i=23514", "CurrencyUnitType")

def mapDataType(DataType, ValueRank):
	if DataType.NodeId.Value in BOOLEAN:
		ret = "Boolean"
	elif DataType.NodeId.Value in DATETIME:
		ret = "DateTime"
	elif DataType.NodeId.Value in (DECIMAL + FLOAT):
		ret = "Float4"
	elif DataType.NodeId.Value in (DOUBLE + DURATION):
		ret = "Float8"
	elif DataType.NodeId.Value in BYTE:
		ret = "Int1"
	elif DataType.NodeId.Value in (SBYTE, INT16):
		ret = "Int2"
	elif DataType.NodeId.Value in (NUMBER, UINT16, INT32, STATUSCODE, ENUMERATION, INTEGER):
		ret = "Int4"
	elif DataType.NodeId.Value in (UINT32, INT64, UINT64, UTCTIME, UINTEGER):
		ret = "Int8"
	else:
		ret = "String"
	
	if ValueRank > 1:
		ret = "Document"
	elif ValueRank == 1:
		ret = "%sArray" % ret
	
	return ret

class ReleaseStatus:
	Released = "Released"
	Draft = "Draft"
	Deprecated = "Deprecated"
	
	@staticmethod
	def getStatus(xmlNode):
		status = xmlNode.attrib.get("ReleaseStatus", "Released")
		if status == "Released":
			return ReleaseStatus.Released
		elif status == "Draft":
			return ReleaseStatus.Draft
		elif status == "Deprecated":
			return ReleaseStatus.Deprecated
			
		return ReleaseStatus.Released
	
class DataTypePurpose:
	Normal = "Normal"
	ServicesOnly = "ServicesOnly"
	CodeGenerator = "CodeGenerator"
	
	@staticmethod
	def getStatus(xmlNode):
		status = xmlNode.attrib.get("Purpose", "Normal")
		if status == "Normal":
			return DataTypePurpose.Normal
		elif status == "ServicesOnly":
			return DataTypePurpose.ServicesOnly
		elif status == "CodeGenerator":
			return DataTypePurpose.CodeGenerator
			
		return DataTypePurpose.Normal
	
class NodeId:
	def __init__(self, *args, **kwargs):
		self.Value = ""
		self.Index = None
		self.IsAlias = False
		
		if len(kwargs) == 0:
			self.Value = args[0]
		else:
			if "Value" in kwargs:
				self.Value = kwargs["Value"]
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					defaultValue = None
					if "defaultValue" in kwargs:
						defaultValue = kwargs["defaultValue"]
						
					self.Value = kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], defaultValue)
				else:
					self.Value = kwargs["xmlNode"].text
		
		if self.Value != None:
			if self.Value.find("=") > -1:
				parts = self.Value.split(";")
				if len(parts) > 1:
					self.Value = parts[1]
					self.Index = CESMII.TypeUtils.toInt(parts[0].replace("ns=", ""))
										
					if "uaNodeSet" in kwargs and self.Index > 0:
						uaNodeSet = kwargs["uaNodeSet"]
						if uaNodeSet.ParentNamespaceUris != None:
							uri = uaNodeSet.NamespaceUris.UriList[self.Index-1]
							self.Index = uaNodeSet.ParentNamespaceUris[uri]
				else:
					self.Index = 0
			else:
				self.IsAlias = True
	
	def fix(self, Aliases):
		if self.IsAlias:
			self.clone(Aliases[self.Value])
			
	def clone(self, NodeIdToClone):
		self.Value = NodeIdToClone.Value
		self.Index = NodeIdToClone.Index
		self.IsAlias = NodeIdToClone.IsAlias
		
	def __eq__(self, other):
		"""Overrides the default implementation"""
		if isinstance(other, NodeId):
			return self.Value == other.Value and self.Index == self.Index
		return False
		
	def __ne__(self, other):
		"""Overrides the default implementation (unnecessary in Python 3)"""
		return not self.__eq__(other)
		
	def getNamespaceNodeId(self):
		return "ns=%d;%s" % (self.Index, self.Value)

class QualifiedName:
	def __init__(self, *args, **kwargs):
		self.Value = ""
		self.Index = None
		
		if len(kwargs) == 0:
			self.Value = args[0]
		else:
			if "Value" in kwargs:
				self.Value = kwargs["Value"]
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], None)
				else:
					self.Value = kwargs["xmlNode"].attrib.get("QualifiedName", None)
				
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
		
		if self.Value != None:
			if self.Value.find(":") > -1:
				parts = self.Value.split(":")
				self.Value = parts[1]
				self.Index = CESMII.TypeUtils.toInt(parts[0])
			else:
				self.Index = 0
						
class SymbolicName:
	def __init__(self, *args, **kwargs):
		self.Value = ""
		
		if len(kwargs) == 0:
			self.Value = args[0]
		else:
			if "Value" in kwargs:
				self.Value = kwargs["Value"]
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], None)
				else:
					self.Value = kwargs["xmlNode"].attrib.get("SymbolicName", None)
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
			
class ValueRank:
	def __init__(self, *args, **kwargs):
		self.Value = -1
		
		if len(kwargs) == 0:
			self.Value = CESMII.TypeUtils.toInt(args[0])
		else:
			if "Value" in kwargs:
				self.Value = CESMII.TypeUtils.toInt(kwargs["Value"])
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], -1))
				else:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get("ValueRank", -1))
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]

class ArrayDimensions:
	def __init__(self, *args, **kwargs):
		self.Value = ""
		
		if len(kwargs) == 0:
			self.Value = args[0]
		else:
			if "Value" in kwargs:
				self.Value = kwargs["Value"]
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], None)
				else:
					self.Value = kwargs["xmlNode"].attrib.get("ArrayDimensions", None)
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]

class AccessLevel:
	def __init__(self, *args, **kwargs):
		self.Value = 0
		
		if len(kwargs) == 0:
			self.Value = CESMII.TypeUtils.toInt(args[0])
		else:
			if "Value" in kwargs:
				self.Value = CESMII.TypeUtils.toInt(kwargs["Value"])
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], 0))
				else:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get("AccessLevel", 0))
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
		
class Duration:
	def __init__(self, *args, **kwargs):
		self.Value = 0
		
		if len(kwargs) == 0:
			self.Value = CESMII.TypeUtils.toFloat(args[0])
		else:
			if "Value" in kwargs:
				self.Value = CESMII.TypeUtils.toFloat(kwargs["Value"])
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], 0))
				else:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get("Duration", 0))
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
		
class ModelVersion:
	def __init__(self, *args, **kwargs):
		self.Value = ""
		
		if len(kwargs) == 0:
			self.Value = args[0]
		else:
			if "Value" in kwargs:
				self.Value = kwargs["Value"]
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], None)
				else:
					self.Value = kwargs["xmlNode"].attrib.get("ModelVersion", None)
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]

class LocalizedText:
	def __init__(self, xmlNode):
		self.Value = None
		self.Locale = None
			
		if xmlNode != None:
			self.Value = xmlNode.text
			self.Locale = CESMII.BaseTypes.Locale(xmlNode=xmlNode)
						
class Locale:
	def __init__(self, *args, **kwargs):
		self.Value = ""
		
		if len(kwargs) == 0:
			self.Value = args[0]
		else:
			if "Value" in kwargs:
				self.Value = kwargs["Value"]
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], None)
				else:
					self.Value = kwargs["xmlNode"].attrib.get("Locale", None)
				
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
		
class WriteMask:
	def __init__(self, *args, **kwargs):
		self.Value = 0
		
		if len(kwargs) == 0:
			self.Value = CESMII.TypeUtils.toInt(args[0])
		else:
			if "Value" in kwargs:
				self.Value = CESMII.TypeUtils.toInt(kwargs["Value"])
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], 0))
				else:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get("WriteMask", 0))
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
		
class EventNotifier:
	def __init__(self, *args, **kwargs):
		self.Value = 0
		
		if len(kwargs) == 0:
			self.Value = CESMII.TypeUtils.toInt(args[0])
		else:
			if "Value" in kwargs:
				self.Value = CESMII.TypeUtils.toInt(kwargs["Value"])
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], 0))
				else:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get("EventNotifier", 0))
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]
		
class AccessRestriction:
	def __init__(self, *args, **kwargs):
		self.Value = 0
		
		if len(kwargs) == 0:
			self.Value = CESMII.TypeUtils.toInt(args[0])
		else:
			if "Value" in kwargs:
				self.Value = CESMII.TypeUtils.toInt(kwargs["Value"])
			elif "xmlNode" in kwargs:
				if "xmlAttrib" in kwargs:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get(kwargs["xmlAttrib"], 0))
				else:
					self.Value = CESMII.TypeUtils.toInt(kwargs["xmlNode"].attrib.get("AccessRestrictions", 0))
								
			if "defaultValue" in kwargs and self.Value == None:
				self.Value = kwargs["defaultValue"]