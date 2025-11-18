@echo off

echo Weekly SWAI digest generator starting
echo %date %time
call setDT.bat

cd c:\kj\myCode\GitHub\newsletter-digest-standalone
if not exist logs mkdir logs
call venv_activate.bat

REM TO DO: Add step that fetches the latest list of newsletters from the SWAI directory

REM Solve encoding issues with special characters when logging to file in Windows
set PYTHONIOENCODING=utf_8

REM Runstring options:
REM usage: digest_generator.py [-h]
REM        [--csv_path CSV_PATH] 
REM        [--days_back DAYS_BACK]
REM        [--featured_count FEATURED_COUNT]
REM        [--interactive INTERACTIVE] 
REM        [--match_authors MATCH_AUTHORS]
REM        [--max_retries MAX_RETRIES]
REM        [--output_file_csv OUTPUT_FILE_CSV]
REM        [--output_file_html OUTPUT_FILE_HTML]
REM        [--scoring_choice SCORING_CHOICE]
REM        [--show_scores SHOW_SCORES]
REM        [--use_substack_api USE_SUBSTACK_API] 
REM        [--verbose VERBOSE]
REM        [--wildcard WILDCARD]

REM 5 retries wasn't enough for ~2 writers who did have articles, when tested 2025-11-16. Try bumping the retry limit up to 7.
python digest_generator.py --csv_path inputs\2025-11-18_my_SWAI_newsletters.csv --days_back 7 --featured_count 10 --match_authors y --max_retries 7 --output_file_html outputs\%dt%_swai_newsletters-digest.html --output_file_csv outputs\%dt%_swai_newsletters-digest.csv --scoring_choice 1 --show_scores n --use_substack_api y  --verbose y --wildcards 5  >logs\%dt%_swai_newsletters-digest_log.txt

dir outputs\%dt%_swai_newsletters-digest*.* /o-d

dir logs\%dt%_swai_newsletters-digest_log.txt

call venv_deactivate.bat

echo Weekly SWAI digest generator finished
echo %date %time

exit /b 0