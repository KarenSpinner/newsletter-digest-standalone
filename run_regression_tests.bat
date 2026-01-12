@echo off

REM KJS 2025-11-21
REM This script takes about 30 min to run on a laptop computer with a fast internet connection.
REM KJS 2025-11-30 Add regression test for reuse of an article CSV output file.
REM
REM Results (HTML and CSV) and log files will be stored in a dated TESTS subfolder. 
REM Intermediate files (HTML and JSON) will be stored in a dated TEMP subfolder.
REM
REM Note that this script can reuse the same %dt%-named folder for temp for all runs. The program no longer 
REM overwrites existing HTML and JSON files that already exist (e.g. were created in earlier tests in this run.)
REM Each run has its own subfolder in the timestamped temp folder. Exception: Tests 6 & 7 deliberately use 
REM the same temp\%dt% folder to validate that the file naming for uniqueness works as intended (up to 9 times).

cls

REM Prerequisites:
REM - digest_generator.py
REM - inputs\my_newsletters.csv
REM - inputs\kjs_newsletters.csv
REM - inputs\smiley_newsletters.csv
REM - inputs\my_SWAI_newsletters.csv 
REM Use script_prep.bat to copy the latest versions to this scripts folder before running.
REM It will optionally fetch the latest version of the SWAI workbook from Google.
call script_prep.bat download

echo digest_generator.py regression tests starting at %date% %time%

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
echo 1) Run with most defaults: csv_path, output HTML, no metrics API, no article CSV, all basic options.
echo .  Not verbose. Only runstring option used is to set output folder to tests\%dt%\test1\.
python digest_generator.py -o tests\%dt%\test1 >tests\%dt%\test1_my_newsletters.digest_defaults.log
echo Test1 result: %errorlevel%
call checklog.bat tests\%dt%\test1_my_newsletters.digest_defaults.log
copy my_newsletters.csv tests\%dt%\test1\my_newsletters.csv
echo .

echo ******************************************************************************************************
echo 2) Repeat with Substack API calls, for metrics (restacks) and co-authors. 
echo .  Default HTML file and article CSV in same folder as input; put timestamps into filenames. 
echo .  Save JSONs and HTMLs to subfolder temp\%dt%\test2\.
copy my_newsletters.csv tests\%dt%\test2_my_newsletters.csv
python digest_generator.py -v -u -t temp\%dt%\test2 -oc . -oh . -ts -c tests\%dt%\test2_my_newsletters.csv >tests\%dt%\test2_my_newsletters.digest_substack_metrics.log
echo Test2 result: %errorlevel%
call checklog.bat tests\%dt%\test2_my_newsletters.digest_substack_metrics.log
echo .

echo ******************************************************************************************************
REM Use default output naming on test3, specify filenames on test4
echo 3) Run with my 3 newsletters only, 1000 days with standard scoring, no normalization.
echo .  Use Substack API to get restacks and co-authors.
echo .  Request 0 featured, 3 wildcards (shouldn't get any, though). 
echo .  Save article data to CSV and save HTML and JSON files to subfolder temp\%dt%\test3\.
copy inputs\kjs_newsletters.csv tests\%dt%\test3_kjs_newsletters.csv
python digest_generator.py -v -d1000 -s1 -nn -f0 -w0 -u -o tests\%dt%\test3 -oc . -t temp\%dt%\test3 -c tests\%dt%\test3_kjs_newsletters.csv  >tests\%dt%\test3_kjs_newsletters.digest1000d_s1nN_f0w20.log
echo Test3 result: %errorlevel%
call checklog.bat tests\%dt%\test3_kjs_newsletters.digest1000d_s1nN_f0w20.log
echo .

echo ******************************************************************************************************
echo 4) Repeat with my 3 newsletters only, 1000 days with daily average scoring, 1 per author, no wildcards.
echo .  Save article data to CSV. HTML metrics only, no restacks and no co-authors. No author name matching.
echo .  (Should pull in 1 article Lakshmi wrote in AI6P without my byline, if within the 20 in RSS?)
echo .  Use new output folder test4 and default naming for HTML and CSV outputs. No temp files saved. 
copy inputs\kjs_newsletters.csv       tests\%dt%\test4_kjs_newsletters.csv
python digest_generator.py -v -a1 -d1000 -s2 -nm -nn -f20 -w0 -oh . -oc . -c tests\%dt%\test4_kjs_newsletters.csv -o tests\%dt%\test4 >tests\%dt%\test4_kjs_newsletters.digest1000d_s2nN.log
echo Test4 result: %errorlevel%
call checklog.bat tests\%dt%\test4_kjs_newsletters.digest1000d_s2nN.log
echo .

echo ******************************************************************************************************
echo 5) 30-day test with Substack API for restacks, co-authors, joint articles, Author matching, no categories.
echo .  Use Publisher name as default if no byline.
echo .  Save articles to CSV with expanded author names. No temp files.
copy inputs\smiley_newsletters.csv tests\%dt%\test5_smiley_newsletters.csv
python digest_generator.py -v -d30 -u -xma -j -o tests\%dt%\test5 -oc . -c tests\%dt%\test5_smiley_newsletters.csv >tests\%dt%\test5_smiley_newsletters.digest30d_a0j_nm.log
echo Test5 result: %errorlevel%
call checklog.bat tests\%dt%\test5_smiley_newsletters.digest30d_a0j_nm.log
echo .

