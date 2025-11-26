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

echo ******************************************************************************************************
echo Save the current runstring help to help_text.txt
python digest_generator.py -h >tests\%DT%\help_text.txt

echo ******************************************************************************************************
echo 1) Run with all defaults: csv_path, output HTML filename, HTML metrics, no article CSV file, all other basic options.
python digest_generator.py -o tests\%dt%\test1 >tests\%dt%\test1_my_newsletters.digest_defaults.log
copy my_newsletters.csv tests\%dt%\test1\my_newsletters.csv

echo ******************************************************************************************************
echo 2) Repeat with Substack API calls for metrics and co-authors. 
echo .  (default HTML file and article CSV; put timestamp into filename).
echo .  Save JSONs and HTMLs to test2 subfolder in temp\%dt%.
copy my_newsletters.csv tests\%dt%\test2_my_newsletters.csv
python digest_generator.py -v -u -t temp\%dt%\test2 -oc . -oh . -ts -c tests\%dt%\test2_my_newsletters.csv >tests\%dt%\test2_my_newsletters.digest_substack_metrics.log

echo ******************************************************************************************************
REM Use default output naming on test3, specify filenames on test4
echo 3) Run with my 3 newsletters only, 1000 days with standard scoring, no normalization.
echo .  Use Substack API to get restacks and co-authors.
echo .  Request 0 featured, 3 wildcards (shouldn't get any, though). 
echo .  Save article data to CSV and save HTMLs and JSON files to subfolder test3 in temp\%dt%.
copy inputs\kjs_newsletters.csv tests\%dt%\test3_kjs_newsletters.csv
python digest_generator.py -v -d 1000 -s 1 -nn -f 0 -w 0 -u -oc . -t temp\%dt%\test3 -c tests\%dt%\test3_kjs_newsletters.csv  >tests\%dt%\test3_kjs_newsletters.digest1000d_s1nN_f0w20.log

echo ******************************************************************************************************
echo 4) Repeat with my 3 newsletters only, 1000 days with daily average scoring, no wildcards.
echo .  Save article data to CSV. HTML metrics only, no restacks and no co-authors. No author name matching.
echo .  (Should pull in 1 article Lakshmi wrote in AI6P without my byline, if within the 20 in RSS?)
echo .  Use new output folder test4 and default naming for HTML and CSV outputs. No temp files saved. 
copy inputs\kjs_newsletters.csv       tests\%dt%\test4_kjs_newsletters.csv
python digest_generator.py -v -d1000 -s2 -nm -nn -f20 -w0 -oh . -oc . -c tests\%dt%\test4_kjs_newsletters.csv -o tests\%dt%\test4 >tests\%dt%\test4_kjs_newsletters.digest1000d_s2nN.log

echo ******************************************************************************************************
echo 5) 30-day test with Substack API for restacks and co-authors, Author matching, no categories.
echo .  Use Publisher name as default if no byline.
echo .  Save articles to CSV with expanded author names. No temp files.
copy inputs\smiley_newsletters.csv tests\%dt%\test5_smiley_newsletters.csv
python digest_generator.py -v -d30 -u -xma -oc . -c tests\%dt%\test5_smiley_newsletters.csv >tests\%dt%\test5_smiley_newsletters.digest30d_a0_nm.log

echo ******************************************************************************************************
echo 6) Test with full categorized SWAI newsletter list 500+, weekly digest with 10 featured and 10 wildcards,
echo .  using standard scoring, no normalization, no max per author, publisher name available.
echo .  Save article data to CSV and save HTML and JSON files to temp.
copy inputs\my_SWAI_newsletters.csv tests\%dt%\test67_SWAI_newsletters_cats.csv
python digest_generator.py -v -s1 -nn -f10 -w10 -rt 7 -u -t temp\%dt% -o tests\%dt%\test6 -oh . -oc . -c tests\%dt%\test67_SWAI_newsletters_cats.csv >tests\%dt%\test6_SWAI_newsletters_cats.digest7d_a0_s1nN_f5w1.log

echo ******************************************************************************************************
echo 7) Test with full SWAI newsletter list 500+, but fetch only one l article per writer and newsletter, 
echo .  publisher name available, go way back in time, and use daily average scoring without normalization. 
echo .  0 featured, no wildcards. Fetch one row per writer+newsletter, save article data to CSV with 
echo .  co-authors expanded to multiple rows, and save HTML and JSON files to temp (2nd version of some files from test6).
echo . (This CSV output is used to update the latest article per author in the SheWritesAI directory.)
python digest_generator.py -v -d2000 -a1 -s2 -nn -f0 -w0 -rt 7 -u -t temp\%dt% -oh . -oc . -xma -c tests\%dt%\test67_SWAI_newsletters_cats.csv >tests\%dt%\test7_SWAI_newsletters_cats.digest2000d_a1_s2nY.log
ren tests\%dt%\test67_SWAI_newsletters_cats.digest*.* test7_SWAI_newsletters_cats.digest*.*

echo ******************************************************************************************************
call venv_deactivate.bat

dir tests\%dt%\test*.*.log

echo digest_generator.py regression tests finished at %date% %time%
echo Check results in tests\%dt%*.log and digest output files

exit /b 0