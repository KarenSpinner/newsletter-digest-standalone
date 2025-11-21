@echo off

echo Weekly SWAI digest generator starting
echo %date %time
call setDT.bat

if not exist logs mkdir logs
call venv_activate.bat

REM TO DO: Add step that fetches the latest list of newsletters from the SWAI directory

REM Solve encoding issues with special characters when logging to file in Windows
set PYTHONIOENCODING=utf_8

REM 5 retries wasn't enough for ~2 writers who did have articles, when tested 2025-11-16. Try bumping the retry limit up to 7.
python digest_generator.py --csv_path inputs\2025-11-20_my_SWAI_newsletters.csv --days_back 7 --featured_count 10 --match_authors y --max_retries 7 --output_file_html outputs\%dt%_swai_newsletters-digest.html --output_file_csv outputs\%dt%_swai_newsletters-digest.csv --scoring_choice 1 --show_scores n --use_substack_api y  --verbose y --wildcards 5 --temp_folder temp\%dt%\ >logs\%dt%_swai_newsletters-digest_log.txt

dir outputs\%dt%_swai_newsletters-digest*.* /o-d

dir logs\%dt%_swai_newsletters-digest_log.txt

call venv_deactivate.bat

echo Weekly SWAI digest generator finished
echo %date %time

exit /b 0