@echo off
REM Change directory to the "3.6" folder
cd 3.6

REM Call the Python interpreter from your virtual environment
..\myenv\Scripts\python.exe bpmnParsing.py

REM Restore back to the original directory (optional)
cd ..

REM Pause to keep the command prompt window open (optional)
pause
