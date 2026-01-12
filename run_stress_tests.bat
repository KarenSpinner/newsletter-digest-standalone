@echo off

REM KJS 2025-12-12
REM This script takes several hours to run on a laptop computer with a fast internet connection.
REM
REM Results (HTML and CSV) and log files will be stored in a dated TESTS subfolder. 
REM Intermediate files (HTML and JSON) will be stored in a dated TEMP subfolder.
REM

cls

REM Prerequisites:
REM - digest_generator.py
REM - inputs\my_SWAI_newsletters.csv 
REM Use script_prep.bat to copy the latest versions to this scripts folder before running.
REM We make it fetch the latest version of the SWAI workbook from Google.
call script_prep.bat download

echo digest_generator.py STRESS tests starting at %date% %time%

call venv_activate.bat
call setDT.bat
mkdir tests\%dt%
mkdir temp\%dt%

echo ******************************************************************************************************
echo 0) Save the current runstring help to help_text.txt, and display version number here.
python digest_generator.py -h >tests\%dt%\help_text.txt
echo Test0 result: %errorlevel%
findstr " v1." tests\%DT%\help_text.txt

echo ******************************************************************************************************
echo STRESS1) Test with full SWAI newsletter list 500+, with no limit on articles per writer combo and newsletter. 
echo .  Use publisher name, go way back in time, and use daily average scoring without normalization. 
echo .  Save article data to CSV without expanding co-authors to multiple rows. 
echo .  20 featured, no wildcards, joint, show scores. Save HTML and JSON files to temp (v3 of some files from test6?).
echo . (This is the stress test for the largest possible file and max number of API calls. It takes several hours to fetch the data!)
set prefix=STRESS1_SWAI_newsletters_cats.digest2000d_a0jf20w20_s2nY
set inputf=stress_SWAI_newsletters_cats.csv
xcopy /Y inputs\my_SWAI_newsletters.csv tests\%dt%\%inputf%

python digest_generator.py -v -d2000 -s2 -nn -f20 -w20 -rt 10 -u -j -cc -t temp\%dt% -oh tests\%dt%\%prefix%.html -oc tests\%dt%\%prefix%.csv -c inputs\%inputf% >tests\%dt%\%prefix%.log

echo STRESS1 finished at %date% %time% with result: %errorlevel%
call checklog.bat tests\%dt%\%prefix%.log
echo .

echo TO DO: Use the file we just created and execute a battery of reuse tests with different output options
echo combinations. (Put these in a separate script so we can use them on ANY file, not wait on this one.)


echo ******************************************************************************************************
call venv_deactivate.bat

dir tests\%dt%\test*.*.log
for %%f in (tests\%dt%\test*.*.log) do call checklog.bat %%f

echo .
echo digest_generator.py regression tests finished at %date% %time%
echo Check results in tests\%dt%*.log and digest output files in tests\%dt%\

exit /b 0