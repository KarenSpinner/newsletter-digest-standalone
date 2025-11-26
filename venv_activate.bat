@echo off
REM from CMD prompt window in the project folder where venv was created with command:
REM python -m venv ./venv

call venv\scripts\activate.bat

echo Virtual python environment at %CD% activated. Now running:
python -c "import sys; print(sys.executable)"

REM Be sure we point to the right Python for any PIP usage 
REM (need full path to prevent pip-audit complaints)
set PIPAPI_PYTHON_LOCATION=%CD%\venv\Scripts\python.exe

REM Prevent issues with logging UTF-8 output to a file
set PYTHONIOENCODING=utf_8

REM Remember to check environment for vulnerabilities regularly
REM (use run_pip_audit.bat >run_pip_audit.log)
REM echo Any vulnerabilities shown by pip-audit should be updated with further pip install --upgrade commands
