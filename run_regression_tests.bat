@echo off

echo digest_generator.py regression tests starting at %date% %time%

call venv_activate.bat
call setDT.bat

python digest_generator.py -h >tests\help_text.txt

echo 1) Run with default csv_path and default output HTML filename, no output CSV file, all default options (HTML metrics_
python digest_generator.py >%dt%_1_default_html_metrics.log

echo 2) Repeat with Substack API calls for metrics
python digest_generator.py --use_substack_api Y  >%dt%_2_default_substack_metrics.log

echo 3) Run with my 3 newsletters only, 2000 days with standard scoring, no featured; save articles to CSV
python digest_generator.py --csv_path kjs_newsletters.csv --output_file_csv . --days_back 2000 --featured_count 0 --wildcards 20 --scoring_choice 1 >%dt%_3_kjs_d2000_s1.log

echo 4) Run with my 3 newsletters only, 2000 days with daily average scoring, no wildcard; save articles to CSV
python digest_generator.py --csv_path kjs_newsletters.csv --output_file_csv . --days_back 2000 --featured_count 20 --wildcards 0 --scoring_choice 2 >%dt%_4_kjs_d2000_s2.log

echo 5) Test with no category column and ignoring author name matching even though Author column is present
python digest_generator.py --csv_path tests\smiley_newsletter_tests.csv --output_file_csv . --days_back 30 --match_authors N >%dt%_5_smiley_d30.log

echo 6) Test with full SWAI newsletter list 500+, standard weekly digest
python digest_generator.py --csv_path tests\2025-11-19_SWAI-activity-digest-categories-537.csv --output_file_html . --output_file_csv . --use_substack_api Y --max_retries 7  >%dt%_6_SWAI_d7.log

echo 7) Test with full SWAI newsletter list 500+, fetch only one l article per writer & newsletter, but go way back in time
python digest_generator.py --csv_path tests\2025-11-19_SWAI-activity-digest-categories-537.csv --output_file_html . --output_file_csv . --use_substack_api Y --max_retries 7 --max_per_author 1 --days_back 2000 >%dt%_7_SWAI_d2000_m1.log

call venv_deactivate.bat

dir %dt%*.log

echo digest_generator.py regression tests finished at %date% %time%
echo Check results in %dt%*.log and digest output files

exit /b 0