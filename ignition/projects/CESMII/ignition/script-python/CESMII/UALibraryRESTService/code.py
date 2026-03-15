def getCreds(session):
	url = session.custom.settings.library
	username = session.custom.settings.username
	password = session.custom.settings.password
	return (url, username, password)

def namespaces(session):
	import urllib
	
	(url, username, password) = getCreds(session)
	
	url = "%s/infomodel/namespaces" % url
	res = system.net.httpGet(url=url, username=username, password=password, headerValues={"accept":"text/plain"})
	jsonRes = system.util.jsonDecode(res)
	namespaces = {}
	for row in jsonRes:
		parts = row.split(",")
		if parts[0] in namespaces:
			namespaces[parts[0]].append(parts[1])
		else:
			namespaces[parts[0]] = [parts[1]]
	return namespaces

def find(session, keywords=None):
	import urllib
	
	(url, username, password) = getCreds(session)
	
	if keywords == None or keywords == "":
		keywords = "*"
	
	url = "%s/infomodel/find" % url
	if keywords != None:
		url += "?%s" % urllib.urlencode({"keywords":keywords})
		
	res = system.net.httpGet(url=url, username=username, password=password, headerValues={"accept":"text/plain"})
	jsonRes = system.util.jsonDecode(res)
	return jsonRes
		
def download(session, identifier):
	import urllib
	
	(url, username, password) = getCreds(session)
	
	url = "%s/infomodel/download/%s" % (url, identifier)
		
	res = system.net.httpGet(url=url, username=username, password=password, headerValues={"accept":"text/plain"})
	jsonRes = system.util.jsonDecode(res)
	return jsonRes
	
def downloadXML(session, identifier):
	res = download(session, identifier)
	return getXML(res)
	
def getXML(res):
	return res["nodeset"]["nodesetXml"].strip('ï»¿')