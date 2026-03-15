def handleTimerEvent():
	
	logger = system.util.getLogger("OEE_Gateway")
	
	try:
		linePath = "[default]Enterprise/Site/Area/Line 1"
		
		# CORRECTED: Run Enabled is under /Line/ subfolder
		runEnabledPath = linePath + "/Line/Run Enabled"
		
		# Check if run is enabled
		runEnabledResult = system.tag.readBlocking([runEnabledPath])[0]
		
		if not runEnabledResult.quality.isGood():
			logger.warn("Run Enabled tag quality is bad: %s" % runEnabledResult.quality)
			return
		
		runEnabled = runEnabledResult.value
		
		if runEnabled == 1 or runEnabled == True:
			logger.debug("Calculating OEE for: %s" % linePath)
			mes_core.oee.getOee(linePath)
			logger.debug("OEE calculation complete")
		else:
			logger.trace("Skipping OEE - Run not enabled")
			
	except Exception as e:
		import traceback
		logger.error("OEE calculation failed: %s" % str(e))
		logger.error("Traceback: %s" % traceback.format_exc())

# Call the function
handleTimerEvent()
