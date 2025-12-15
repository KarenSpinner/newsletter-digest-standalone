@echo off
REM use the digest tool to summarize my personal subscriptions
cls
echo KJS weekly digest generator starting at %date% %time%
echo Runs without Newsguard because it tends to flake out (resists bulk calls, maybe?)
call setDT.bat

if not exist logs mkdir logs
mkdir temp\%dt%
call venv_activate.bat

REM Solve encoding issues with special characters when logging to file in Windows
set PYTHONIOENCODING=utf_8

echo ******************************************************************************************************
if exist inputs\karensmiley-substack-subscriptions.csv goto proceed

echo Missing input file: inputs\karensmiley-substack-subscriptions.csv 
exit /b -1

:proceed
echo Using inputs\karensmiley-substack-subscriptions.csv

echo ******************************************************************************************************
echo KJS weekly digest starting at %date% %time%
echo . 7 day lookback, 10 featured, 10 wildcard, 7 retries, match names.
echo . Scoring choice 1 (standard), no normalization, show scores.
echo . Use Substack API, do not expand multiple authors in CSV file or HTML, verbose. 
echo . Save HTML and JSON to temp folder. 
python digest_generator.py -d7 -j -f10 -w10 -rt 7 -s1 -nn -u -v -c inputs\karensmiley-substack-subscriptions.csv -o outputs\%dt%_digest\ -oh . -oc . -t temp\%dt%\ >logs\%dt%_karensmiley-substack-subscriptions.log
echo SWAI HTML post and CSV for searchable digest finished with return status %errorlevel% at %date% %time%
call checklog.bat logs\%dt%_karensmiley-substack-subscriptions.log

echo Running S1 with normalization off
python digest_generator.py -d7 -j -f20 -w20 -ra -s1 -nn -c outputs\%dt%_digest\karensmiley-substack-subscriptions.digest7d_s1nN_a0.csv -o outputs\%dt%_digest\ -oh . >logs\%dt%_karensmiley-substack-subscriptions_reuse_s1nN.log
echo Finished with return status %errorlevel% at %date% %time%

echo Running S1 with normalization on
python digest_generator.py -d7 -j -f20 -w20 -ra -s1 -c outputs\%dt%_digest\karensmiley-substack-subscriptions.digest7d_s1nN_a0.csv -o outputs\%dt%_digest\ -oh . >logs\%dt%_karensmiley-substack-subscriptions_reuse_s1nY.log
echo Finished with return status %errorlevel% at %date% %time%

echo Running S2 with normalization off
python digest_generator.py -d7 -j -f20 -w20 -ra -s2 -nn -c outputs\%dt%_digest\karensmiley-substack-subscriptions.digest7d_s1nN_a0.csv -o outputs\%dt%_digest\ -oh . >logs\%dt%_karensmiley-substack-subscriptions_reuse_s2nN.log
echo Finished with return status %errorlevel% at %date% %time%

echo Running S2 with normalization on
python digest_generator.py -d7 -j -f20 -w20 -ra -s2 -c outputs\%dt%_digest\karensmiley-substack-subscriptions.digest7d_s1nN_a0.csv -o outputs\%dt%_digest\ -oh . >logs\%dt%_karensmiley-substack-subscriptions_reuse_s2nY.log
echo Finished with return status %errorlevel% at %date% %time%

dir logs\%dt%_*_log.txt
for %%f in (logs\%dt%_karensmiley*.log) do call checklog.bat %%f

call venv_deactivate.bat

echo KJS weekly digest generator finished
echo %date% %time%

exit /b 0