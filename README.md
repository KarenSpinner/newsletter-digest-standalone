# Standalone Newsletter Digest Generator V1.0.1

A simple, self-contained digest generator that runs locally with **no authentication** and **no paid API calls**.

## What it does

Creates a formatted newsletter digest from your Substack subscriptions that you can copy/paste directly into Substack's editor.

### Features
- ✅ **No login required** - Uses public RSS feeds and HTML parsing
- ✅ **Free forever** - No API keys, no paid services
- ✅ **Engagement metrics** - Shows comments and likes from article pages
- ✅ **Flexible scoring** - Choose Standard or Daily Average scoring
- ✅ **Interactive CLI** - Guided setup with sensible defaults
- ✅ **Substack-ready** - Copy/paste formatted HTML directly

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection

### Setup

1. **Create a CSV file with your newsletter subscriptions:**

   Create a file named `my_newsletters.csv` with the following format:

   ```csv
   Newsletter Name,Website URL,Category,Collections, Author, Substack Handle
   The Generalist,https://thegeneralist.substack.com,Business,,
   Stratechery,https://stratechery.com,Technology,,Andrew Sharp
   Not Boring,https://notboring.substack.com,Business,Tech Favorites
   Exponential View (Azeem Azhar),https://www.exponentialview.co/,AI & Machine Learning,SWAI,Chantal Smith
   ```

   **Required fields:**
   - `Newsletter Name` - The name of the newsletter
   - `Website URL` - The Substack URL (e.g., `https://newsletter.substack.com`)

   **Optional fields:**
   - `Category` - For grouping articles (defaults to "Uncategorized")
   - `Collections` - Additional tags or groupings (optional, not currently used)
   - `Author` - Only include articles by a specific author for a newsletter. Put the full or partial author name to match in the column. Blank for a row means no author name matching on that newsletter.
   - `Substack Handle` - If included, will be used in future to create hyperlinks to author names in the digest pages.
   
   **Note:** Currently only supports Substack newsletters with public RSS feeds.

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
   
3. **Windows logging configuration**
   To prevent encoding issues when logging output to a file on Windows, use this command first:
    set PYTHONIOENCODING=utf_8   

That's it! You're ready to go.

## Usage

### Run the generator:
```bash
**python digest_generator.py --help** - show runstring commands
**python digest_generator.py** - all default configuration options are used
**python digest_generator.py --interactive** - prompt for main configuration options (other options can be set in the runstring)
**python digest_generator.py [options]** - run with specified options and default values for unspecified options

usage: digest_generator.py [-h] [-i] [-a ARTICLES_PER_AUTHOR] [-c CSV_PATH]
                           [-d DAYS_BACK] [-f FEATURED_COUNT] [-hs] [-nm]
                           [-nn] [-oc OUTPUT_FILE_CSV] [-oh OUTPUT_FILE_HTML]
                           [-ra] [-r RETRIES] [-s {1,2}] [-t TEMP_FOLDER] [-u]
                           [-v] [-w WILDCARDS]

Generate newsletter digest.

options: (keywords must be in lower case as shown)
  -h, --help            show this help message and exit
  -i, --interactive     Use interactive prompting for inputs.
  -a ARTICLES_PER_AUTHOR, --articles_per_author ARTICLES_PER_AUTHOR
                        Maximum number of articles to include for each
                        newsletter and author combination. 0=no limit, 1=most
                        recent only, 2-max=20 ok. (Substack RSS file max is
                        20.) Default=0.
  -c CSV_PATH, --csv_path CSV_PATH
                        Path to CSV file with newsletter list (OR saved
                        article data, with --reuse_CSV_data Y).
                        Default='my_newsletters.csv'
  -d DAYS_BACK, --days_back DAYS_BACK
                        How many days back to fetch articles. Default=7,
                        min=1.
  -f FEATURED_COUNT, --featured_count FEATURED_COUNT
                        How many articles to feature. Default=5, min=0 (none),
                        max=20.
  -hs, --hide_scores    Hide scores on articles outside the Featured and
                        Wildcard sections
  -nm, --no_name_match  Do not use Author column in CSV newsletter file to
                        filter articles (partial matching). Matching is on by
                        default if Author column is in the newsletter file. It
                        has no effect if the cell is blank for a newsletter
                        row.
  -nn, --no_normalization
                        Suppress normalization of final scores to 1-100 range.
                        (Raw scores over 100 are still capped at final
                        score=100 regardless.)
  -oc OUTPUT_FILE_CSV, --output_file_csv OUTPUT_FILE_CSV
                        Output CSV filename for digest article data (e.g.,
                        'digest_output.csv'). Default=none. Use '.' for a
                        default filename based on csv_path, timestamp, and
                        settings.
  -oh OUTPUT_FILE_HTML, --output_file_html OUTPUT_FILE_HTML
                        Output HTML filename (e.g., 'digest_output.html' in
                        interactive mode). Omit or use '.' in runstring for a
                        default name based on csv_path, timestamp, and
                        settings.
  -ra, --reuse_article_data
                        Read article data from CSV Path instead of newsletter
                        data.
  -r RETRIES, --retries RETRIES
                        Number of times to retry failed API calls with
                        increasing delays. Default=3. Retries will be logged
                        as ⏱ .
  -s {1,2}, --scoring_choice {1,2}
                        Scoring method: 1=Standard, 2=Daily Average.
                        Default=1.
  -t TEMP_FOLDER, --temp_folder TEMP_FOLDER
                        Subfolder for saving temporary HTML and JSON files
                        (results of API calls), e.g. 'temp'. Default='' (no
                        temp files saved)
  -u, --use_substack_api
                        Use Substack API to get engagement metrics. (Default
                        is to get metrics from HTML (faster, but restack
                        counts are not available)
  -v, --verbose         More detailed outputs while program is running.
  -w WILDCARDS, --wildcards WILDCARDS
                        Number of wildcard picks to include. Default=1, min=0
                        (none), max=20.

```
**Tip for developers working on this tool** 

