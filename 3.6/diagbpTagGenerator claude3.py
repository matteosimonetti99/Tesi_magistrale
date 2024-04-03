import json
from datetime import datetime

def get_input_array(name):
    arr = []
    while True:
        user_input = input(f"Enter {name} (or press Enter to stop): ")
        if not user_input:
            break
        arr.append(user_input)
    return arr

def get_input_dict(name, keys):
    d = {}
    for key in keys:
        d[key] = input(f"Enter {key} for {name}: ")
    return d

def convert_datetime(date_str, time_str):
    date = datetime.strptime(date_str, "%d/%m/%Y")
    time = datetime.strptime(time_str, "%H:%M:%S")
    return date.replace(hour=time.hour, minute=time.minute, second=time.second).isoformat() + "Z"

def create_json():
    data = {
        "processInstances": [],
        "startDateTime": None,
        "arrivalRateDistribution": None,
        "timetables": [],
        "resources": [],
        "elements": [],
        "sequenceFlows": []
    }

    # Process Instances
    while True:
        process_instance = get_input_dict("Process Instance", ["type", "count"])
        if not process_instance["type"]:
            break
        data["processInstances"].append(process_instance)

    # Start Date Time
    start_date = input("Enter start date (dd/mm/yyyy): ")
    start_time = input("Enter start time (hh:mm:ss): ")
    data["startDateTime"] = convert_datetime(start_date, start_time)

    # Arrival Rate Distribution
    data["arrivalRateDistribution"] = get_input_dict("Arrival Rate Distribution", ["type", "mean", "arg1", "arg2", "timeUnit"])

    # Timetables
    while True:
        timetable = get_input_dict("Timetable", ["name"])
        timetable["rules"] = []
        while True:
            rule = get_input_dict("Rule", ["fromTime", "toTime", "fromWeekDay", "toWeekDay"])
            if not rule["fromTime"]:
                break
            timetable["rules"].append(rule)
        if not timetable["name"]:
            break
        data["timetables"].append(timetable)

    # Resources
    while True:
        resource = get_input_dict("Resource", ["name", "totalAmount", "costPerHour", "timetableName"])
        if not resource["name"]:
            break
        data["resources"].append(resource)

    # Elements
    while True:
        element = get_input_dict("Element", ["worklistId", "elementId", "fixedCost", "costThreshold", "durationThreshold", "durationThresholdTimeUnit"])
        element["durationDistribution"] = get_input_dict("Duration Distribution", ["type", "mean", "arg1", "arg2", "timeUnit"])
        element["resourceIds"] = []
        while True:
            resource_id = get_input_dict("Resource ID", ["resourceName", "amountNeeded", "groupId"])
            if not resource_id["resourceName"]:
                break
            element["resourceIds"].append(resource_id)
        if not element["worklistId"]:
            break
        data["elements"].append(element)

    # Sequence Flows
    while True:
        sequence_flow = get_input_dict("Sequence Flow", ["elementId", "executionProbability"])
        sequence_flow["types"] = get_input_array("Type")
        if not sequence_flow["elementId"]:
            break
        data["sequenceFlows"].append(sequence_flow)

    return data

if __name__ == "__main__":
    json_data = create_json()
    with open("output.json", "w") as f:
        json.dump(json_data, f, indent=2)
    print("JSON file created successfully!")