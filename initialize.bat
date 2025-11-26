REM one-time setup of virtual environment for SWAI digest data tools

python -m venv ./venv
call venv_activate.bat

REM python --version
python -m pip install --upgrade pip
if EXIST requirements.txt venv\scripts\pip install -r requirements.txt
if NOT EXIST requirements.txt echo No requirements file found for installing packages.

REM setuptools update seems to be needed in default environment, and it isn't in requirements.txt even after a fresh freeze
pip install --upgrade setuptools

echo Using run_pip_audit.bat >run_pip_audit.log to check for security vulnerabilities in your new environment.
run_pip_audit.bat >run_pip_audit.log

call venv_deactivate.bat

echo Use venv_activate.bat to enable this new environment when you want to use it
echo Use venv_deactivate.bat when you are done

exit /b 0