If you are working on enhancements to digest formatting, here's a way to speed up your testing.
Run the program once using runstring option:
  `--output_file_csv (article_data_filename)`
This will save the artice data to a CSV file. Then when you are ready to run the program again to test formatting changes, specify in the runstring: 
  `--reuse_article_data --csv_path (article_data_filename)`
The program will load the article data from CSV and then execute the formatting and output steps
with no time required for making any API calls.
This allows very fast iteration, even with no network connection. And it makes tests repeatable.

**Using the digest tool for periodic backups of your own newsletter**

- Create a my_backup.csv file which has links to your own newsletter (or newsletters, if you have more than one).
- Run the digest tool with a long lookback period (enough to cover your last 20 articles) and with the temp_folder option.
  Example: python digest_generator.py -d 90 -t backup_files -c my_backup.csv
- The tool will generate a digest page and save a HTML copy of each of your articles in the backup_files folder
- You can also save a CSV file of your article data with the links and metrics by including the -oc option.
  Example: python digest_generator.py -d 90 -t backup_files -c my_backup.csv -oc backup_files\my_article_data.csv


### Interactive prompts:

You'll be asked:

1. **CSV file path** (default: `my_newsletters.csv`)
   - Just press Enter if the file is in the same directory

2. **Days back** (default: 7)
   - How far back to look for articles
   - 7 days = weekly digest
   - 14 days = bi-weekly digest

3. **Featured articles** (default: 5)
   - Number of top articles to highlight
   - 3-7 is typical

4. **Include wildcards?** (default: 1)
   - Adds a random "hidden gem" from next 10 articles
   - Makes digest more interesting!

5. **Scoring method** (default: Standard)
   - Standard: Favors total engagement (50 likes last week > 10 likes today)
   - Daily Average: Favors recent articles (10 likes today > 50 likes last week)

6. **Show scores** (default: yes)
   - Include scores on digest page for non-featured articles

7. **Output filename** (default: `digest_output.html`)
   - Name of the HTML file to save

