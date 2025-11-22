@echo off

REM KJS 2025-11-21
REM This script takes about 30 min to run on a laptop computer with a fast internet connection.
REM Note that this script does not (yet) include regression tests for the reuse of the article CSVs.
REM
REM Also note that this script reuses the same %dt%-named folder for temp for all runs. HTML and JSON
REM files created in earlier tests in this run might be overwritten. To prevent any overwriting, call 
REM setDT.bat before each program execution, so each run has its own timestamped folder. Or put test*
REM into the folder name, to avoid any issues if e.g. test1 and test2 execute within the same minute
REM and both save temp files (but right now, test1 doesn't save anything to temp, so it's safe).

REM This script uses a subfolder 'inputs' with the following files:
REM   my_newsletters.csv
REM   kjs_newsletters.csv
REM   smiley_newsletters.csv
REM   2025-11-21_my_SWAI_newsletters.csv 
REM Results (HTML and CSV) and log files will be stored in a dated TESTS subfolder. 
REM Intermediate files (HTML and JSON) will be stored in a dated TEMP subfolder.

echo digest_generator.py regression tests starting at %date% %time%

call venv_activate.bat
call setDT.bat
mkdir tests\%dt%
mkdir temp\%dt%

python digest_generator.py -h >tests\%DT%\help_text.txt

echo 1) Run with all defaults: csv_path, output HTML filename, HTML metrics, no article CSV file, all other basic options.
copy my_newsletters.csv tests\%dt%\my_newsletters.csv
cd tests\%dt%
python ..\..\digest_generator.py >my_newsletters.test1.digest_defaults.log
ren my_newsletters.csv my_newsletters.test1.csv
ren my_newsletters.digest7d_s1nY_m0.*.f5w1.html my_newsletters.test1.digest7d_s1nY_m0.*.f5w1.html
cd ..\..

echo 2) Repeat with Substack API calls for metrics (default HTML file only, no article CSV). Save JSONs to temp folder.
copy my_newsletters.csv tests\%dt%\my_newsletters.test2.csv
python digest_generator.py -v -u -t temp\%dt% -c tests\%dt%\my_newsletters.test2.csv >tests\%dt%\my_newsletters.test2.digest_substack_metrics.log

REM Use default output naming on test3, specify filenames on test4
echo 3) Run with my 3 newsletters only, 1000 days with standard scoring, Substack API, no normalization, 0 featured, 0 wildcards. Save article data to CSV and save HTMLs to temp.
copy inputs\kjs_newsletters.csv       tests\%dt%\kjs_newsletters.test3.csv
python digest_generator.py -v -d 1000 -s 1 -nn -f 0 -w 0 -u -oc . -t temp\%dt% -c tests\%dt%\kjs_newsletters.test3.csv  >tests\%dt%\kjs_newsletters.test3.digest1000d_s1nN_f0w20.log

echo 4) Run with my 3 newsletters only, 1000 days with daily average scoring, no wildcards. Save article data to CSV. HTML metrics only, no temp files.
copy inputs\kjs_newsletters.csv       tests\%dt%\kjs_newsletters.test4.csv
python digest_generator.py -v -d 1000 -s 2 -nn -f 20 -w 0 -c tests\%dt%\kjs_newsletters.test4.csv -oh tests\%dt%\kjs_newsletters.test4.digest1000d_s2nN_f20w0.html -oc tests\%dt%\kjs_newsletters.test4.digest1000d_s2nN.csv >tests\%dt%\kjs_newsletters.test4.digest1000d_s2nN.log

echo 5) Test with no category column and ignore author name matching even though Author column is present.
echo .  Save articles to CSV. No temp files.
copy tests\smiley_newsletter_tests.csv tests\%dt%\smiley_newsletters.test5.csv
python digest_generator.py -v -d 30 -nm -oc . -c tests\%dt%\smiley_newsletters.test5.csv >tests\%dt%\smiley_newsletters.test5.digest30d_a0_nm.log

echo 6) Test with full categorized SWAI newsletter list 500+, weekly digest with standard scoring, no normalization,
echo .  no max per author. Save article data to CSV and save HTML and JSON files to temp.
copy inputs\2025-11-21_my_SWAI_newsletters.csv tests\%dt%\SWAI_newsletters_cats.test67.csv
python digest_generator.py -v -nn -rt 7 -u -t temp\%dt% -c tests\%dt%\SWAI_newsletters_cats.test67.csv -oh tests\%dt%\SWAI_newsletters_cats.test6.digest7d_a0_s1nN_f5w1.%dt%.html -oc tests\%dt%\SWAI_newsletters_cats.test6.digest7d_a0_s1nN.csv >tests\%dt%\SWAI_newsletters_cats.test6.digest7d_a0_s1nN_f5w1.log

echo 7) Test with full SWAI newsletter list 500+, but fetch only one l article per writer and newsletter, go way back in time, and use daily average scoring. Save article data to CSV and save HTML files to temp (no JSON).
python digest_generator.py -v -d 2000  -a 1 -s 2 -rt 7 -t temp\%dt% -oh . -oc . -c tests\%dt%\SWAI_newsletters_cats.test67.csv >tests\%dt%\SWAI_newsletters_cats.test7.digest2000d_a1_s2nY.log
ren tests\%dt%\SWAI_newsletters_cats.test67.digest*.* SWAI_newsletters_cats.test7.digest*.*

call venv_deactivate.bat

dir tests\%dt%\*.test*.*.log

echo digest_generator.py regression tests finished at %date% %time%
echo Check results in tests\%dt%*.log and digest output files

exit /b 0