'''
Gateway Events HiveMQ UNS
'''



'''
This script is used to publish tag values from an Ignition SCADA system to an MQTT broker, 
using the Cirrus Link MQTT Transmission module. The script works as follows:

1. It starts from a root tag path in the Ignition system, and it recursively goes through all 
   tags and subfolders from that path.

2. For each tag encountered, it checks if the tag is of type 'AtomicTag', which indicates that 
   the tag holds a value.

3. If the tag is an 'AtomicTag', it reads the tag's value. If the value is None, it converts 
   it to an empty string. 

4. It then constructs an MQTT topic for the tag. The topic is built by appending the tag's 
   full path (with the root path removed) to a base string 'UFP Industries/Retail/Moneta VA 554/SCADA'.

5. If the tag's value is a dataset (instance of BasicDataset), it retrieves the column names 
   and then converts the dataset into a list of dictionaries, where each dictionary represents 
   a row in the dataset.

6. The tag value (or the list of dictionaries if it's a dataset) is then converted to a JSON 
   string to be used as the MQTT payload. If the conversion fails (which can happen if the value 
   is not serializable), it assigns the raw tagValue to the payload and skips to the next iteration.

7. Finally, it publishes the MQTT message to the broker using the MQTT Transmission module. 
   The publish function is called with the following arguments: the MQTT Server name, the MQTT 
   topic, the payload, the QoS, and the retain flag.

8. If the tag is not an 'AtomicTag', it assumes that the tag is a folder and calls the 
   process_tags function recursively on the tag's path to process its subtags.

9. The root tag path is defined as '[edge]Driftwood Dairy', and the process starts by calling 
   the process_tags function on this root path.
'''



def publish_mqtt():
    from com.inductiveautomation.ignition.common import BasicDataset
    import system
    import json

    # Logging function
    def log(message):
        system.util.getLogger("MQTT_Publish").info(message)

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

    # Recursive function to process tags under a given path
    def process_tags(path):
        # Browse through the tags under the given path
        results = system.tag.browse(path).getResults()

        for result in results:
            tagPath = result['fullPath']
            tagPath = str(tagPath)
            # If the tag is a folder, process its subtags
            if str(result['tagType']) == 'AtomicTag':
                # Read the value of the tag
                tagValue = system.tag.readBlocking([tagPath])[0].value
                if tagValue is None:
                    tagValue = ''
                # Construct the MQTT topic from the tag's full path
                mqtt_topic = 'Enterprise' + tagPath.replace('[default]Enterprise', '')

                # Check if the tag's dataType is a DataSet
                if isinstance(tagValue, BasicDataset):
                    # Convert BasicDataset to a list of dictionaries
                    tagValue = convert_dataset_to_dict_list(tagValue)

                    # Log the converted dataset for debugging
                    log("Converted dataset for {}: {}".format(tagPath, tagValue))

                # Convert the tag value to a string to be used as MQTT payload
                try:
                    payload = json.dumps(tagValue)
                except Exception as e:
                    log("Failed to serialize tag value to JSON for {}: {}".format(tagPath, str(e)))
                    payload = str(tagValue)
                    continue

                # Publish the MQTT message using the Cirrus Link MQTT Transmission Module
                # Arguments: MQTT Server name, MQTT topic, payload, QoS, and retain flag
                system.cirruslink.transmission.publish("HiveMQ", str(mqtt_topic), str(payload), 0, 0)
                log("Published to {}: {}".format(mqtt_topic, payload))

            else:
                process_tags(tagPath)

    # Define the path where the tags are located
    root_path = '[default]Enterprise'

    # Call the function to start the process
    process_tags(root_path)

#publish_mqtt()