#!/usr/bin/env python3
"""
Standalone Digest Generator
===========================
Generates newsletter digests from my_newsletters.csv using free Substack APIs.
No authentication required, no paid API calls.

Features:
- Reads newsletters from CSV export
- Fetches articles via RSS feeds
- Gets engagement metrics (likes, comments) from public Substack API
- Uses Daily Average scoring model
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
            print(f"   Please export your newsletters from StackDigest first.")
            return False

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build RSS URL from website URL (Substack pattern)
                website_url = row['Website URL'].strip()

                # Extract base URL and build RSS feed
                if 'substack.com' in website_url:
                    # Handle both custom domains and substack.com URLs
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

        cutoff_date = datetime.now(timezone.utc) - timedelta(days=days_back)
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

                    # Extract article data
                    article = {
                        'title': entry.get('title', ''),
                        'link': entry.get('link', ''),
                        'summary': self._clean_summary(entry.get('summary', '')),
                        'published': pub_date,
                        'newsletter_name': newsletter['name'],
                        'newsletter_category': newsletter['category'],
                        'word_count': 0,  # Will calculate if needed
                        'comment_count': 0,
                        'reaction_count': 0,
                        'restacks': 0,
                    }

                    # Get engagement metrics from Substack API
                    self._fetch_engagement_metrics(article)

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

    def _fetch_engagement_metrics(self, article):
        """Fetch engagement metrics from Substack's public API"""
        try:
            # Extract slug from URL
            # Format: https://newsletter.substack.com/p/slug-here
            match = re.search(r'/p/([^/?\#]+)', article['link'])
            if not match:
                return

            slug = match.group(1)

            # Extract base URL
            base_url_match = re.match(r'(https?://[^/]+)', article['link'])
            if not base_url_match:
                return

            base_url = base_url_match.group(1)

            # Fetch post details from Substack API
            api_url = f"{base_url}/api/v1/posts/{slug}"
            headers = {
                'User-Agent': 'Mozilla/5.0 (compatible; DigestBot/1.0)',
                'Accept': 'application/json'
            }

            response = requests.get(api_url, headers=headers, timeout=10)

            if response.status_code == 200:
                post_data = response.json()

                # Extract engagement metrics
                article['comment_count'] = post_data.get('comment_count', 0)

                # Sum up reactions
                reactions = post_data.get('reactions', {})
                if isinstance(reactions, dict):
                    article['reaction_count'] = sum(reactions.values())

                article['restacks'] = post_data.get('restacks', 0)

                # Get word count from body
                body_html = post_data.get('body_html', '')
                if body_html:
                    text = BeautifulSoup(body_html, 'html.parser').get_text()
                    article['word_count'] = len(text.split())

        except Exception as e:
            # Silently fail - engagement metrics are optional
            pass

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

    def score_articles_daily_average(self):
        """
        Score articles using Daily Average model

        Engagement score normalized by days since publication.
        This rewards consistently good articles over viral spikes.
        """
        print("\n📊 Scoring articles using Daily Average model...")

        now = datetime.now(timezone.utc)

        for article in self.articles:
            # Calculate days since publication (minimum 1 to avoid division by zero)
            days_old = max((now - article['published']).days, 1)

            # Calculate total engagement
            total_engagement = (
                (article['comment_count'] * 2) +  # Comments weighted 2x
                article['reaction_count'] +       # Likes
                (article['restacks'] * 3)         # Restacks weighted 3x
            )

            # Daily average engagement
            daily_avg = total_engagement / days_old

            # Bonus for longer articles (over 1000 words)
            length_bonus = 0
            if article['word_count'] > 1000:
                length_bonus = 0.2
            elif article['word_count'] > 500:
                length_bonus = 0.1

            # Final score
            article['score'] = daily_avg * (1 + length_bonus)

        # Sort by score descending
        self.articles.sort(key=lambda x: x['score'], reverse=True)

        print(f"✅ Scored {len(self.articles)} articles")

        # Show top 5 scores
        if self.articles:
            print("\n🏆 Top 5 articles:")
            for i, article in enumerate(self.articles[:5], 1):
                days_old = (now - article['published']).days
                print(f"   {i}. {article['title'][:60]}")
                print(f"      Score: {article['score']:.2f} | Engagement: {article['comment_count']} comments, "
                      f"{article['reaction_count']} likes, {article['restacks']} restacks | {days_old}d old")

    def generate_digest_html(self, featured_count=5, include_wildcard=False):
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
        html_parts.append(f'''
        <div style="text-align: center; padding: 40px 20px; margin-bottom: 40px; border-bottom: 1px solid #ddd;">
            <h1 style="font-size: 36px; font-weight: 700; color: #1a1a1a; margin: 0 0 10px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">Newsletter Digest</h1>
            <div style="font-size: 16px; color: #666; margin-bottom: 8px;">{now.strftime('%A, %B %d, %Y')}</div>
            <div style="font-size: 14px; color: #666; margin-bottom: 8px;">{len(featured)} Featured • {len(self.articles)} Total Articles</div>
            <div style="font-size: 13px; color: #888; font-style: italic;">Daily Average scoring • {len(self.newsletters)} newsletters</div>
        </div>
        ''')

        # Featured Section
        if featured:
            html_parts.append('<h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 40px 0 20px 0; padding-bottom: 8px; border-bottom: 2px solid #ddd; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">Featured Articles</h2>')

            for i, article in enumerate(featured, 1):
                html_parts.append(self._format_article_featured(article, number=i))

        # Wildcard Section
        if wildcard:
            html_parts.append('<h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 40px 0 20px 0; padding-bottom: 8px; border-bottom: 2px solid #ddd; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">Wildcard Pick</h2>')
            html_parts.append(self._format_article_featured(wildcard, wildcard=True))

        # Categorized Sections
        for category in sorted(categorized.keys()):
            articles = categorized[category][:10]  # Limit per category

            if articles:
                html_parts.append(f'<h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 40px 0 20px 0; padding-bottom: 8px; border-bottom: 2px solid #ddd; font-family: -apple-system, BlinkMacSystemFont, \'Segoe UI\', sans-serif;">{category}</h2>')

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

        # Engagement metadata
        days_ago = (datetime.now(timezone.utc) - article['published']).days
        meta_parts = [article['newsletter_name']]

        if article['comment_count'] > 0:
            meta_parts.append(f"{article['comment_count']} comments")
        if article['reaction_count'] > 0:
            meta_parts.append(f"{article['reaction_count']} likes")
        if article['restacks'] > 0:
            meta_parts.append(f"{article['restacks']} restacks")

        meta_parts.append(f"{days_ago}d ago")

        # Add score
        score = article.get('score', 0)
        if score > 0:
            meta_parts.append(f"Score: {score:.1f}")

        meta_text = ' • '.join(meta_parts)

        # Build HTML
        return f'''
        <div style="margin-bottom: 40px; padding-bottom: 30px; border-bottom: 1px solid #ddd;">
            <div style="font-size: 22px; font-weight: 700; line-height: 1.3; margin-bottom: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                <a href="{article['link']}" style="color: #1a1a1a; text-decoration: none;">{title_text}</a>
            </div>
            <div style="font-size: 14px; color: #666; margin-bottom: 15px;">{meta_text}</div>
            {f'<div style="font-size: 17px; line-height: 1.7; color: #1a1a1a; margin-bottom: 15px;">{article["summary"]}</div>' if article['summary'] else ''}
        </div>
        '''

    def _format_article_compact(self, article):
        """Format a compact article (for category sections)"""
        # Engagement metadata
        days_ago = (datetime.now(timezone.utc) - article['published']).days
        meta_parts = [article['newsletter_name']]

        if article['comment_count'] > 0:
            meta_parts.append(f"{article['comment_count']} comments")
        if article['reaction_count'] > 0:
            meta_parts.append(f"{article['reaction_count']} likes")
        if article['restacks'] > 0:
            meta_parts.append(f"{article['restacks']} restacks")

        meta_parts.append(f"{days_ago}d ago")

        # Add score
        score = article.get('score', 0)
        if score > 0:
            meta_parts.append(f"Score: {score:.1f}")

        meta_text = ' • '.join(meta_parts)

        return f'''
        <div style="padding: 15px 0; border-bottom: 1px solid #ddd;">
            <div style="font-size: 18px; font-weight: 600; line-height: 1.4; margin-bottom: 5px;">
                <a href="{article['link']}" style="color: #1a1a1a; text-decoration: none;">{article['title']}</a>
            </div>
            <div style="font-size: 14px; color: #666;">{meta_text}</div>
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
    generator.score_articles_daily_average()

    print()

    # Step 5: Generate digest
    print("Step 5: Generate Digest")
    print("-" * 70)
    html = generator.generate_digest_html(
        featured_count=featured_count,
        include_wildcard=include_wildcard
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
