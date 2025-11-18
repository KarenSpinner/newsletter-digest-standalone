@echo off
cls
echo Starting RUN_SWAI_DIGEST_TEST.bat at %date% %time%

cd c:\kj\myCode\GitHub\newsletter-digest-standalone
if not exist logs mkdir logs
call venv_activate.bat

REM TO DO: Add step that fetches the latest list of newsletters from the SWAI directory Google sheet

REM See if this solves the encoding issues with special characters
set PYTHONIOENCODING=utf_8

REM Runstring options:
REM usage: digest_generator.py [-h]
REM        [--csv_path CSV_PATH] 
REM        [--days_back DAYS_BACK]
REM        [--featured_count FEATURED_COUNT]
REM        [--interactive INTERACTIVE] 
REM        [--max_retries MAX_RETRIES]
REM        [--output_file_csv OUTPUT_FILE_CSV]
REM        [--output_file_html OUTPUT_FILE_HTML]
REM        [--scoring_choice SCORING_CHOICE]
REM        [--show_scores SHOW_SCORES]
REM        [--use_substack_api USE_SUBSTACK_API] 
REM        [--verbose VERBOSE]
REM        [--wildcard WILDCARD]

call setDT.bat

REM small test
REM python digest_generator.py --csv_path inputs\my_newsletters_short.swai-handles.csv --days_back 7 --featured_count 5 --match_authors y --max_retries 5 --output_file_html . --output_file_csv . --scoring_choice 1 --show_scores n --use_substack_api y  --verbose y --wildcard 1  
REM >logs\%dt%_my_newsletters_short.swai-digest.log

REM dir inputs\my_newsletters_short.swai-handles*.* /o-d

REM dir logs\%dt%_my_newsletters_short.swai-digest.log

set inputf=2025-11-18_my_SWAI_newsletters
dir inputs\%inputf%.csv

REM Big test
@echo on
python digest_generator.py --csv_path inputs\%inputf%.csv --days_back 7 --featured_count 20 --match_authors y --max_retries 7 --output_file_html . --output_file_csv . --scoring_choice 1 --show_scores n --use_substack_api y  --verbose y --wildcard 10 >logs\%dt%_my_swai_newsletters_test.log
echo %date% %time% Status: %errorlevel% 
@echo off

dir inputs\%inputf%*digest*.* /o-d

dir logs\%dt%_my_swai_newsletters_test.log

call venv_deactivate.bat
echo Finished at %date% %time%. See log file logs\%dt%_my_swai_newsletters_test.log
exit /b 0