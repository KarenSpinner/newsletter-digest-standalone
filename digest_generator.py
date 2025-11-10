#!/usr/bin/env python3
"""
Standalone Digest Generator
===========================
Generates newsletter digests from my_newsletters.csv using RSS feeds and HTML parsing.
No Substack API calls, no authentication required.

Features:
- Reads newsletters from CSV export
- Fetches articles via RSS feeds (substackURL/feed)
- Extracts engagement metrics (likes, comments) from article page HTML
- Engagement-based scoring with length bonus
- Interactive CLI for configuration
- Outputs Substack-ready HTML

Usage:
    python digest_generator.py
"""

import csv
import sys
import requests
import feedparser
from datetime import datetime, timedelta, timezone
from collections import defaultdict
from pathlib import Path
import re
from bs4 import BeautifulSoup


class DigestGenerator:
    """Standalone newsletter digest generator"""

    def __init__(self):
        self.newsletters = []
        self.articles = []

    def load_newsletters_from_csv(self, csv_path='my_newsletters.csv'):
        """Load newsletters from CSV export"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"❌ Error: {csv_path} not found!")
            print(f"   Please create a CSV file with your newsletter subscriptions.")
            return False

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build RSS URL from website URL (Substack pattern)
                website_url = row['Website URL'].strip()

                # Skip empty URLs
                if not website_url:
                    continue

                # Extract base URL and build RSS feed
                # Note: Custom domains (e.g., insights.priva.cat) still use /feed endpoint
                if website_url.startswith('http'):
                    base_url = website_url.rstrip('/')
                else:
                    base_url = f"https://{website_url}"

                rss_url = f"{base_url}/feed"

                self.newsletters.append({
                    'name': row['Newsletter Name'],
                    'url': website_url,
                    'rss_url': rss_url,
                    'category': row.get('Category', 'Uncategorized'),
                    'collections': row.get('Collections', ''),
                })

        print(f"✅ Loaded {len(self.newsletters)} newsletters from CSV")
        return True

    def fetch_articles(self, days_back=7):
        """Fetch recent articles from all newsletters"""
        print(f"\n📰 Fetching articles from past {days_back} days...")

        # Use date boundaries (midnight to midnight) not current time
        # Example: If today is Nov 10 at 5pm and days_back=7,
        # include all articles from Nov 4 00:00 onwards, not from Nov 3 5pm
        today = datetime.now(timezone.utc).date()
        cutoff_date = datetime.combine(today - timedelta(days=days_back), datetime.min.time()).replace(tzinfo=timezone.utc)

        print(f"   Date range: {cutoff_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

        articles = []
        success_count = 0

        for i, newsletter in enumerate(self.newsletters, 1):
            try:
                print(f"  [{i}/{len(self.newsletters)}] {newsletter['name']}...", end='', flush=True)

                # Fetch RSS feed
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; DigestBot/1.0)'}
                response = requests.get(newsletter['rss_url'], headers=headers, timeout=10)

                if response.status_code != 200:
                    print(f" ⚠️  HTTP {response.status_code}")
                    continue

                feed = feedparser.parse(response.content)
                article_count = 0

                for entry in feed.entries:
                    # Parse publication date
                    pub_date = None
                    if hasattr(entry, 'published_parsed') and entry.published_parsed:
                        pub_date = datetime(*entry.published_parsed[:6], tzinfo=timezone.utc)
                    elif hasattr(entry, 'updated_parsed') and entry.updated_parsed:
                        pub_date = datetime(*entry.updated_parsed[:6], tzinfo=timezone.utc)

                    # Skip old articles
                    if not pub_date or pub_date < cutoff_date:
                        continue

                    # Extract author(s) from RSS feed
                    authors = []
                    if hasattr(entry, 'author') and entry.author:
                        authors.append(entry.author)
                    elif hasattr(entry, 'authors') and entry.authors:
                        authors.extend([a.get('name', a) if isinstance(a, dict) else a for a in entry.authors])

                    # Get content for word count (try content first, fallback to summary)
                    content_html = ''
                    if hasattr(entry, 'content') and entry.content:
                        # RSS content is usually a list of dicts with 'value' key
                        if isinstance(entry.content, list) and len(entry.content) > 0:
                            content_html = entry.content[0].get('value', '')
                        else:
                            content_html = str(entry.content)
                    elif hasattr(entry, 'summary') and entry.summary:
                        content_html = entry.summary

                    # Calculate word count from content
                    word_count = 0
                    if content_html:
                        text = BeautifulSoup(content_html, 'html.parser').get_text()
                        word_count = len(text.split())

                    # Extract article data
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'summary': self._clean_summary(entry.get('summary', '')),
                        'published': pub_date,
                        'newsletter_name': newsletter['name'],
                        'newsletter_category': newsletter['category'],
                        'authors': authors,  # List of author names
                        'word_count': word_count,
                        'comment_count': 0,  # Extracted from HTML
                        'reaction_count': 0,  # Extracted from HTML
                    }

                    # Fetch engagement metrics from article page HTML
                    self._fetch_engagement_from_html(article)

                    articles.append(article)
                    article_count += 1

                if article_count > 0:
                    print(f" ✅ {article_count} articles")
                    success_count += 1
                else:
                    print(f" - (no recent articles)")

            except Exception as e:
                print(f" ❌ Error: {e}")
                continue

        print(f"\n✅ Fetched {len(articles)} total articles from {success_count} newsletters")
        self.articles = articles
        return articles

    def _clean_summary(self, html_content):
        """Remove HTML tags from summary"""
        if not html_content:
            return ""

        soup = BeautifulSoup(html_content, 'html.parser')
        text = soup.get_text()

        # Limit to first 150 characters
        if len(text) > 150:
            text = text[:147] + '...'

        return text.strip()

    def _fetch_engagement_from_html(self, article):
        """Fetch engagement metrics by parsing the article page HTML"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; DigestBot/1.0)'}
            response = requests.get(article['link'], headers=headers, timeout=10)

            if response.status_code != 200:
                return

            soup = BeautifulSoup(response.text, 'html.parser')

            # Method 1: Parse interactionStatistic meta tag (structured data)
            meta_tag = soup.find('meta', {'property': 'interactionStatistic'})
            if meta_tag and meta_tag.get('content'):
                import json
                try:
                    stats = json.loads(meta_tag['content'])
                    for stat in stats:
                        if stat.get('interactionType') == 'https://schema.org/LikeAction':
                            article['reaction_count'] = stat.get('userInteractionCount', 0)
                        elif stat.get('interactionType') == 'https://schema.org/CommentAction':
                            article['comment_count'] = stat.get('userInteractionCount', 0)
                except json.JSONDecodeError:
                    pass

            # Method 2: Parse aria-labels from buttons (backup method)
            if article['reaction_count'] == 0:
                like_button = soup.find('button', {'aria-label': re.compile(r'Like \((\d+)\)')})
                if like_button:
                    match = re.search(r'Like \((\d+)\)', like_button.get('aria-label', ''))
                    if match:
                        article['reaction_count'] = int(match.group(1))

            if article['comment_count'] == 0:
                comment_button = soup.find('button', {'aria-label': re.compile(r'View comments \((\d+)\)')})
                if comment_button:
                    match = re.search(r'View comments \((\d+)\)', comment_button.get('aria-label', ''))
                    if match:
                        article['comment_count'] = int(match.group(1))

        except Exception as e:
            # Silently fail - engagement metrics are optional
            pass

    def score_articles(self, use_daily_average=True):
        """
        Score articles based on engagement and content length

        Scoring formula:
        - Engagement component (weighted heavily):
          * Comments weighted 3x (deeper engagement)
          * Likes weighted 1x (standard engagement)
        - Daily average (optional): Divide by days since publication
        - Length component (ensures articles with 0 engagement still get scored):
          * Word count / 100 as base points
          * Ensures longer articles rank above zero even without engagement
        - Final scores normalized to 1-100 range

        To customize scoring weights, edit the values below:
        """
        if use_daily_average:
            print("\n📊 Scoring articles using Daily Average model (engagement + length)...")
        else:
            print("\n📊 Scoring articles using Standard model (total engagement + length)...")

        now = datetime.now(timezone.utc)

        # SCORING CONFIGURATION - Edit these to change the scoring model
        COMMENT_WEIGHT = 3      # How much to weight comments (deeper engagement)
        LIKE_WEIGHT = 1         # How much to weight likes (standard engagement)
        LENGTH_WEIGHT = 0.05    # Points per 100 words (e.g., 2000 words = 1 point)

        for article in self.articles:
            # Calculate engagement component
            engagement_score = (
                (article['comment_count'] * COMMENT_WEIGHT) +
                (article['reaction_count'] * LIKE_WEIGHT)
            )

            # Apply daily average if requested
            if use_daily_average:
                days_old = max((now - article['published']).days, 1)
                engagement_score = engagement_score / days_old

            # Calculate length component (ensures non-zero score)
            # Word count contributes a small amount even with zero engagement
            length_score = (article['word_count'] / 100) * LENGTH_WEIGHT

            # Combine engagement + length
            article['raw_score'] = engagement_score + length_score

        # Normalize scores to 1-100 range
        if self.articles:
            raw_scores = [a['raw_score'] for a in self.articles]
            min_score = min(raw_scores)
            max_score = max(raw_scores)

            # Handle edge case where all scores are the same
            score_range = max_score - min_score
            if score_range == 0:
                for article in self.articles:
                    article['score'] = 50.0  # All get mid-range score
            else:
                for article in self.articles:
                    # Normalize to 1-100 range
                    normalized = ((article['raw_score'] - min_score) / score_range) * 99 + 1
                    article['score'] = normalized

        # Sort by score descending
        self.articles.sort(key=lambda x: x['score'], reverse=True)

        print(f"✅ Scored {len(self.articles)} articles")

        # Show top 5 scores
        if self.articles:
            print("\n🏆 Top 5 articles:")
            for i, article in enumerate(self.articles[:5], 1):
                now = datetime.now(timezone.utc)
                days_old = (now - article['published']).days
                print(f"   {i}. {article['title'][:60]}")
                print(f"      Score: {article['score']:.1f} | {article['comment_count']} comments, "
                      f"{article['reaction_count']} likes | "
                      f"{article['word_count']} words | {days_old}d old")

    def generate_digest_html(self, featured_count=5, include_wildcard=False, days_back=7, scoring_method='daily_average'):
        """Generate Substack-ready HTML digest with clean formatting"""
        print(f"\n📝 Generating digest HTML...")

        # Select featured articles
        featured = self.articles[:featured_count]

        # Select wildcard (random from next 10)
        wildcard = None
        if include_wildcard and len(self.articles) > featured_count:
            import random
            wildcard_pool = self.articles[featured_count:featured_count + 10]
            if wildcard_pool:
                wildcard = random.choice(wildcard_pool)

        # Group remaining articles by category
        categorized = defaultdict(list)
        for article in self.articles:
            if article not in featured and article != wildcard:
                categorized[article['newsletter_category']].append(article)

        # Build HTML with inline styles (Substack-friendly)
        html_parts = []

        # Container with max-width for readability
        html_parts.append('<div style="font-family: Georgia, serif; max-width: 700px; margin: 0 auto; line-height: 1.7; color: #1a1a1a;">')

        # Header
        now = datetime.now()
        scoring_label = "Daily Average" if scoring_method == 'daily_average' else "Standard"
        html_parts.append(f'''
        <div style="text-align: center; padding: 40px 20px; margin-bottom: 40px;">
            <h1 style="font-size: 36px; font-weight: 700; color: #1a1a1a; margin: 0 0 10px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">Newsletter Digest</h1>
            <div style="font-size: 16px; color: #666; margin-bottom: 8px;">{now.strftime('%A, %B %d, %Y')}</div>
            <div style="font-size: 14px; color: #666; margin-bottom: 8px;">{len(featured)} Featured • {len(self.articles)} Total Articles</div>
            <div style="font-size: 13px; color: #888; font-style: italic;">{scoring_label} scoring (engagement + length) • {days_back} day lookback • {len(self.newsletters)} newsletters</div>
        </div>
        ''')

        # Featured Section
        if featured:
            html_parts.append('<h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 40px 0 20px 0; padding-bottom: 8px; border-bottom: 1px solid #eee; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">Featured Articles</h2>')

            for i, article in enumerate(featured, 1):
                html_parts.append(self._format_article_featured(article, number=i))

        # Wildcard Section
        if wildcard:
            html_parts.append('<h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 40px 0 20px 0; padding-bottom: 8px; border-bottom: 1px solid #eee; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">Wildcard Pick</h2>')
            html_parts.append(self._format_article_featured(wildcard, wildcard=True))

        # Categorized Sections
        for category in sorted(categorized.keys()):
            articles = categorized[category]

            if articles:
                html_parts.append(f'<h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 40px 0 20px 0; padding-bottom: 8px; border-bottom: 1px solid #eee; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">{category}</h2>')

                for article in articles:
                    html_parts.append(self._format_article_compact(article))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    def _format_article_featured(self, article, number=None, wildcard=False):
        """Format a featured article with full details"""
        # Title
        title_text = article['title']
        if number:
            title_text = f"{number}. {title_text}"
        if wildcard:
            title_text = f"🎲 {title_text}"

        # Build engagement lines
        days_ago = (datetime.now(timezone.utc) - article['published']).days
        engagement_html = f'<div style="font-size: 13px; color: #666; line-height: 1.6;">'

        # First line: Newsletter name, author(s), and date
        first_line_parts = [article["newsletter_name"]]
        if article.get('authors') and len(article['authors']) > 0:
            author_text = ' & '.join(article['authors'])
            first_line_parts.append(f"by {author_text}")
        first_line_parts.append(f"{days_ago}d ago")
        engagement_html += f'<div>{" • ".join(first_line_parts)}</div>'

        # Add engagement metrics if present
        metrics = []
        if article['comment_count'] > 0:
            metrics.append(f"{article['comment_count']} comments")
        if article['reaction_count'] > 0:
            metrics.append(f"{article['reaction_count']} likes")

        if metrics:
            engagement_html += f'<div>{" • ".join(metrics)}</div>'

        # Add word count and score
        score = article.get('score', 0)
        word_count = article.get('word_count', 0)
        score_line = f'Score: {score:.1f}'
        if word_count > 0:
            score_line += f' • {word_count:,} words'
        engagement_html += f'<div>{score_line}</div>'

        engagement_html += '</div>'

        # Build HTML
        return f'''
        <div style="margin-bottom: 40px;">
            <div style="font-size: 22px; font-weight: 700; line-height: 1.3; margin-bottom: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                <a href="{article['link']}" style="color: #1a1a1a; text-decoration: none;">{title_text}</a>
            </div>
            {engagement_html}
            {f'<div style="font-size: 17px; line-height: 1.7; color: #1a1a1a; margin-top: 12px;">{article["summary"]}</div>' if article['summary'] else ''}
        </div>
        '''

    def _format_article_compact(self, article):
        """Format a compact article (for category sections)"""
        # Build engagement lines (SEPARATE LINES)
        days_ago = (datetime.now(timezone.utc) - article['published']).days
        engagement_html = f'<div style="font-size: 13px; color: #666; line-height: 1.6;">'

        # First line: Newsletter name, author(s), and date
        first_line_parts = [article["newsletter_name"]]
        if article.get('authors') and len(article['authors']) > 0:
            author_text = ' & '.join(article['authors'])
            first_line_parts.append(f"by {author_text}")
        first_line_parts.append(f"{days_ago}d ago")
        engagement_html += f'<div>{" • ".join(first_line_parts)}</div>'

        # Add engagement metrics if present
        metrics = []
        if article['comment_count'] > 0:
            metrics.append(f"{article['comment_count']} comments")
        if article['reaction_count'] > 0:
            metrics.append(f"{article['reaction_count']} likes")

        if metrics:
            engagement_html += f'<div>{" • ".join(metrics)}</div>'

        # Add word count and score
        score = article.get('score', 0)
        word_count = article.get('word_count', 0)
        score_line = f'Score: {score:.1f}'
        if word_count > 0:
            score_line += f' • {word_count:,} words'
        engagement_html += f'<div>{score_line}</div>'

        engagement_html += '</div>'

        return f'''
        <div style="padding: 15px 0;">
            <div style="font-size: 18px; font-weight: 600; line-height: 1.4; margin-bottom: 5px;">
                <a href="{article['link']}" style="color: #1a1a1a; text-decoration: none;">{article['title']}</a>
            </div>
            {engagement_html}
        </div>
        '''

    def save_digest(self, html, filename='digest_output.html'):
        """Save digest to HTML file"""
        output_path = Path(filename)

        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(html)

        print(f"\n💾 Digest saved to: {output_path.absolute()}")
        print(f"\n📋 To use in Substack:")
        print(f"   1. Open {filename} in a browser")
        print(f"   2. Select all (Cmd/Ctrl + A)")
        print(f"   3. Copy (Cmd/Ctrl + C)")
        print(f"   4. Paste into Substack editor")
        print(f"   5. Substack will preserve all formatting!")


