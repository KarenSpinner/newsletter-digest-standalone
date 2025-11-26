@echo off
REM from CMD prompt window in the project folder where venv was created with command:
REM   python -m venv ./venv
REM To get the pip-audit results in a file, use run_pip_audit.bat >run_pip_audit.log.txt
REM The pip-audit option to redirect output to a file isn't working, for some reason.
REM The log file is always empty.

echo .
echo Activating virtual environment and setting PIP python location
call venv_activate.bat

echo .
echo Ensuring pip and pip-audit are installed and current
python.exe -m pip install --upgrade pip
pip.exe install --upgrade pip-audit

echo .
echo Checking installed packages for vulnerabilities
pip-audit.exe
set pip_result=%errorlevel%
echo .
echo pip-audit result (number of vulnerable packages): %pip_result%

REM pip-audit does not put "No vulnerabilities found" into the log file (stdout) for some reason.
REM It goes to the console regardless. So let's use echo to put it into the log file.

if     %pip_result%==0 echo pip-audit result: No vulnerabilities found. 
if not %pip_result%==0 echo pip-audit result: %pip_result% Vulnerable packages identified by pip-audit should be updated with further pip install --upgrade [packages] commands. 

call venv_deactivate.bat
exit /b %pip_result%