echo ******************************************************************************************************
echo 6) Test with full categorized SWAI newsletter list 500+, weekly digest with 10 featured and 10 wildcards,
echo .  using standard scoring, no normalization, no max per author, publisher name available.
echo .  Create a separate category for any jointly authored articles (collaborations).
echo .  Save article data to CSV and save HTML and JSON files to temp.
copy inputs\my_SWAI_newsletters.csv tests\%dt%\test67_SWAI_newsletters_cats.csv
python digest_generator.py -v -s1 -nn -f10 -w10 -rt 7 -u -j -t temp\%dt% -o tests\%dt%\test6 -oh . -oc . -c tests\%dt%\test67_SWAI_newsletters_cats.csv >tests\%dt%\test6_SWAI_newsletters_cats.digest7d_a0_s1nN_jf5w1.log
echo Test6 result: %errorlevel%
call checklog.bat tests\%dt%\test6_SWAI_newsletters_cats.digest7d_a0_s1nN_jf5w1.log
echo .

echo ******************************************************************************************************
echo 7) Test with full SWAI newsletter list 500+, but fetch only one l article per writer combo and newsletter. 
echo .  Use publisher name, go way back in time, and use daily average scoring without normalization. 
echo .  Fetch one row per writer+newsletter. Save article data to CSV with co-authors expanded to multiple rows. 
echo .  0 featured, no wildcards, joint, show scores. Save HTML and JSON files to temp (v2 of some files from test6).
echo . (This CSV output is used to update the latest article link per author in the SheWritesAI directory.)
python digest_generator.py -v -d2000 -a1 -s2 -nn -f0 -w0 -rt 7 -u -j -t temp\%dt% -o tests\%dt%\test7 -oh . -oc . -xma -c tests\%dt%\test67_SWAI_newsletters_cats.csv >tests\%dt%\test7_SWAI_newsletters_cats.digest2000d_a1j_s2nY.log
echo Test7 result: %errorlevel%
call checklog.bat tests\%dt%\test7_SWAI_newsletters_cats.digest2000d_a1j_s2nY.log
ren tests\%dt%\test7\test67_SWAI_newsletters_cats.digest*.* test7_SWAI_newsletters_cats.digest*.*
echo .

echo ******************************************************************************************************
echo 8) Test new skip and max arguments with full SWAI newsletter list 500+. Skip 2 rows, limit 10.
mkdir tests\%dt%\rows\
python digest_generator.py -v -d2000 -a1 -s2 -nn -f0 -w0 -rt 7 -u --skip_rows 2 --max_rows 10 -o tests\%dt%\test8\ -oh . -oc . -xma -t temp\%dt% -c inputs\my_SWAI_newsletters.csv >tests\%dt%\test8_SWAI_newsletters_rows.digest2000d_a1_s2nY_rows3-12.log
echo Test8 result: %errorlevel%
call checklog.bat tests\%dt%\test8_SWAI_newsletters_rows.digest2000d_a1_s2nY_rows3-12.log
echo .

echo ******************************************************************************************************
echo 9) Test regenerating HTML only while reusing the big output file from test 7. 
echo .  (tests\%dt%\test7_SWAI_newsletters_cats.digest2000d_s2nN_a1_xma.csv)
echo .  Make collapsible category sections in HTML. Change to 5 featured, 5 wildcards, joint, hide scores.
echo .  See if the expansion of the featured section for tied max scores works. 
echo .  Add timestamp to default output filename (HTML only). Not verbose.
dir tests\%dt%\test7\test7_SWAI_newsletters_cats.digest2000d_s2nN_a1_xma.csv
python digest_generator.py -v -ra -cc -j -f5 -w5 -hs -ts -o tests\%dt%\test9 -oh . -c tests\%dt%\test7\test7_SWAI_newsletters_cats.digest2000d_s2nN_a1_xma.csv >tests\%dt%\test9_SWAI_newsletters_cats.reuse_jf5w5c.log
echo Test9 result: %errorlevel%
call checklog.bat tests\%dt%\test9_SWAI_newsletters_cats.reuse_jf5w5c.log
echo .

echo ******************************************************************************************************
REM echo 10) Test with full SWAI newsletter list 500+, with no limit on articles per writer combo and newsletter. 
REM echo .  Use publisher name, go way back in time, and use daily average scoring without normalization. 
REM echo .  Save article data to CSV with co-authors expanded to multiple rows. 
REM echo .  20 featured, no wildcards, joint, show scores. Save HTML and JSON files to temp (v3 of some files from test6?).
REM echo . (This is the stress test for the largest possible file and max number of API calls. It takes several hours to fetch the data!)
echo Test #10 MOVED TO THE STRESS TEST SCRIPT - use it sparingly.
REM python digest_generator.py -v -d2000 -s2 -nn -f20 -w0 -rt 10 -u -j -t temp\%dt% -o tests\%dt%\test10 -oh . -oc . -xma -c tests\%dt%\test67_SWAI_newsletters_cats.csv >tests\%dt%\test10_SWAI_newsletters_cats.digest2000d_a0jf20w0_s2nY.log
REM echo Test10 result: %errorlevel%
REM call checklog.bat tests\%dt%\test10_SWAI_newsletters_cats.digest2000d_a0jf20w0_s2nY.log
REM ren tests\%dt%\test7\test67_SWAI_newsletters_cats.digest*.* test10_SWAI_newsletters_cats.digest*.*
REM echo .

echo ******************************************************************************************************
call venv_deactivate.bat

dir tests\%dt%\test*.*.log
for %%f in (tests\%dt%\test*.*.log) do call checklog.bat %%f

echo .
echo digest_generator.py regression tests finished at %date% %time%
echo Check results in tests\%dt%*.log and digest output files in tests\%dt%\

exit /b 0