### Example session:
```
=========================================
📧 Standalone Newsletter Digest Generator
=========================================

Step 1: Digest Configuration
----------------------------------------

Path to CSV file (press Enter for 'my_newsletters.csv'): [Enter]

How many days back to fetch articles? (default: 7): [Enter]
How many featured articles? (default: 5): [Enter]
Include wildcard picks? (default: 1): [Enter]

Scoring method:
  1. Standard - Favors total engagement (50 likes last week > 10 likes today)
  2. Daily Average - Favors recent articles (10 likes today > 50 likes last week)
Choose scoring method (1/2, default: 1): [Enter]

Show scores? (y/n, default: y): [Enter]

Output filename (default: digest_output.html): [Enter]

Step 2: Load Newsletters
----------------------------------------
✅ Loaded 25 newsletters from CSV

Step 3: Fetch Articles
----------------------------------------
📰 Fetching articles from past 7 days...
  [1/25] The Generalist... ✅ 2 articles
  [2/25] Stratechery... ✅ 3 articles
  ...
✅ Fetched 47 total articles from 18 newsletters

Step 4: Score Articles
----------------------------------------
📊 Scoring articles using Standard model (total engagement + length)...
✅ Scored 47 articles

🏆 Top 5 articles:
   1. The Future of AI Agents
      Score: 100.0 | 45 comments, 234 likes | 4,521 words | 2d old
   2. Understanding Neural Networks
      Score: 87.3 | 12 comments, 89 likes | 3,200 words | 1d old
   3. The Ethics of AI Development
      Score: 65.2 | 8 comments, 45 likes | 2,800 words | 3d old
   ...

Step 5: Generate Digest
----------------------------------------
📝 Generating digest HTML...

💾 Digest saved to: /path/to/digest_output.html

📋 To use in Substack:
   1. Open digest_output.html in a browser
   2. Select all (Cmd/Ctrl + A)
   3. Copy (Cmd/Ctrl + C)
   4. Paste into Substack editor
   5. Substack will preserve all formatting!

========================================
✅ Digest generation complete!
========================================
```

## Output Format

The digest includes:

### ✨ Featured Articles
Top-scored articles with:
- Numbered list (1, 2, 3...)
- Full title with link
- Newsletter name with link
- Author name
- Days since publication and publication date
- Engagement stats (comments, likes, restacks if available) and score
- Article summary

### 🎲 Wildcard Picks (optional)
Same content as Featured Articles. One or more random articles from the next 10 highest-scored articles - helps surface hidden gems!

### 📂 Categorized Sections
Remaining articles grouped by category, using categories in the newsletter CSV file:
- Business
- Technology
- Culture
- etc.
If there is no Category column in the newsletter CSV file, all articles will be grouped as Uncategorized.

Each categorized article shows:
- Title with link
- Newsletter name with link
- Author name
- Days since publication and date of publication
- Engagement stats (comments, likes, restacks if available) and (if not suppressed) score

## How It Works

### Data Sources
1. **RSS Feeds** - Gets article titles, links, dates, content (public, no auth)
   ```
   https://newsletter.substack.com/feed
   ```
2. **HTML Parsing** - Extracts engagement metrics from article pages
   - Parses Schema.org structured data in meta tags
   - Gets `comment_count` and `like_count` (reactions)
   - **No API calls** unless overridden in runstring - complies with Substack TOS

### Scoring Algorithm

You can choose between two scoring methods:

#### 1. Standard Scoring (Default - Recommended)

**Formula:**
```python
engagement = (comments × 2) + likes
length = (word_count / 100) × 0.05
raw_score = engagement + length
normalized_score = scale to 1-100 range
```

**Best for:**
- Highlighting articles with most total engagement
- Finding evergreen content that remains popular
- Weekly/bi-weekly digests with older articles
- Balanced view across publication dates

**Key features:**
- Articles with 0 engagement still get scored based on length
- All scores normalized to 1-100 range for consistency
- Longer articles always rank above zero

**Example:**
- Article with 50 likes, 2000 words = high engagement + length score
- Article with 0 likes, 3000 words = low score but not zero
- Article with 5 comments, 500 words = medium-high score

#### 2. Daily Average Scoring

**Formula:**
```python
engagement = (comments × 2) + likes
daily_avg_engagement = engagement / days_since_publication
length = (word_count / 100) × 0.05
raw_score = daily_avg_engagement + length
normalized_score = scale to 1-100 range
```

**Best for:**
- Highlighting fresh, trending content
- Daily digests where recency matters
- Identifying articles gaining momentum
- When you want newest content prioritized

**Key features:**
- Same length scoring as Standard
- Divides engagement by age in days
- Favors recent articles with moderate engagement over older articles with high engagement

**Example:**
- Article from 7 days ago with 50 likes = 7.1 engagement/day + length
- Article from today with 10 likes = 10 engagement/day + length
- Today's article likely wins! 🏆

#### Shared Settings

**Weights (both methods):**
- **Restacks: 3×** (deeper engagement signal, if available)
- **Comments: 2×** (deeper engagement signal)
- **Likes: 1×** (standard engagement)
- **Length: 0.05 points per 100 words** (ensures non-zero scores)
- **Score range: Always normalized to 1-100**