def interactive_cli():
    """Interactive CLI for digest generation"""
    print("=" * 70)
    print("📧 Standalone Newsletter Digest Generator")
    print("=" * 70)
    print()

    generator = DigestGenerator()

    # Step 1: Load newsletters
    print("Step 1: Load Newsletters")
    print("-" * 70)
    csv_path = input("Path to CSV file (press Enter for 'my_newsletters.csv'): ").strip()
    if not csv_path:
        csv_path = 'my_newsletters.csv'

    if not generator.load_newsletters_from_csv(csv_path):
        return

    print()

    # Step 2: Configuration
    print("Step 2: Digest Configuration")
    print("-" * 70)

    days_back = input("How many days back to fetch articles? (default: 7): ").strip()
    days_back = int(days_back) if days_back.isdigit() else 7

    featured_count = input("How many featured articles? (default: 5): ").strip()
    featured_count = int(featured_count) if featured_count.isdigit() else 5

    wildcard = input("Include wildcard pick? (y/n, default: y): ").strip().lower()
    include_wildcard = wildcard != 'n'

    print("\nScoring method:")
    print("  1. Daily Average - Favors recent articles (10 likes today > 50 likes last week)")
    print("  2. Standard - Favors total engagement (50 likes last week > 10 likes today)")
    scoring_choice = input("Choose scoring method (1/2, default: 2): ").strip()
    use_daily_average = scoring_choice == '1'
    scoring_method = 'daily_average' if use_daily_average else 'standard'

    print()

    # Step 3: Fetch articles
    print("Step 3: Fetch Articles")
    print("-" * 70)
    articles = generator.fetch_articles(days_back=days_back)

    if not articles:
        print("\n❌ No articles found! Try increasing the lookback period.")
        return

    print()

    # Step 4: Score articles
    print("Step 4: Score Articles")
    print("-" * 70)
    generator.score_articles(use_daily_average=use_daily_average)

    print()

    # Step 5: Generate digest
    print("Step 5: Generate Digest")
    print("-" * 70)
    html = generator.generate_digest_html(
        featured_count=featured_count,
        include_wildcard=include_wildcard,
        days_back=days_back,
        scoring_method=scoring_method
    )

    # Step 6: Save
    output_file = input("\nOutput filename (default: digest_output.html): ").strip()
    if not output_file:
        output_file = 'digest_output.html'

    generator.save_digest(html, output_file)

    print("\n" + "=" * 70)
    print("✅ Digest generation complete!")
    print("=" * 70)


if __name__ == '__main__':
    try:
        interactive_cli()
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        sys.exit(0)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
