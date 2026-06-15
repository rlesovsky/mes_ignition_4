"""
UNS Data Publisher Module
=========================
Publishes line data to BigQuery tags for UNS/MQTT distribution.

Author: Randy Lesovsky
Company: Texas Automation Systems
Version: 1.0.1
"""

import json


def publish_to_bigquery(line_path, logger=None):
	"""
	Publish line data to BigQuery tag for UNS/MQTT distribution.
	
	Reads line metrics (Line, Edge, OEE) and writes them as JSON to the 
	BigQuery/Line Data tag. The tag should be configured with MQTT settings 
	to auto-publish to the UNS.
	
	Args:
		line_path (str): Full tag path to line (e.g., "[default]Enterprise/Site/Area/Line 1")
		logger (object): Optional logger instance for debug/error messages
		
	Returns:
		dict: Result dictionary with keys:
			- success (bool): Whether operation succeeded
			- message (str): Success/error message
			- data (str): JSON data written (only if success=True)
			
	Example:
		>>> result = publish_to_bigquery("[default]Enterprise/Site/Area/Line 1")
		>>> if result['success']:
		>>>     print "Success:", result['message']
	"""
	
	def safe_value(val):
		"""Convert non-JSON-serializable values to JSON-compatible types."""
		if val is None:
			return None
		if hasattr(val, 'getTime'):
			try:
				return val.getTime()
			except:
				return None
		val_str = str(val)
		if val_str == '[]':
			return None
		try:
			if isinstance(val, bool):
				return val
			if isinstance(val, (int, long)):
				return int(val)
			if isinstance(val, float):
				return float(val)
			if isinstance(val, (str, unicode)):
				return str(val)
			if hasattr(val, '__iter__'):
				return list(val)
			return str(val)
		except:
			return None
	
	# Input validation
	if not line_path or not isinstance(line_path, basestring):
		error_msg = "Invalid line_path parameter. Must be a non-empty string."
		if logger:
			logger.error(error_msg)
		return {"success": False, "message": error_msg}
	
	try:
		# Build tag paths
		bigquery_data_tag = line_path + "/BigQuery/Line Data"
		line_data_path = line_path + "/Line"
		edge_path = line_path + "/Edge"
		oee_path = line_path + "/Line/OEE"
		
		if logger:
			logger.debug("Publishing data for: {}".format(line_path))
		
		# Verify BigQuery tag exists
		check_tag = system.tag.readBlocking([bigquery_data_tag])
		if not check_tag[0].quality.isGood():
			error_msg = "BigQuery tag does not exist or has bad quality: {}".format(bigquery_data_tag)
			if logger:
				logger.error(error_msg)
			return {"success": False, "message": error_msg}
		
		# Read all tags from each namespace - CORRECTED PATHS
		line_tags = system.tag.readBlocking([
			line_data_path + "/Dispatch/OEE Infeed/LastCount",
			line_data_path + "/Dispatch/OEE Outfeed/LastCount",
			line_data_path + "/State",
			line_data_path + "/Dispatch/OEE Waste/LastCount"
		])
		
		edge_tags = system.tag.readBlocking([
			edge_path + "/Infeed",
			edge_path + "/Outfeed",
			edge_path + "/State",
			edge_path + "/Waste"
		])
		
		oee_tags = system.tag.readBlocking([
			oee_path + "/OEE",
			oee_path + "/OEE Quality",
			oee_path + "/OEE Performance",
			oee_path + "/OEE Availability"
		])
		
		# Check for bad quality tags
		bad_tags = []
		for i, tag in enumerate(line_tags):
			if not tag.quality.isGood():
				bad_tags.append("Line/" + ["Dispatch/OEE Infeed/LastCount", "Dispatch/OEE Outfeed/LastCount", "State", "Dispatch/OEE Waste/LastCount"][i])
		for i, tag in enumerate(edge_tags):
			if not tag.quality.isGood():
				bad_tags.append("Edge/" + ["Infeed", "Outfeed", "State", "Waste"][i])
		for i, tag in enumerate(oee_tags):
			if not tag.quality.isGood():
				bad_tags.append("OEE/" + ["OEE", "Quality", "Performance", "Availability"][i])
		
		if bad_tags and logger:
			logger.warn("Bad quality tags detected: {}".format(", ".join(bad_tags)))
		
		# Structure the data
		data = {
			"timestamp": system.date.format(system.date.now(), "yyyy-MM-dd HH:mm:ss"),
			"Line": {
				"Infeed": safe_value(line_tags[0].value),
				"Outfeed": safe_value(line_tags[1].value),
				"State": safe_value(line_tags[2].value),
				"Waste": safe_value(line_tags[3].value)
			},
			"Edge": {
				"Infeed": safe_value(edge_tags[0].value),
				"Outfeed": safe_value(edge_tags[1].value),
				"State": safe_value(edge_tags[2].value),
				"Waste": safe_value(edge_tags[3].value)
			},
			"OEE": {
				"OEE": safe_value(oee_tags[0].value),
				"Quality": safe_value(oee_tags[1].value),
				"Performance": safe_value(oee_tags[2].value),
				"Availability": safe_value(oee_tags[3].value)
			}
		}
		
		# Convert to JSON
		try:
			json_data = json.dumps(data)
		except Exception as e:
			error_msg = "Failed to serialize data to JSON: {}".format(str(e))
			if logger:
				logger.error(error_msg)
			return {"success": False, "message": error_msg}
		
		# Write to BigQuery tag
		try:
			system.tag.writeBlocking([bigquery_data_tag], [json_data])
		except Exception as e:
			error_msg = "Failed to write to tag {}: {}".format(bigquery_data_tag, str(e))
			if logger:
				logger.error(error_msg)
			return {"success": False, "message": error_msg}
		
		# Verify write by reading back
		try:
			verify_read = system.tag.readBlocking([bigquery_data_tag])
			if not verify_read[0].quality.isGood():
				error_msg = "Tag write verification failed - tag has bad quality after write"
				if logger:
					logger.error(error_msg)
				return {"success": False, "message": error_msg}
		except Exception as e:
			error_msg = "Failed to verify tag write: {}".format(str(e))
			if logger:
				logger.error(error_msg)
			return {"success": False, "message": error_msg}
		
		# Success
		success_msg = "Data successfully written to {}".format(bigquery_data_tag)
		if logger:
			logger.info(success_msg)
		
		return {
			"success": True,
			"message": success_msg,
			"data": json_data
		}
		
	except Exception as e:
		error_msg = "Unexpected error: {}".format(str(e))
		if logger:
			logger.error(error_msg)
		return {"success": False, "message": error_msg}
		
# From a timer script
#publish_to_bigquery("[default]Enterprise/Site/Area/Line 1")