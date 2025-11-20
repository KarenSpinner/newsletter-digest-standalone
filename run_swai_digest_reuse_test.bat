@echo off
cls
echo Starting RUN_SWAI_DIGEST_REUSE_TEST.bat at %date% %time%

if not exist logs mkdir logs
call venv_activate.bat

REM See if this solves the encoding issues with special characters
set PYTHONIOENCODING=utf_8
call setDT.bat

REM Small test:
set inputf=2025-11-17T0630_my_newsletters_short.swai-handles.digest_output-saved
dir outputs\%inputf%.csv

@echo on
python digest_generator.py --reuse_csv_data y --csv_path outputs\%inputf%.csv --featured_count 5 --scoring_choice 1 --show_scores n --output_file_csv . --output_file_html . --verbose y --wildcards 2  >logs\%dt%_my_newsletters_short.swai-digest-test.log
echo %date% %time% Status: %errorlevel% 
@echo off
dir logs\%dt%_my_newsletters_short.swai-digest-test.log

REM Big test:
echo %date% %time%

set inputf=2025-11-17T0645_my_swai_newsletters.digest_output-saved
dir outputs\%inputf%.csv

@echo on
python digest_generator.py --reuse_csv_data y --csv_path outputs\%inputf%.csv --featured_count 20 --scoring_choice 1 --show_scores y --output_file_csv . --output_file_html . --verbose y --wildcards 5 >>logs\%dt%_my_newsletters_big.swai-digest-test.log
echo %date% %time% Status: %errorlevel% 
@echo off
dir outputs\%inputf%*.* /o-d

dir logs\%dt%_my_newsletters_big.swai-digest-test.log

call venv_deactivate.bat

exit /b 0
