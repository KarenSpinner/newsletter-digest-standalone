# Standalone Newsletter Digest Generator

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
   Newsletter Name,Website URL,Category,Collections, Author
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
**python digest_generator.py --interactive Y** - prompt for all configuration options
**python digest_generator.py [options]** - run with specified options and default values for unspecified options

usage: digest_generator.py [-h] [--csv_path CSV_PATH] [--days_back DAYS_BACK] 
						   [--featured_count FEATURED_COUNT] [--interactive INTERACTIVE] 
                           [--match_authors MATCH_AUTHORS] [--max_retries MAX_RETRIES] 
						   [--output_file_csv OUTPUT_FILE_CSV] [--output_file_html OUTPUT_FILE_HTML]  
                           [--scoring_choice SCORING_CHOICE]
                           [--show_scores SHOW_SCORES] 
						   [--use_substack_api USE_SUBSTACK_API]
                           [--verbose VERBOSE] [--wildcards WILDCARDS]

Generate newsletter digest.

options:
  -h, --help            show this help message and exit
  --csv_path CSV_PATH   Path to CSV file with newsletter list (default='my_newsletters.csv')
  --days_back DAYS_BACK How many days back to fetch articles (default=7)
  --featured_count FEATURED_COUNT
                        How many articles to feature (default=5)
  --interactive INTERACTIVE
                        Use interactive prompting for inputs? (default='n')
  --match_authors MATCH_AUTHORS
                        Use Author column in CSV file to filter articles (default='y'; no effect if no such column in the file, or cell is blank)
  --max_retries MAX_RETRIES
                        Number of times to retry API calls (default=3)
  --output_file_csv OUTPUT_FILE_CSV
                        Output CSV filename for digest data (e.g., 'digest_output.csv'); default=none, use . for a default name
  --output_file_html OUTPUT_FILE_HTML
                        Output HTML filename (e.g., default 'digest_output.html'; use . for a default name)
  --reuse_csv_data REUSE_CSV_DATA
                        CVS_PATH has the name of an output file from a previous run. Reuse it without re-fetching RSS data or metrics from Substack.
  --scoring_choice SCORING_CHOICE
                        Scoring method: 1=Standard, 2=Daily Average (default=1)
  --show_scores SHOW_SCORES
                        Show scores outside the Featured section? (default=n)
  --use_substack_api USE_SUBSTACK_API
                        Use Substack API to get engagement metrics? (default=n, get from RSS - restack counts not available)
  --verbose VERBOSE     More detailed outputs while program is running? (default='n')
  --wildcards WILDCARDS How many wildcard picks to include? (default=1)
```

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

4. **Include wildcard?** (default: yes)
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
========================================
📧 Standalone Newsletter Digest Generator
========================================

Step 1: Load Newsletters
----------------------------------------
Path to CSV file (press Enter for 'my_newsletters.csv'): [Enter]
✅ Loaded 25 newsletters from CSV

Step 2: Digest Configuration
----------------------------------------
How many days back to fetch articles? (default: 7): [Enter]
How many featured articles? (default: 5): [Enter]
Include wildcard pick? (y/n, default: y): [Enter]

Scoring method:
  1. Daily Average - Favors recent articles (10 likes today > 50 likes last week)
  2. Standard - Favors total engagement (50 likes last week > 10 likes today)
Choose scoring method (1/2, default: 2): [Enter]

Show scores? (y/n, default: y): [Enter]

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

Output filename (default: digest_output.html): [Enter]

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
- Engagement stats (comments, likes) and score
- Article summary

### 🎲 Wildcard Picks (optional)
One or more random articles from the next 10 highest-scored articles - helps surface hidden gems!

### 📂 Categorized Sections
Remaining articles grouped by category:
- Business
- Technology
- Culture
- etc.

Each article shows:
- Title with link
- Newsletter name with link and author
- Author name
- Days since publication and date of publication
- Engagement stats (comments, likes) and (optionally) score

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
engagement = (comments × 3) + likes
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
engagement = (comments × 3) + likes
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
- Check that CSV has valid Substack URLs

### "HTTP errors" during fetch
- Some newsletters may be temporarily down
- Script will skip and continue with others
- Normal to see a few failures in large lists

### Engagement metrics are zero
- Article may genuinely have no engagement yet
- HTML parsing may have failed for that specific article
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

Edit styling around line 300+ in `digest_generator.py`:
- Font sizes
- Colors
- Spacing
- Border styles

### Article Limits

- **Featured count**: Set via CLI prompt
- **Articles per category**: No limit

## Support

Questions? Contact karen@wonderingabout.ai

## License

Free to use and modify. No warranty provided.
