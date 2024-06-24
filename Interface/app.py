from flask import Flask, render_template, request, send_from_directory
import os
import subprocess
import zipfile
import time
import xml.etree.ElementTree as ET


app = Flask(__name__)
JSON_FOLDER='json'
UPLOAD_FOLDER = 'uploads'
PREUPLOAD_FOLDER = 'preupload'
LOGS_FOLDER = 'logs' # Directory for logs within the container
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
    if request.method == 'POST':
        bpmn_file = request.files['bpmn_file']
        extra = request.files['extra']
        for filename in os.listdir(LOGS_FOLDER): # remove old log files
            file_path = os.path.join(LOGS_FOLDER, filename)
            os.remove(file_path)
        #check diagbp tag
        tree = ET.parse(bpmn_file)
        root = tree.getroot()
        diagbpTag = root.find('.//' + tagName)

        if bpmn_file:
            if diagbpTag is not None or extra: #se è presente o il tag nel file o l'extra.json file
                if extra:
                    extra_path = os.path.join(JSON_FOLDER, extra.filename)
                    extra.save(extra_path)
                # Save uploaded BPMN
                bpmn_path = os.path.join(UPLOAD_FOLDER, bpmn_file.filename)
                bpmn_file.save(bpmn_path)
                uploaded_filename = os.path.splitext(bpmn_file.filename)[0]
                wait_for_and_remove_flag()                
                return render_template('results.html')
            else:
                bpmn_path = os.path.join(PREUPLOAD_FOLDER, bpmn_file.filename)
                bpmn_file.save(bpmn_path)
                return render_template('parameters.html')

    return render_template('index.html')

@app.route('/resultsAfterParam')
def resultsAfterParam():
    wait_for_and_remove_flag
    return render_template('results.html')

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