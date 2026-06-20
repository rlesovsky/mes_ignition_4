'''
Gateway Events HiveMQ UNS
'''



'''
This script publishes tag values from an Ignition SCADA system to an MQTT broker, using the
Cirrus Link MQTT Transmission module, for a UNS. It works as follows:

1. Starting from the root tag path '[default]Enterprise', it recursively browses all subfolders
   to COLLECT the full paths of every AtomicTag (a tag that holds a value).

2. All collected paths are read in a single bulk system.tag.readBlocking([...]) call rather than
   one read per tag.

3. For each tag, the MQTT topic is built by replacing the '[default]Enterprise' root with an
   'Enterprise' topic prefix.

4. If the value is a dataset (BasicDataset), it is converted to a list of row dictionaries.

5. The value is serialized to a JSON string for the payload. If serialization fails, a string
   fallback payload is published (the tag is NOT silently dropped).

6. Each message is published RETAINED (retain=1) so consumers receive the last-known value on
   connect. Publish activity is logged at DEBUG, not INFO.

Note: this is still timer-polled. For a UNS the ideal trigger is a tag-change event rather than
polling the whole tree each tick; that is a gateway-event configuration change beyond this script.
'''



def publish_mqtt():
    from com.inductiveautomation.ignition.common import BasicDataset
    import system
    import json

    logger = system.util.getLogger("MQTT_Publish")

    # Function to convert BasicDataset to a list of dictionaries
    def convert_dataset_to_dict_list(dataset):
        columnNames = list(dataset.getColumnNames())
        rowData = []
        for rowIndex in range(dataset.getRowCount()):
            rowDict = {}
            for colIndex, colName in enumerate(columnNames):
                rowDict[colName] = dataset.getValueAt(rowIndex, colIndex)
            rowData.append(rowDict)
        return rowData

    # Recursively collect the paths of every AtomicTag under the given path (no reads here).
    def collect_tag_paths(path, paths):
        for result in system.tag.browse(path).getResults():
            tagPath = str(result['fullPath'])
            if str(result['tagType']) == 'AtomicTag':
                paths.append(tagPath)
            else:
                collect_tag_paths(tagPath, paths)

    # Define the path where the tags are located
    root_path = '[default]Enterprise'

    # 1) Collect, then 2) bulk-read in a single call.
    tagPaths = []
    collect_tag_paths(root_path, tagPaths)
    if not tagPaths:
        return
    qualifiedValues = system.tag.readBlocking(tagPaths)

    for tagPath, qv in zip(tagPaths, qualifiedValues):
        tagValue = qv.value
        if tagValue is None:
            tagValue = ''

        # Construct the MQTT topic from the tag's full path
        mqtt_topic = 'Enterprise' + tagPath.replace('[default]Enterprise', '')

        # Convert datasets to a JSON-friendly list of row dicts
        if isinstance(tagValue, BasicDataset):
            tagValue = convert_dataset_to_dict_list(tagValue)
            logger.debug("Converted dataset for {}: {}".format(tagPath, tagValue))

        # Serialize to JSON; on failure publish a string fallback (do not drop the tag)
        try:
            payload = json.dumps(tagValue)
        except Exception as e:
            logger.debug("JSON serialize failed for {}: {}; publishing string fallback".format(tagPath, str(e)))
            payload = str(tagValue)

        # Publish RETAINED (QoS 0, retain 1) so consumers get last-known value on connect.
        # Arguments: MQTT Server name, MQTT topic, payload, QoS, retain flag
        system.cirruslink.transmission.publish("HiveMQ", str(mqtt_topic), str(payload), 0, 1)
        logger.debug("Published to {}: {}".format(mqtt_topic, payload))

#publish_mqtt()