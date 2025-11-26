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
python digest_generator.py -d 7 -f 10 -w 10 -rt 7 -s 1 -nn -hs -u -xma -v -c inputs\my_SWAI_newsletters.csv -oh outputs\%dt%_swai_newsletters-digest.html -oc outputs\%dt%_swai_newsletters-digest.csv -t temp\%dt%\ >logs\%dt%_swai_newsletters-digest_log.txt
echo CSV for searchable digest finished with return status %errorlevel% at %date% %time%

echo Running SWAI digest for directory update with max 1 per author+newsletter, 2000 day lookback, match names.
echo 0 featured, 0 wildcard, scoring choice 1 (standard), no normalization, hide scores, 
echo use Substack API, 7 retries, verbose. Save HTML and JSON to the same dated temp folder. 
python digest_generator.py -a 1 -d 2000 -f 0 -w 0 -rt 7 -s 1 -nn -hs -u -v -c inputs\my_SWAI_newsletters.csv -oh outputs\%dt%_swai_newsletters-directory_updates.html -oc outputs\%dt%_swai_newsletters-directory_updates.csv -t temp\%dt%\ >logs\%dt%_swai_newsletters-directory_updates_log.txt
echo Directory update feed links finished with return status %errorlevel% at %date% %time%

dir outputs\%dt%_swai_newsletters*.* /o-d

dir logs\%dt%_swai_newsletters*_log.txt

call venv_deactivate.bat

echo Weekly SWAI digest generator finished
echo %date% %time%

exit /b 0