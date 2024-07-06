from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import subprocess
import zipfile
import time
import xml.etree.ElementTree as ET
import json


app = Flask(__name__, template_folder='../templates', static_folder='../static')
JSON_FOLDER='../json'
DOWNLOAD_FOLDER='../download'
UPLOAD_FOLDER = '../uploads'
PREUPLOAD_FOLDER = '../preupload'
LOGS_FOLDER = '../logs' # Directory for logs within the container
tagName = "diagbp"


# Create upload and logs folders if they don't exist, FORSE DA RIMUOVERE POI CON DOCKER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
os.makedirs(LOGS_FOLDER, exist_ok=True)
os.makedirs(PREUPLOAD_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

def wait_for_and_remove_flag():
    # Wait for 'flag.txt' to appear in 'uploads' folder, created by main.py after simulation is over
    flag_path = os.path.join(UPLOAD_FOLDER, "flag.txt")
    while not os.path.exists(flag_path):
        time.sleep(1) 
    try:
        os.remove(flag_path) 
        print("Flag file removed successfully.")
    except OSError as e:
        print(f"Error removing flag file: {e}")


@app.route('/', methods=['GET', 'POST'])
def index():
    for filename in os.listdir(PREUPLOAD_FOLDER): # remove old log files
        file_path = os.path.join(PREUPLOAD_FOLDER, filename)
        os.remove(file_path)
    for filename in os.listdir(DOWNLOAD_FOLDER): # remove old log files
        file_path = os.path.join(DOWNLOAD_FOLDER, filename)
        os.remove(file_path)
    for filename in os.listdir(LOGS_FOLDER): # remove old log files
        file_path = os.path.join(LOGS_FOLDER, filename)
        os.remove(file_path)
    for filename in os.listdir(JSON_FOLDER): # remove old log files
        file_path = os.path.join(JSON_FOLDER, filename)
        os.remove(file_path)
    
    try:
        flag_path = os.path.join(UPLOAD_FOLDER, "flag.txt")
        if os.path.exists(flag_path):
            os.remove(flag_path) 
            print("Flag file removed successfully.")
    except OSError as e:
        print(f"Error removing flag file: {e}")

    if request.method == 'POST':
        bpmn_file = request.files['bpmn_file']
        extra = request.files['extra']

        if bpmn_file:
            bpmn_path = os.path.join(PREUPLOAD_FOLDER, bpmn_file.filename)
            bpmn_file.save(bpmn_path)
            bpmn_file.seek(0)  

            #check diagbp tag
            tree = ET.parse(bpmn_path)
            root = tree.getroot()
            diagbpTag = root.find('.//' + tagName)
            if diagbpTag is not None or extra: #se è presente o il tag nel file o l'extra.json file
                if extra:
                    extra_path = os.path.join(JSON_FOLDER, "extra.json")
                    extra.save(extra_path)
                # Save uploaded BPMN
                bpmn_path = os.path.join(UPLOAD_FOLDER, bpmn_file.filename)
                bpmn_file.save(bpmn_path)
                os.remove(os.path.join(PREUPLOAD_FOLDER, bpmn_file.filename)) 
                return redirect(url_for('results'))
            else:
                bpmn_path = os.path.join(UPLOAD_FOLDER, bpmn_file.filename) #save in upload so that simulator reads it and creates bpmn.json for parameters.html
                bpmn_file.save(bpmn_path)
                wait_for_and_remove_flag()
                return redirect(url_for('parameters'))

    return render_template('index.html')

@app.route('/results')
def results():
    wait_for_and_remove_flag()
    return render_template('results.html')

@app.route('/parameters', methods=['GET', 'POST'])
def parameters():
    bpmn_filename = os.listdir(PREUPLOAD_FOLDER)[0]
    with open(os.path.join(JSON_FOLDER, "bpmn.json"), 'r') as f:
        bpmn_dict = json.load(f)
    if request.method == 'POST':
        diagbp_data = {
            "processInstances": [],
            "startDateTime": request.form.get('start_date'),
            "arrivalRateDistribution": {
                "type": request.form.get('inter_arrival_time_type'),
                "mean": request.form.get('inter_arrival_time_mean'),
                "arg1": request.form.get('inter_arrival_time_arg1'),
                "arg2": request.form.get('inter_arrival_time_arg2'),
                "timeUnit": request.form.get('inter_arrival_time_time_unit'),
            },
            "timetables": [],
            "resources": [],
            "elements": [],
            "sequenceFlows": [],
            "catchEvents": {}
        }

        # Process instance types
        for key, value in request.form.items():
            if key.startswith('instance_type_'):
                instance_type = value
                instance_count_key = key.replace('instance_type_', 'instance_count_')
                instance_count = int(request.form.get(instance_count_key))

                diagbp_data["processInstances"].append({
                    "type": instance_type,
                    "count": instance_count
                })

        # Process resources
        for key, value in request.form.items():
            if key.startswith('resource_name_'):
                resource_name = value
                resource_amount_key = key.replace('resource_name_', 'resource_amount_')
                resource_cost_key = key.replace('resource_name_', 'resource_cost_')
                resource_timetable_key = key.replace('resource_name_', 'resource_timetable_')

                resource_amount = int(request.form.get(resource_amount_key))
                resource_cost = float(request.form.get(resource_cost_key))
                resource_timetable = request.form.get(resource_timetable_key)

                diagbp_data["resources"].append({
                    "name": resource_name,
                    "totalAmount": resource_amount,
                    "costPerHour": resource_cost,
                    "timetableName": resource_timetable
                })
               
        # Timetables
        for key, value in request.form.items():
            if key.startswith('timetable_name_'):
                timetable_name = value
                timetable_rules = []

                # Find rules related to this timetable
                for rule_key, rule_value in request.form.items():
                    if rule_key.startswith(f'rule_from_time_{key.split("_")[2]}_'):
                        rule_index = rule_key.split("_")[3]  # Extract rule index
                        from_time = rule_value
                        to_time = request.form.get(f'rule_to_time_{key.split("_")[2]}_{rule_index}')
                        from_day = request.form.get(f'rule_from_day_{key.split("_")[2]}_{rule_index}')
                        to_day = request.form.get(f'rule_to_day_{key.split("_")[2]}_{rule_index}')

                        timetable_rules.append({
                            "fromTime": from_time,
                            "toTime": to_time,
                            "fromWeekDay": from_day,
                            "toWeekDay": to_day
                        })

                diagbp_data["timetables"].append({
                    "name": timetable_name,
                    "rules": timetable_rules
                })

        # Process elements (example, needs to be adapted to your BPMN)
        for element_id in bpmn_dict['process_elements']:
            # Get element data from BPMN or form (example)
            element_name = element_id  
            diagbp_data["elements"].append({
                "elementId": element_id,
                "worklistId": "default_worklist",  
                "fixedCost": "0",  
                "costThreshold": "0",
                "durationDistribution": {
                    "type": "FIXED",  
                    "mean": "10",  
                    "arg1": "",
                    "arg2": "",
                    "timeUnit": "seconds" 
                },
                "durationThreshold": "0",
                "durationThresholdTimeUnit": "seconds",
                "resourceIds": []  
            })

        source_path = os.path.join(PREUPLOAD_FOLDER, bpmn_filename)
        destination_path = os.path.join(UPLOAD_FOLDER, bpmn_filename)
        
        #Write to upload folder so that diagbp can simulate it
        with open(destination_path, 'w') as file:
            bpmn_content = bpmn_dict.replace('</bpmn:definitions>', f'<diagbp>{diagbp_data}</diagbp>\n</bpmn:definitions>')
            file.write(bpmn_content)
        
        #Remove file from preupload folder
        os.remove(source_path)    

        return redirect(url_for('results'))

    return render_template('parameters.html', bpmn_dict=bpmn_dict)

@app.route('/download_logs')
def download_logs():
    # 1. Create the ZIP archive
    zip_filename = 'simulation_logs.zip'
    zip_path = os.path.join(LOGS_FOLDER, zip_filename)
    if os.path.isfile(zip_path): 
        os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for filename in os.listdir(LOGS_FOLDER):
            if filename != zip_filename: # Don't add the zip itself
                file_path = os.path.join(LOGS_FOLDER, filename)
                zf.write(file_path, arcname=filename)  # Add file to archive

    # 2. Send the ZIP file for download
    response = send_from_directory(LOGS_FOLDER, zip_filename, as_attachment=True)

    return response 

@app.route('/download_bpmn_with_parameters')
def download_bpmn_with_parameters():
    for filename in os.listdir(DOWNLOAD_FOLDER):
        if filename.endswith('.bpmn'):
            return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    return "BPMN file not found", 404

@app.route('/download_extra_json')
def download_extra_json():
    for filename in os.listdir(DOWNLOAD_FOLDER):
        if filename.endswith('.json'):
            return send_from_directory(DOWNLOAD_FOLDER, filename, as_attachment=True)
    return "JSON file not found", 404

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')