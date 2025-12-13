@echo off

echo Weekly SWAI digest generator starting at %date% %time%
call setDT.bat

if not exist logs mkdir logs
mkdir temp\%dt%
call venv_activate.bat

REM Solve encoding issues with special characters when logging to file in Windows
set PYTHONIOENCODING=utf_8

echo ******************************************************************************************************
echo Fetching latest 'activity' worksheet from the Google Sheets workbook
if exist inputs\%date%_my_swai_newsletters-backup.csv del inputs\%date%_my_swai_newsletters-backup.csv
if exist inputs\my_swai_newsletters.csv ren inputs\my_swai_newsletters.csv %date%_my_swai_newsletters-backup.csv

python export_public_sheet_to_csv.py
set download_result=%errorlevel%
if "%download_result%"=="0" goto proceed

echo Error %download_result% retrieving activity worksheet from Google
exit /b %download_result%

:proceed

echo ******************************************************************************************************
echo SWAI weekly digest starting at %date% %time%
echo . 7 day lookback, 10 featured, 10 wildcard, 7 retries, match most names.
echo . Scoring choice 1 (standard), no normalization, hide scores.
echo . Use Substack API, do not expand multiple authors in CSV file or HTML, verbose. 
echo . Save HTML and JSON to temp folder. 
python digest_generator.py -d7 -j -f10 -w10 -rt 7 -s1 -nn -hs -u -v -c inputs\my_SWAI_newsletters.csv -o outputs\%dt%_digest\ -oh . -oc . -t temp\%dt%\ >logs\%dt%_SWAI_newsletter_digest_log.txt
echo SWAI HTML post and CSV for searchable digest finished with return status %errorlevel% at %date% %time%
dir outputs\%dt%_digest\my_swai_newsletters*.* /o-d
call checklog.bat logs\%dt%_SWAI_newsletter_digest_log.txt

echo ******************************************************************************************************
echo Creating a collapsed version of the HTML page too, with scores shown (my use only)
echo . Specify the full HTML filename desired
python digest_generator.py -j -f10 -w10 -cc -v -ra -c outputs\%dt%_digest\my_SWAI_newsletters.digest7d_s1nN_a0.csv -oh outputs\%dt%_digest\SWAI_newsletter_reuse_page_collapsed.html >logs\%dt%_SWAI_newsletter_reuse_log.txt
echo SWAI alternate HTML page finished with return status %errorlevel% at %date% %time%
dir outputs\%dt%_digest\*reuse*.* /o-d
call checklog.bat logs\%dt%_SWAI_newsletter_reuse_log.txt

echo ******************************************************************************************************
echo SWAI weekly directory link update starting at %date% %time%
echo . Max=1 per author+newsletter, 2000 day lookback, match most names, expand multiple co-authors.
echo . 0 featured, 0 wildcard, scoring choice 1 (standard), no normalization, do not hide scores, 
echo . Use Substack API, 7 retries, verbose. Make digest page category sections collapsible.
echo . Save HTML and JSON to the same dated temp folder. 
python digest_generator.py -a1 -d2000 -xma -f0 -w0 -s1 -nn -u -rt 7 -cc -v -c inputs\my_SWAI_newsletters.csv -o outputs\%dt%_directory_updates\ -oh . -oc . -t temp\%dt%\ >logs\%dt%_SWAI_directory_update_log.txt
echo SWAI directory link update finished with return status %errorlevel% at %date% %time%
call checklog.bat logs\%dt%_SWAI_directory_update_log.txt

dir outputs\%dt%_directory_updates\my_swai_newsletters*.* /o-d

dir logs\%dt%_*_log.txt
for %%f in (logs\%dt%_*_log.txt) do call checklog.bat %%f

call venv_deactivate.bat

echo Weekly SWAI digest generator finished
echo %date% %time%

exit /b 0