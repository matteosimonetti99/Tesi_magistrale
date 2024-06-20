from flask import Flask, render_template, request, send_from_directory
import os
import subprocess

app = Flask(__name__)
UPLOAD_FOLDER = 'uploads'
LOGS_FOLDER = 'logs' # Directory for logs within the container
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['LOGS_FOLDER'] = LOGS_FOLDER

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        bpmn_file = request.files['bpmn_file']
        parameters = request.form.get('parameters') 

        if bpmn_file:
            # Save uploaded BPMN
            bpmn_path = os.path.join(app.config['UPLOAD_FOLDER'], bpmn_file.filename)
            bpmn_file.save(bpmn_path)

            # Run the simulation using subprocess (adjust command as needed)
            subprocess.run(["docker", "exec", "python-app-container",  # Replace with your Python app container name
                            "python", "your_app.py", bpmn_path, parameters], 
                           check=True) 

            return render_template('results.html') 
    return render_template('index.html')

@app.route('/download_logs')
def download_logs():
    logs_file = 'simulation_logs.txt'  # Adjust if your log file name is different
    return send_from_directory(app.config['LOGS_FOLDER'], logs_file, as_attachment=True)

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')