**To customize scoring:**
Edit the constants in `digest_generator.py`:
```python
RESTACK_WEIGHT = 3      # How much to weight restacks, if known (default: 3×)
COMMENT_WEIGHT = 2      # How much to weight comments (default: 2×)
LIKE_WEIGHT = 1         # How much to weight likes (default: 1×)
LENGTH_WEIGHT = 0.05    # Points per 100 words (default: 0.05)
```

## Troubleshooting

### "UnicodeEncodeError"
- Happens on Windows when logging output to a file without setting the default encoding
- Solution: set PYTHONIOENCODING=utf_8

### "CSV file not found"
- Make sure `my_newsletters.csv` is in the same directory
- Or provide the full path when prompted

### "No articles found"
- Try increasing the lookback period (14 or 21 days)
- Some newsletters publish infrequently
- Check that CSV has valid Substack URLs (newesletter writers sometimes change them)

### "HTTP errors" during fetch
- Some newsletters may be temporarily down
- Script will retry a few times, then skip and continue with others; each retry will show ⏱ 
- Common to see a few failures in large lists or with long lookback periods
- To reduce these failures, increase the number of retry attempts (set via the runstring)

### Engagement metrics are zero
- Article may genuinely have no engagement yet
- HTML retrieval or parsing may have failed for that specific article
- API calls to fetch engagement metrics may have timed out, even after retries
- Articles are still included, just scored lower

## Customization

### Scoring Weights

To customize the scoring model, edit `digest_generator.py`:

```python
# SCORING CONFIGURATION - Edit these to change the scoring model
RESTACK_WEIGHT = 3      # How much to weight restacks (default: 3×, if available)
COMMENT_WEIGHT = 2      # How much to weight comments (default: 2×)
LIKE_WEIGHT = 1         # How much to weight likes (default: 1×)
LENGTH_WEIGHT = 0.05    # Points per 100 words (default: 0.05)
```

**Effect of changes:**
- Increase `COMMENT_WEIGHT` or `RESTACK_WEIGHT` to prioritize discussions over passive engagement
- Increase `LENGTH_WEIGHT` to give more weight to longer, substantial articles
- All scores are automatically normalized to 1-100 range

### HTML Styling

Edit styling in `digest_generator.py`:
- Font sizes
- Colors
- Spacing
- Border styles
Note that Substack will igmore these settings when you paste the digest into the Substack editor. However, they will work when viewing the HTML file in your browser.

### Article Limits

- **Featured count**: Set via CLI prompt or runstring
- **Wildcard count**: Set via CLI prompt or runstring
- **Articles per category**: No limit
- **Articles per newsletter+author**: Default is no limit. Can set a limit in the runstring. Substack RSS limits seem to be 20 articles max.

### Known Limitations

- ** Restack Counts**: Restack counts are currently only available if the Substack API is used for engagement metrics. This is controlled by a runstring argument (no prompting). 

Future: Try to get restack counts from the HTML files, e.g. in <script>window._preloads = JSON.parse{...}, look for 		\"restacks\":<#>,\"reactions\":{\"\u2764\":<#>}

- **Author Listing**: At present, only the lead author name is in the RSS file. When there are multiple authors, Substack appears to choose the name which occurs first alphabetically.
-- Secondary or additional authors' names are not shown in the digest.  
-- If an Author name is specified in a column of the Newsletter file, and a named Author has a byline on the article but is not the first author name that Substack chooses as 'the' lead author, then that Author will not be matched to the article. 

A future workaround is to enhance the program to look inside the HTML of the article for additional author names. (Perhaps in 'entry' in <div id="main"  ... under <script type="application/ld+json">
		{"@context": ... "author":[{"@type":"Person","name":"A<the author name we want>", "url":"https://substack.com/@<author_handle>",}]}
Or in <script>window._preloads = JSON.parse{...}, look for 'name' and 'handle' in 'contributors'. 
Fetching the HTML file to look for author names will make execution a bit slower if the Substack API is being used for metrics instead of HTML. However, if restack counts can be obtained from the HTML, then the Substack API will not be needed and that API call can be dropped.

## Support

Questions? Contact karen@wonderingabout.ai

## License

Free to use and modify for non-commercial purposes. No warranty provided.
