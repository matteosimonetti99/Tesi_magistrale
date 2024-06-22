from flask import Flask, render_template, request, send_from_directory
import os
import subprocess
import zipfile


app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
LOGS_FOLDER = 'logs' # Directory for logs within the container
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LOGS_FOLDER'] = LOGS_FOLDER

# Create upload and logs folders if they don't exist, FORSE DA RIMUOVERE POI CON DOCKER
os.makedirs(UPLOAD_FOLDER, exist_ok=True) 
os.makedirs(LOGS_FOLDER, exist_ok=True)

APP_ROOT = os.path.dirname(os.path.abspath(__file__))  
BPMN_FOLDER = os.path.join(APP_ROOT, app.config['UPLOAD_FOLDER'])  # Relative to Flask app
LOG_FOLDER = os.path.join(APP_ROOT, app.config['LOGS_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        bpmn_file = request.files['bpmn_file']

        if bpmn_file:
            # Save uploaded BPMN
            bpmn_path = os.path.join(app.config['UPLOAD_FOLDER'], bpmn_file.filename)
            bpmn_file.save(bpmn_path)
            uploaded_filename = os.path.splitext(bpmn_file.filename)[0]
            return render_template('results.html')

    return render_template('index.html')

@app.route('/download_logs')
def download_logs():
    for filename in os.listdir(app.config['LOGS_FOLDER']):
        file_path = os.path.join(app.config['LOGS_FOLDER'], filename)
        if filename.endswith('.rar'):
            os.remove(file_path)
    # 1. Create the ZIP archive
    zip_filename = 'simulation_logs.zip'
    zip_path = os.path.join(app.config['LOGS_FOLDER'], zip_filename)
    if os.path.isfile(zip_path): 
        os.remove(zip_path)
    
    with zipfile.ZipFile(zip_path, 'w') as zf:
        for filename in os.listdir(app.config['LOGS_FOLDER']):
            if filename != zip_filename: # Don't add the zip itself
                file_path = os.path.join(app.config['LOGS_FOLDER'], filename)
                zf.write(file_path, arcname=filename)  # Add file to archive

    # 2. Send the ZIP file for download
    response = send_from_directory(app.config['LOGS_FOLDER'], zip_filename, as_attachment=True)

    return response 

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')