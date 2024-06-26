from flask import Flask, render_template, request, send_from_directory, redirect, url_for
import os
import subprocess
import zipfile
import time
import xml.etree.ElementTree as ET


app = Flask(__name__, template_folder='../templates')
JSON_FOLDER='../json'
UPLOAD_FOLDER = '../uploads'
PREUPLOAD_FOLDER = '../preupload'
LOGS_FOLDER = '../logs' # Directory for logs within the container
tagName = "diagbp"


# Create upload and logs folders if they don't exist, FORSE DA RIMUOVERE POI CON DOCKER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
os.makedirs(LOGS_FOLDER, exist_ok=True)
os.makedirs(PREUPLOAD_FOLDER, exist_ok=True)
os.makedirs(JSON_FOLDER, exist_ok=True)

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
        for filename in os.listdir(LOGS_FOLDER): # remove old log files
            file_path = os.path.join(LOGS_FOLDER, filename)
            os.remove(file_path)

        if bpmn_file:
            bpmn_path = os.path.join(UPLOAD_FOLDER, bpmn_file.filename)
            bpmn_file.save(bpmn_path)
            #check diagbp tag
            tree = ET.parse(bpmn_path)
            root = tree.getroot()
            diagbpTag = root.find('.//' + tagName)
            if diagbpTag is not None or extra: #se è presente o il tag nel file o l'extra.json file
                if extra:
                    extra_path = os.path.join(JSON_FOLDER, extra.filename)
                    extra.save(extra_path)
                # Save uploaded BPMN
                return redirect(url_for('results'))
            else:
                bpmn_path = os.path.join(PREUPLOAD_FOLDER, bpmn_file.filename)
                bpmn_file.save(bpmn_path)
                return redirect(url_for('parameters'))

    return render_template('index.html')

@app.route('/results')
def results():
    wait_for_and_remove_flag()
    return render_template('results.html')

@app.route('/parameters', methods=['GET', 'POST'])
def parameters():
    if request.method == 'POST':
        bpmn_filename = os.listdir(PREUPLOAD_FOLDER)[0]
        with open(os.path.join(PREUPLOAD_FOLDER, bpmn_filename), 'r') as f:
            bpmn_dict = json.load(f)
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

        # Process resources
        resource_count = int(request.form.get('resource_count', 0))
        for i in range(1, resource_count + 1):
            resource_name = request.form.get(f'resource_name_{i}')
            resource_amount = int(request.form.get(f'resource_amount_{i}'))
            resource_cost = float(request.form.get(f'resource_cost_{i}'))
            resource_timetable = request.form.get(f'resource_timetable_{i}')
            diagbp_data["resources"].append({
                "name": resource_name,
                "totalAmount": resource_amount,
                "costPerHour": resource_cost,
                "timetableName": resource_timetable
            })

        # Process timetables
        timetable_count = int(request.form.get('timetable_count', 0))
        for i in range(1, timetable_count + 1):
            timetable_name = request.form.get(f'timetable_name_{i}')
            timetable_rules = []
            rule_count = int(request.form.get(f'rule_count_{i}', 0))
            for j in range(1, rule_count + 1):
                from_time = request.form.get(f'rule_from_time_{i}_{j}')
                to_time = request.form.get(f'rule_to_time_{i}_{j}')
                from_day = request.form.get(f'rule_from_day_{i}_{j}')
                to_day = request.form.get(f'rule_to_day_{i}_{j}')
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
        diagbp_path = os.path.join(JSON_FOLDER, "diagbp.json")
        diagbp(diagbp_path, diagbp_data)
        
        source_path = os.path.join(PREUPLOAD_FOLDER, bpmn_filename)
        destination_path = os.path.join(UPLOAD_FOLDER, bpmn_filename)
        os.rename(source_path, destination_path)  

        return redirect(url_for('results'))

    return render_template('parameters.html')

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

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')