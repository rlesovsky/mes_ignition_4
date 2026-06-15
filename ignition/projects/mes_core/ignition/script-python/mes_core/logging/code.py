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

''''
Script: log.py
Purpose: Logs messages to the MES logger with specified severity.
Context: Used to log events or errors in MES Ignition scripts.
Parameters:
   - message: String, the message to log.
   - level: String, logging level ('fatal', 'error', 'warn', 'info', 'debug', 'trace').
   - debug: Bool, enables console output (default: False).
 Returns: None
'''

def log(message, level, debug=False):
    logger = system.util.getLogger('MES')

    try:
        # Validate inputs lightly
        if not isinstance(message, str):
            logger.error('Invalid message type: %s' % type(message))
            return
        level = level.lower()
        if level not in ('fatal', 'error', 'warn', 'info', 'debug', 'trace'):
            logger.error('Invalid log level: %s' % level)
            return

        # Always log at the requested level; `debug` only gates the extra status message.
        getattr(logger, level)(message)
        if debug:
            system.util.sendLogMessage('MES: [%s] %s' % (level.upper(), message), 'MES')

    except Exception as e:
        logger.error('Logging error: %s' % str(e))
        if debug:
            system.util.sendLogMessage('MES: Logging error: %s' % str(e), 'MES')

# Example usage:
# log('Production count updated', 'info', debug=True)
# log('Database error', 'error', debug=False)