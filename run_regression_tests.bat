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
REM   2025-11-20_my_SWAI_newsletters.csv 
REM Results (HTML and CSV) and log files will be stored in a dated TESTS subfolder. 
REM Intermediate files (HTML and JSON) will be stored in a dated TEMP subfolder.

echo digest_generator.py regression tests starting at %date% %time%

call venv_activate.bat
call setDT.bat
mkdir tests\%dt%

python digest_generator.py -h >tests\%DT%\help_text.txt

echo 1) Run with all defaults: csv_path, output HTML filename, HTML metrics, no article CSV file, all other basic options.
copy my_newsletters.csv tests\%dt%\my_newsletters.csv
cd tests\%dt%
python ..\..\digest_generator.py >my_newsletters.test1.digest_defaults.log
ren my_newsletters.csv my_newsletters.test1.csv
ren my_newsletters.digest7d_s1_m0.*.f5_w1.html my_newsletters.test1.digest7d_s1_m0.*.f5_w1.html
cd ..\..

echo 2) Repeat with Substack API calls for metrics (default HTML file only, no article CSV). Save JSONs to temp folder.
copy my_newsletters.csv tests\%dt%\my_newsletters.test2.csv
python digest_generator.py --use_substack_api Y --temp_folder temp\%dt% --csv_path tests\%dt%\my_newsletters.test2.csv >tests\%dt%\my_newsletters.test2.digest_substack_metrics.log

REM Use default output naming on test3, specify filenames on test4
echo 3) Run with my 3 newsletters only, 2000 days with standard scoring, 0 featured, 20 wildcards. Save article data to CSV and save HTMLs to temp.
copy inputs\kjs_newsletters.csv       tests\%dt%\kjs_newsletters.test3.csv
python digest_generator.py --csv_path tests\%dt%\kjs_newsletters.test3.csv --output_file_csv . --days_back 2000 --featured_count 0 --wildcards 20 --scoring_choice 1 --verbose Y --temp_folder temp\%dt%  >tests\%dt%\kjs_newsletters.test3.digest2000d_s1_f0_w20.log

echo 4) Run with my 3 newsletters only, 2000 days with daily average scoring, no wildcards. Save article data to CSV. No temp files.
copy inputs\kjs_newsletters.csv       tests\%dt%\kjs_newsletters.test4.csv
python digest_generator.py --csv_path tests\%dt%\kjs_newsletters.test4.csv --output_file_html tests\%dt%\kjs_newsletters.test4.digest2000d_s2_f20_w0.html --output_file_csv tests\%dt%\kjs_newsletters.test4.digest2000d_s2.csv --days_back 2000 --scoring_choice 2 --featured_count 20 --wildcards 0 --verbose Y >tests\%dt%\kjs_newsletters.test4.digest2000d_s2.log

echo 5) Test with no category column and ignore author name matching even though Author column is present. Save articles to CSV. No temp files.
copy tests\smiley_newsletter_tests.csv tests\%dt%\smiley_newsletters.test5.csv
python digest_generator.py --csv_path  tests\%dt%\smiley_newsletters.test5.csv --output_file_csv . --days_back 30 --match_authors N --verbose Y >tests\%dt%\smiley_newsletters.test5.digest30d_m0_nomatch.log

echo 6) Test with full categorized SWAI newsletter list 500+, standard weekly digest with standard scoring, no max per author. Save article data to CSV and save JSON files to temp.
copy inputs\2025-11-20_my_SWAI_newsletters.csv tests\%dt%\SWAI_newsletters_cats.test67.csv
python digest_generator.py --csv_path tests\%dt%\SWAI_newsletters_cats.test67.csv --output_file_html tests\%dt%\SWAI_newsletters_cats.test6.digest7d_m0_s1_f5_w1.%dt%.html --output_file_csv tests\%dt%\SWAI_newsletters_cats.test6.digest7d_m0_s1.csv --use_substack_api Y --max_retries 7 --verbose Y --temp_folder temp\%dt% >tests\%dt%\SWAI_newsletters_cats.test6.digest7d_m0_s1_f5_w1.log

echo 7) Test with full SWAI newsletter list 500+, but fetch only one l article per writer and newsletter, go way back in time, and use daily average scoring. Save article data to CSV and save HTML files to temp.
python digest_generator.py --csv_path tests\%dt%\SWAI_newsletters_cats.test67.csv --output_file_html . --output_file_csv . --use_substack_api N --max_retries 7 --max_articles_per_author 1 --days_back 2000 --scoring_choice 2 --verbose Y --temp_folder temp\%dt% >tests\%dt%\SWAI_newsletters_cats.test7.digest2000d_m1_s2.log
ren tests\%dt%\SWAI_newsletters_cats.test67.digest*.* SWAI_newsletters_cats.test7.digest*.*

call venv_deactivate.bat

dir tests\%dt%\*.test*.*.log

echo digest_generator.py regression tests finished at %date% %time%
echo Check results in tests\%dt%*.log and digest output files

exit /b 0