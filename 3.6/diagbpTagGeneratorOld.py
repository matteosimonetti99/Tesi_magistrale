#dì di lasciare vuoto fromTime e toTime if all day, codice da runnare ancora
def diagbp(diagbpPath, bpmnDictionary):
    import json
    from datetime import datetime

    def get_input(prompt):
        return input(prompt)
        
    def alias(name):
        aliases = {
            "processInstances": "Instances of the process"

            # Add more aliases here as needed
        }
        return aliases.get(name, name)

    def get_array_input(array_name, keys):
        array = []
        while True:
            element = {}
            for key in keys:
                if isinstance(key, list):
                    element[key[0]] = get_array_input(key[0], key[1:])
                elif isinstance(key, dict):
                    element[list(key.keys())[0]] = get_dict_input(list(key.keys())[0], key[list(key.keys())[0]])
                    if all(value == "" for value in element[list(key.keys())[0]].values()):
                        print("\n")
                        return array
                else:
                    value = get_input(f"Enter {alias(key)} for {alias(array_name)} (leave empty to go to next parameter group): ")
                    if value == "":
                        print("\n")
                        return array
                    element[key] = value
            array.append(element)

    def get_dict_input(dict_name, keys):
        dictionary = {}
        for key in keys:
            if isinstance(key, list):
                dictionary[key[0]] = get_array_input(key[0], key[1:])
            elif isinstance(key, dict):
                dictionary[list(key.keys())[0]] = get_dict_input(list(key.keys())[0], key[list(key.keys())[0]])
            else:
                value = get_input(f"Enter {alias(key)} for {alias(dict_name)} (leave empty to go to next parameter group): ")
                dictionary[key] = value
        return dictionary

    def get_datetime_input():
        date_str = get_input("Enter process start date in dd/mm/yyyy format: ")
        time_str = get_input("Enter process start time in hh:mm:ss format: ")
        datetime_str = f"{date_str} {time_str}"
        if not datetime_str.strip():
            # Return default date if datetime_str is empty
            default_date = datetime.now()
            return default_date.strftime("%Y-%m-%dT%H:%M:%S")
        datetime_obj = datetime.strptime(datetime_str, "%d/%m/%Y %H:%M:%S")
        return datetime_obj.strftime("%Y-%m-%dT%H:%M:%S")

    data = {
        "processInstances": get_array_input("processInstances", ["type", "count"]),
        "startDateTime": get_datetime_input(),
        "arrivalRateDistribution": get_dict_input("arrivalRateDistribution", ["type", "mean", "arg1", "arg2", "timeUnit"]),
        "timetables": get_array_input("timetables", ["name", {"rules": ["fromTime", "toTime", "fromWeekDay", "toWeekDay"]}]),
        "resources": get_array_input("resources", ["name", "totalAmount", "costPerHour", "timetableName"]),
        "elements": get_array_input("elements", ["worklistId", "elementId", "fixedCost", "costThreshold", {"durationDistribution": ["type", "mean", "arg1", "arg2", "timeUnit"]},
        "durationThreshold", "durationThresholdTimeUnit", ["resourceIds", {"resourceId": ["resourceName", "amountNeeded", "groupId"]}]]),
        "sequenceFlows": get_array_input("sequenceFlows", ["elementId", "executionProbability", {"types": ["type"]}])
    }

    with open(diagbpPath, 'w') as f:
        json.dump(data, f)