REM @echo off

echo Weekly SWAI digest generator starting at %date% %time%
call setDT.bat

if not exist logs mkdir logs
mkdir temp\%dt%
call venv_activate.bat
@echo on
REM TO DO: Add step that fetches the latest list of newsletters from the SWAI directory

REM Solve encoding issues with special characters when logging to file in Windows
set PYTHONIOENCODING=utf_8

echo Running SWAI weekly digest with 7 day lookback, 10 featured, 10 wildcard, 7 retries, scoring choice 1 (standard), 
echo no normalization, hide scores, use Substack API, verbose. Save HTML and JSON to temp folder. 
python digest_generator.py -d 7 -f 10 -w 10 -m -r 7 -s 1 -nn -hs -u -v -c inputs\2025-11-21_my_SWAI_newsletters.csv -oh outputs\%dt%_swai_newsletters-digest.html -oc outputs\%dt%_swai_newsletters-digest.csv -t temp\%dt%\ >logs\%dt%_swai_newsletters-digest_log.txt

dir outputs\%dt%_swai_newsletters-digest*.* /o-d

dir logs\%dt%_swai_newsletters-digest_log.txt

call venv_deactivate.bat

echo Weekly SWAI digest generator finished
echo %date% %time%

exit /b 0