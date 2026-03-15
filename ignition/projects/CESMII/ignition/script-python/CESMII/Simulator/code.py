def buildProgrammableSimulator(tagPath):
	data = []
	defaultValues = {"Int1":0, "Int2":0, "Int4":0, "Int8":0, "Float4":0, "Float8":0, "Boolean":False, "String":"", "DateTime":system.date.now()}
	simulatorDataType = {"Int1":"Int16", "Int2":"Int16", "Int4":"Int32", "Int8":"Int64", "Float4":"Float", "Float8":"Double", "Boolean":"Boolean", "String":"String", "DateTime":"DateTime"}

	results = system.tag.browse(tagPath, {"recursive":True, "tagType":"AtomicTag"})
	for result in results.getResults():
		fullPath = str(result["fullPath"])
		if fullPath.find("]") > -1:
			fullPath = fullPath[fullPath.find("]")+1:]
			
		dataType = str(result.get("dataType", "String"))
		value = str(defaultValues.get(dataType, "null"))
		simDataType = simulatorDataType.get(dataType, "String")
		data.append(["0", fullPath, value, simDataType])
		
	return system.dataset.toCSV(system.dataset.toDataSet(["Time Interval", "Browse Path", "Value Source", "Data Type"], data))