# Standalone Newsletter Digest Generator

A simple, self-contained digest generator that runs locally with **no authentication** and **no paid API calls**.

## What it does

Creates a formatted newsletter digest from your Substack subscriptions that you can copy/paste directly into Substack's editor.

### Features
- ✅ **No login required** - Uses public RSS feeds and APIs
- ✅ **Free forever** - No API keys, no paid services
- ✅ **Engagement metrics** - Shows comments, likes, and restacks
- ✅ **Smart scoring** - Daily Average model (engagement normalized by age)
- ✅ **Interactive CLI** - Guided setup with sensible defaults
- ✅ **Substack-ready** - Copy/paste formatted HTML directly

## Installation

### Prerequisites
- Python 3.8 or higher
- Internet connection

### Setup

1. **Export your newsletters from StackDigest:**
   - Go to Manage Newsletters
   - Click "Export CSV"
   - Save as `my_newsletters.csv`
   - Place it in this directory

2. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

That's it! You're ready to go.

## Usage

### Run the generator:
```bash
python digest_generator.py
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

5. **Output filename** (default: `digest_output.html`)
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

Step 3: Fetch Articles
----------------------------------------
📰 Fetching articles from past 7 days...
  [1/25] The Generalist... ✅ 2 articles
  [2/25] Stratechery... ✅ 3 articles
  ...
✅ Fetched 47 total articles from 18 newsletters

Step 4: Score Articles
----------------------------------------
📊 Scoring articles using Daily Average model...
✅ Scored 47 articles

🏆 Top 5 articles:
   1. The Future of AI Agents
      Score: 15.3 | Engagement: 45 comments, 234 likes, 12 restacks | 2d old
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
- Newsletter name
- Engagement stats (comments, likes, restacks)
- Days since publication
- Article summary
- Daily Average Score

### 🎲 Wildcard Pick (optional)
A random article from the next 10 highest-scored articles - helps surface hidden gems!

### 📂 Categorized Sections
Remaining articles grouped by category:
- Business
- Technology
- Culture
- etc.

Each article shows:
- Title with link
- Newsletter name
- Engagement stats
- Days since publication

## How It Works

### Data Sources
1. **RSS Feeds** - Gets article titles, links, dates (public, no auth)
2. **Substack API** - Gets engagement metrics via public endpoints like:
   ```
   https://newsletter.substack.com/api/v1/posts/slug
   ```
   Returns: `comment_count`, `reactions`, `restacks`

### Scoring Algorithm (Daily Average)

```python
total_engagement = (comments × 2) + likes + (restacks × 3)
daily_average = total_engagement / days_since_publication
score = daily_average × (1 + length_bonus)
```

**Why Daily Average?**
- Rewards consistent quality over viral spikes
- Newer articles compete fairly with older ones
- Prevents recency bias
- Highlights evergreen content

**Weights:**
- Comments: 2× (high-signal engagement)
- Likes: 1×
- Restacks: 3× (highest-signal - someone shared it!)
- Length bonus: +20% for 1000+ words, +10% for 500+ words

## Troubleshooting

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
- Substack may rate-limit public API calls
- Articles are still included, just missing metrics
- Try running again in a few minutes

## Customization

You can edit `digest_generator.py` to customize:

### Engagement weights (line ~200):
```python
total_engagement = (
    (article['comment_count'] * 2) +  # Change comment weight
    article['reaction_count'] +       # Change like weight
    (article['restacks'] * 3)         # Change restack weight
)
```

### HTML styling (line ~300+):
- Font sizes
- Colors
- Spacing
- Border styles

### Article limits:
- Featured count (CLI prompt)
- Articles per category (line ~350): `articles[:10]`

## Future Plans

After StackDigest shutdown, this tool could:
- Run on a schedule (cron/scheduled task)
- Auto-post to Substack via draft API
- Support email delivery
- Add custom templates

## Support

Questions? Contact karen@wonderingabout.ai

## License

Free to use and modify. No warranty provided.

---

**Made with ❤️ for the StackDigest community**
