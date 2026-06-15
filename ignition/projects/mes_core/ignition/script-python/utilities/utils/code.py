#* 4.0 Solutions LLC CONFIDENTIAL
#* __________________
#* 
#*  [2015] - [2022] 4.0 Solutions LLC 
#*  All Rights Reserved.
#* 
#* NOTICE:  All information contained herein is, and remains
#* the property of 4.0 Solutions LLC and its suppliers,
#* if any.  The intellectual and technical concepts contained
#* herein are proprietary to 4.0 Solutions LLC
#* and its suppliers and may be covered by U.S. and Foreign Patents,
#* patents in process, and are protected by trade secret or copyright law.
#* Dissemination of this information or reproduction of this material
#* is strictly forbidden unless prior written permission is obtained
#* from 4.0 Solutions LLC.

import re
htmlPatternBR = re.compile('\<br\>', re.I)
htmlPatternGeneric = re.compile('\<.*?\>', re.I)

def stripHTML(string, handleBreaks=False):
	"""This removes the HTML markup tags from a string.
	Not to be confused with parsing, of which this does *NONE*.
	https://stackoverflow.com/a/1732454
	"""
	if handleBreaks:
		# line breaks are line feeds
		string = htmlPatternBR.sub('\n', string)
		
	# everything else can be stripped
	string = htmlPatternGeneric.sub('', string)
	
	return string
	
	
def clipboard(imagePath):
	from java.awt.datatransfer import StringSelection
	from java.awt.datatransfer import Clipboard
	from java.awt import Toolkit
	from java.awt.datatransfer import DataFlavor
	toolkit = Toolkit.getDefaultToolkit()
	clipboard = toolkit.getSystemClipboard()
	clipboard.setContents(StringSelection(imagePath), None)
	contents = clipboard.getContents(None)
	logger = system.util.getLogger('IntellicInfo')
	content = contents.getTransferData(DataFlavor.stringFlavor)
	logger.infof('Image %s copied to clipboard.  Content = %s',imagePath,content)
	
def retarget(project):
	system.util.retarget(project)
	

def translateTable(component, translateColumns = [], locale=None, rawTablePropertyName = 'rawdata', destinationTablePropertyName = 'data'):
	# translate the defect descriptions
	data = getattr(component, rawTablePropertyName)
	
	if not locale:
		locale = system.util.getLocale()
	
	header = [h for h in data.getColumnNames()]
	
	translateColumnIX = [data.getColumnIndex(column) for column in translateColumns]
	
#	for rix in range(data.getRowCount()):
#		for cix in translateColumnIX:
#			entry = data.getValueAt(rix, cix)
#			translatedEntry = system.util.translate(entry, locale, False)
#			data.setValueAt(rix, cix, translatedEntry)
#	
#	setattr(component, destinationTablePropertyName, data)
	
	if data.getRowCount() > 0:
		# Ignition datasets are immutable; system.dataset.setValue returns a NEW dataset
		# rather than mutating in place (data.setValueAt would not stick).
		for rix in range(data.getRowCount()):
			for cix in translateColumnIX:
				translatedEntry = system.util.translate(data.getValueAt(rix, cix), locale, False)
				data = system.dataset.setValue(data, rix, cix, translatedEntry)

		setattr(component, destinationTablePropertyName, data)
	