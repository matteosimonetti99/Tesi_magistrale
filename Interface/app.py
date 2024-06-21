from flask import Flask, render_template, request, send_from_directory
import os
import subprocess

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

            # Prepare Docker command with placeholders
            docker_cmd = [
                "docker", "run", "-it", "--rm", 
                "-v", f"{BPMN_FOLDER}:/app/bpmn_input_file_here", 
                "-v", f"{LOG_FOLDER}:/app/logs", 
                "-e", f"BPMN_ARG={uploaded_filename}",
                "diagbp"
            ]
            # Run Docker command and capture output
            consoleOutput = subprocess.run(docker_cmd, check=True, capture_output=True, text=True)
            return render_template('results.html', simulation_output=consoleOutput)

    return render_template('index.html')

@app.route('/download_logs')
def download_logs():
    logs_file = 'simulation_logs.txt'  # Adjust if your log file name is different
    return send_from_directory(app.config['LOGS_FOLDER'], logs_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')