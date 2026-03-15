def toBoolean(value):
	if value == None:
		return None
	
	try:
		return str(value).lower() in ['true', '1', 'yes']
	except:
		return None
		
def toInt(value):
	if value == None:
		return None
	
	try:
		return int(value)
	except:
		return None
		
def toFloat(value):
	if value == None:
		return None
	
	try:
		return float(value)
	except:
		return None
		
def toDate(value):
	if value == None:
		return None
	
	try:
		value = value.replace("T", " ").replace("Z", "")
		return system.date.parse(value, "yyyy-MM-dd HH:mm:ss")
	except:
		return None
		
def coalesce(value, valueIfNull):
	if value == None:
		return valueIfNull
		
	return value
	
def validateURL(url):
	import urlparse
	import string
	
	try:
		pieces = urlparse.urlparse(url)
		assert all([pieces.scheme, pieces.netloc])
		assert set(pieces.netloc) <= set(string.letters + string.digits + '-.')
		assert pieces.scheme in ['http', 'https']
		return True
	except:
		return False