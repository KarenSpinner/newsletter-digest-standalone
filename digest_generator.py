#!/usr/bin/env python3
"""
Standalone Digest Generator
===========================
Generates newsletter digests from my_newsletters.csv using RSS feeds and HTML parsing.
No Substack API calls, no authentication required.

Features:
- Reads newsletters from CSV export
- Fetches articles via RSS feeds (substackURL/feed)
- Extracts engagement metrics (likes, comments, restacks) from article page HTML
- Engagement-based scoring with length bonus
- Interactive CLI or runstring arguments for configuration
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

# Added 2025-11-13 KJS
import argparse
import time


class DigestGenerator:
    """Standalone newsletter digest generator"""

    def __init__(self):
        self.newsletters = []
        self.articles = []

    def load_newsletters_from_csv(self, csv_path='my_newsletters.csv'):
        """Load newsletters from CSV export"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"❌ Error: {csv_path} not found!".encode('utf-8'))
            print(f"   Please create a CSV file with your newsletter subscriptions.")
            return False

        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            for row in reader:
                # Build RSS URL from website URL (Substack pattern)
                website_url = row['Website URL'].strip()

                # Extract base URL and build RSS feed
                # Handle both custom domains and substack.com URLs
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
                    # TO DO: Add author name & profile link for optional additional filtering
                })

        # Check added 2025-11-13 KJS
        if len(self.newsletters) < 1: # no errors, but no newsletters found
            print(f"❌ No newsletters to scan; stopping digest generation".encode('utf-8'))
            return False

        print(f"✅ Loaded {len(self.newsletters)} newsletters from CSV".encode('utf-8'))
        return True

    def fetch_articles(self, days_back=7):
        """Fetch recent articles from all newsletters"""
        print(f"\n📰 Fetching articles from past {days_back} days...".encode('utf-8'))

        # Use date boundaries (midnight to midnight) not current time
        # Example: If today is Nov 10 at 5pm and days_back=7,
        # include all articles from Nov 4 00:00 onwards, not from Nov 3 5pm
        # TO DO: Allow user specification of exact start datetime and end datetime
        today = datetime.now(timezone.utc).date()
        cutoff_date = datetime.combine(today - timedelta(days=days_back), datetime.min.time()).replace(tzinfo=timezone.utc)

        print(f"   Date range: {cutoff_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}")

        articles = []
        success_count = 0

        for i, newsletter in enumerate(self.newsletters, 1):
            try:
                # Added 2025-11-13 KJS - give Substack a breather to try to prevent 429 errors
                # when processing large lists of newsletters
                if (i % 100 == 0): 
                    print(f"(Waiting 5 sec to avoid overloading Substack)")
                    time.sleep(5.0)

                print(f"  [{i}/{len(self.newsletters)}] {newsletter['name']}...".encode('utf-8'), end='', flush=True)

                # Fetch RSS feed
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; DigestBot/1.0)'}
                response = requests.get(newsletter['rss_url'], headers=headers, timeout=10)

                if response.status_code != 200:
                    print(f" ⚠️  HTTP {response.status_code}".encode('utf-8'), end='', flush=True)
                    # KJS 2025-11-13 If response is 429, Too Many Requests, wait
                    # a while and then try again. We don't want to omit anyone.
                    time.sleep(2.0) # 1 second was not enough in some cases; try 2
                    response = requests.get(newsletter['rss_url'], headers=headers, timeout=10)
                    if response.status_code != 200:
                        print(f" ⚠️  HTTP {response.status_code} on retry; skipping this newsletter".encode('utf-8'))
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
                        'title': entry.get('title', ''), # encode as UTF-8 here?
                        'link': entry.get('link', ''),
                        'summary': self._clean_summary(entry.get('summary', '')),  # encode as UTF-8 here?
                        'published': pub_date,
                        'newsletter_name': newsletter['name'], # encode as UTF-8 here?
                        'newsletter_category': newsletter['category'],
                        'authors': authors,  # List of author names  # encode as UTF-8 here?
                        'word_count': word_count,
                        'comment_count': 0,
                        'reaction_count': 0,
                        'restack_count': 0,
                    }

                    # Get engagement metrics from HTML, not Substack API
                    self._fetch_engagement_from_html(article)

                    articles.append(article)
                    article_count += 1

                if article_count > 0:
                    print(f" ✅ {article_count} articles".encode('utf-8'))
                    success_count += 1
                else:
                    print(f" - (no recent articles)")

            except Exception as e:
                print(f" ❌ Error: {e}".encode('utf-8'))
                continue

        print(f"\n✅ Fetched {len(articles)} total articles from {success_count} newsletters".encode('utf-8'))
        self.articles = articles
        return articles

    def _fetch_engagement_metrics_substack_api(self, article):
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

                # Try to get restack count - TO DO: investigate how this might show up in the post data
                article['restack_count'] = post_data.get('restacks', 0)

                # Get word count from body
                body_html = post_data.get('body_html', '')
                if body_html:
                    text = BeautifulSoup(body_html, 'html.parser').get_text()
                    article['word_count'] = len(text.split())

                # Extract authors from API if not already present
                if not article.get('authors'):
                    authors_data = []
                    # Try to get primary author
                    if 'publishedBylines' in post_data:
                        for byline in post_data['publishedBylines']:
                            if 'name' in byline:
                                authors_data.append(byline['name'])
                    # Fallback to single author field
                    elif 'author' in post_data and isinstance(post_data['author'], dict):
                        author_name = post_data['author'].get('name')
                        if author_name:
                            authors_data.append(author_name)

                    if authors_data:
                        article['authors'] = authors_data

        except Exception as e:
            # Silently fail - engagement metrics are optional
            pass

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
                        # KJS 2025-11-13 Try to add restacks back in (as ShareAction?)
                        elif stat.get('interactionType') == 'https://schema.org/ShareAction':
                            article['restack_count'] = stat.get('userInteractionCount', 0)
                        # restack_count isn't working - is there a different interactionType we could use?
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

            # KJS 2025-11-13 Try to count restacks this way too
            if article['restack_count'] == 0: 
                comment_button = soup.find('button', {'aria-label': re.compile(r'Restack \((\d+)\)')})
                if comment_button:
                    match = re.search(r'Restack \((\d+)\)', comment_button.get('aria-label', ''))
                    if match:
                        article['restack_count'] = int(match.group(1))

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
            print("\n📊 Scoring articles using Daily Average model (engagement + length)...".encode('utf-8'))
        else:
            print("\n📊 Scoring articles using Standard model (total engagement + length)...".encode('utf-8'))

        now = datetime.now(timezone.utc)

        # SCORING CONFIGURATION - Edit these to change the scoring model
        RESTACK_WEIGHT = 3      # How much to weight restacks (deeper engagement)
        COMMENT_WEIGHT = 2      # How much to weight comments (deeper engagement)
        LIKE_WEIGHT = 1         # How much to weight likes (standard engagement)
        LENGTH_WEIGHT = 0.05    # Points per 100 words (e.g., 2000 words = 1 point)

        for article in self.articles:
            # Calculate days since publication (minimum 1 to avoid division by zero)
            days_old = max((now - article['published']).days, 1)

            # Calculate engagement component
            total_engagement = engagement_score = (
                (article['reaction_count'] * LIKE_WEIGHT) +
                (article['comment_count'] * COMMENT_WEIGHT) +
                (article['restack_count'] * RESTACK_WEIGHT)    # KJS added restacks
            )

            # Apply daily average if requested
            if use_daily_average:
                engagement_score = engagement_score / days_old

            # Daily average engagement
            daily_avg = total_engagement / days_old

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

        print(f"✅ Scored {len(self.articles)} articles".encode('utf-8'))

        # Show top 5 scores
        if self.articles:
            print("\n🏆 Top 5 articles:".encode('utf-8'))
            for i, article in enumerate(self.articles[:5], 1):
                now = datetime.now(timezone.utc)
                days_old = (now - article['published']).days  # use max (, 1) here?
                print(f"   {i}. {article['title'][:60]}".encode('utf-8')) # handle unicode chars in article titles
                print(f"      Score: {article['score']:.1f} | "
                      f"{article['comment_count']} comments, "
                      f"{article['reaction_count']} likes, "
                      f"{article['word_count']} words | {days_old}d old "
                      f"({article['published'].strftime('%Y-%m-%d.%H:%M')})") # KJS Add actual date published (get in UTC?)

                # removed from above for now, until restack count is working:
                #f"{article['restack_count']} restacks | "


    def generate_digest_html(self, featured_count=5, include_wildcard=False, days_back=7, scoring_method='daily_average', show_scores=True):
        """Generate Substack-ready HTML digest with clean formatting"""
        print(f"\n📝 Generating digest HTML...".encode('utf-8'))

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
        now = datetime.now() # in local time, not UTC, for display purposes (switch to UTC?)
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

                # TO DO: If not showing scores, consider grouping by newsletter and then ordering by date descending
                for article in articles:
                    html_parts.append(self._format_article_compact(article,show_scores))

        html_parts.append('</div>')

        return '\n'.join(html_parts)

    '''
    KJS 2025-11-13 Refactored line1 formatting out from featured and compact functions
    '''
    def _format_article_line1(self, article):

        # First line: Newsletter name, author(s), and date
        first_line_parts = [article["newsletter_name"]]
        if article.get('authors') and len(article['authors']) > 0:
            author_text = ' & '.join(article['authors'])
            first_line_parts.append(f"by {author_text}")
        days_ago = (datetime.now(timezone.utc) - article['published']).days  # use max (, 1) here?
        first_line_parts.append(f" • {days_ago}d ago")
        # TO DO: add actual date published
        
        return f'<div>{" • ".join(first_line_parts)}</div>'
                
    '''
    KJS 2025-11-13 Refactored formatting of engagement metrics out from featured and compact functions
    '''
    def _format_engagement_metrics_and_score(self, article, number=None, show_scores=True):
        # Add engagement metrics if present
        engagement_html = ''
        metrics = []
        if article['comment_count'] > 0:
            metrics.append(f"{article['comment_count']} comments")
        if article['reaction_count'] > 0:
            metrics.append(f"{article['reaction_count']} likes")
        if article['restack_count'] > 0:
            metrics.append(f"{article['restack_count']} restacks")

        engagement_html += f'<div>'
        if metrics:
            engagement_html += f'{" • ".join(metrics)}'
            
        # Add word count and score
        word_count = article.get('word_count', 0)            
        if word_count > 0:
            words_line = f' • {word_count:,} words'
            engagement_html += f' • {words_line}'
        if show_scores:
            score = article.get('score', 0)
            score_line = f'Score: {score:.1f}'
            engagement_html += f' • {score_line}'
        engagement_html += '</div>'        
        return engagement_html

    '''
    Featured articles include numbers or wildcard designators with the article title, and the article summary
    They are otherwise the same as compact articles.
    '''
    def _format_article_featured(self, article, number=None, wildcard=False):
        """Format a featured article with full details"""
        # Title
        title_text = article['title']
        if number:
            title_text = f"{number}. {title_text}"
        if wildcard:
            title_text = f"🎲 {title_text}"

        # Build engagement lines
        engagement_html = f'<div style="font-size: 13px; color: #666; line-height: 1.6;">'

        # First line: Newsletter name, author(s), and date
        engagement_html += self._format_article_line1(article)

        # Add line with engagement metrics and score 
        engagement_html += self._format_engagement_metrics_and_score(article, show_scores=True)        

        engagement_html += '</div>'

        # Add summary if available
        summary_html = f'<div style="font-size: 17px; font-style:italic; line-height: 1.7; color: #1a1a1a; margin-top: 12px;">{article["summary"]}</div>' if article['summary'] else ''

        # Build HTML
        return f'''
        <div style="margin-bottom: 40px;">
            <div style="font-size: 22px; font-weight: 700; line-height: 1.3; margin-bottom: 8px; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">
                <a href="{article['link']}" style="color: #1a1a1a; text-decoration: none;">{title_text}</a>
            </div>
            {engagement_html}
            {summary_html}
        </div>
        '''

    '''
    Format a compact article (for category sections) - no numbers, summary, different HTML styling
    '''
    def _format_article_compact(self, article, show_scores):
        # Build engagement lines (SEPARATE LINES)
        engagement_html = f'<div style="font-size: 13px; color: #666; line-height: 1.6;">'

        # First line: Newsletter name, author(s), and date
        engagement_html += self._format_article_line1(article)

        # Add line with engagement metrics and score 
        engagement_html += self._format_engagement_metrics_and_score(article, show_scores=show_scores)        

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

        print(f"\n💾 Digest saved to: {output_path.absolute()}".encode('utf-8'))
        print(f"\n📋 To use in Substack:".encode('utf-8'))
        print(f"   1. Open {filename} in a browser")
        print(f"   2. Select all (Cmd/Ctrl + A)")
        print(f"   3. Copy (Cmd/Ctrl + C)")
        print(f"   4. Paste into Substack editor")
        print(f"   5. Substack will preserve all formatting!")

'''
Non-Interactive function for digest generation (so it can be scripted and scheduled)
'''
def automated_digest(csv_path, days_back, featured_count, include_wildcard, use_daily_average, scoring_method, show_scores, verbose, output_file):

    print("=" * 70)
    print("📧 Standalone Newsletter Digest Generator".encode('utf-8'))
    print("=" * 70)
    print()

    generator = DigestGenerator()

    # Step 1: Load newsletters
    print("Step 1: Load Newsletters")
    print("-" * 70)

    if not generator.load_newsletters_from_csv(csv_path):
        return -1
    print()

    # Step 2: Configuration
    print("Step 2: Digest Configuration")
    print("-" * 70)
    print()

    # Step 3: Fetch articles
    print("Step 3: Fetch Articles")
    print("-" * 70)
    articles = generator.fetch_articles(days_back=days_back) # TO DO: Update to handle start date-end date

    if not articles:
        print("\n❌ No articles found! Try increasing the lookback period.".encode('utf-8'))
        return -1

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
        scoring_method=scoring_method,
        show_scores=show_scores
    )

    # Step 6: Save
    generator.save_digest(html, output_file)

    # TO DO: Save the data on the articles to a dataframe, then to CSV (if option selected by user)

    print("\n" + "=" * 70)
    print("✅ Digest generation complete!".encode('utf-8'))
    print("=" * 70)

    return 0

################################################################################
'''
Get all inputs interactively up front
'''
def interactive_cli():

    csv_path = input("Path to CSV file (press Enter for 'my_newsletters.csv'): ").strip()
    if not csv_path:
        csv_path = 'my_newsletters.csv'

    days_back = input("How many days back to fetch articles? (default: 7): ").strip()
    days_back = int(days_back) if days_back.isdigit() else 7

    featured_count = input("How many featured articles? (default: 5): ").strip()
    featured_count = int(featured_count) if featured_count.isdigit() else 5

    wildcard = input("Include wildcard pick? (y/n, default: y): ").strip().lower()
    include_wildcard = (wildcard != 'n')

    print("\nScoring method:")
    print("  1. Daily Average - Favors recent articles (10 likes today > 50 likes last week)")
    print("  2. Standard - Favors total engagement (50 likes last week > 10 likes today)")
    scoring_choice = input("Choose scoring method (1/2, default: 2): ").strip()
    use_daily_average = scoring_choice == '1'
    scoring_method = 'daily_average' if use_daily_average else 'standard'

    scoring = input("Show scores on non-featured articles? (y/n, default: y): ").strip().lower()
    show_scores = (scoring != 'n')

    output_file = input("Output filename (default: digest_output.html): ").strip()
    if not output_file:
        output_file = 'digest_output.html'

    return csv_path, days_back, featured_count, include_wildcard, use_daily_average, show_scores, output_file

'''
Handle interactive mode or scriptable runstring
'''
def main():
    
    #sys.setdefaultencoding('utf-8')
    
    # Runstring options added 2025-11-13 KJS
    # See if we have runstring arguments. If so, use them and don't do prompting
    # Allow interactive mode to be an option
    parser = argparse.ArgumentParser(description="Generate newsletter digest.")
    parser.add_argument("--csv_path", help="Path to CSV file (default='my_newsletters.csv')", default="my_newsletters.csv")
    parser.add_argument("--days_back", help="How many days back to fetch articles (default=7)", type=int, default=7)
    parser.add_argument("--featured_count", help="How many articles to feature (default=10)", type=int, default=10)
    parser.add_argument("--wildcard", help="Include wildcard pick? (default=n)", default='n')
    parser.add_argument("--scoring_choice", help="Scoring method: 1=Daily Average, 2=Standard (default=2)",default='2')
    parser.add_argument("--show_scores", help="Show scores outside the Featured section? (default=n)",default='n')
    parser.add_argument("--output_file", help="Output filename (e.g., 'digest_output.html')", default="digest_output.html")
    parser.add_argument("--verbose", help="More detailed outputs while program is running? (default='n')", default='n')
    parser.add_argument("--interactive", help="Use interactive prompting for inputs? (default='n')", default='n')

    print("=" * 70)
    print("📧 Standalone Newsletter Digest Generator".encode('utf-8'))
    print("=" * 70)
    print()

    result=0
    try:
        args = parser.parse_args()
        interactive=(args.interactive[0].lower() != 'n')
        if interactive:
            # prompt for (almost) everything
            csv_path, days_back, featured_count, include_wildcard, use_daily_average, show_scores, output_file = interactive_cli()
            verbose=args.verbose
            print("\nRunning digest generator with defaults and settings from interactive prompts\n")
        else:
            csv_path          = args.csv_path
            days_back         = args.days_back
            featured_count    = args.featured_count
            include_wildcard  = (args.wildcard[0].lower() != 'n')
            use_daily_average = args.scoring_choice == '1'
            show_scores       = (args.show_scores[0].lower() != 'n')
            verbose           = (args.verbose[0].lower() != 'n')
            output_file       = args.output_file.strip()
            if not output_file or len(output_file) < 2:
                output_file = 'digest_output.html'    # TO DO: Make a default name based on input name
            print("\nRunning digest generator with defaults and settings from runstring\n")

        if verbose:
            print(f"CSV path: {csv_path}")
            print(f"Days back: {days_back}")
            print(f"Featured count: {featured_count}")
            print(f"Include wildcard? {include_wildcard}")
            print(f"Show scores? {show_scores}")
            print(f"Output file: {output_file}")
            print()
        
        scoring_method = ('daily_average' if use_daily_average else 'standard')
        result=automated_digest(csv_path, days_back, featured_count, include_wildcard, use_daily_average, scoring_method, show_scores, verbose, output_file)
    
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user".encode('utf-8'))
        return 0

    except Exception as e:
        print(f"\n❌ Error: {e}".encode('utf-8'))
        import traceback
        traceback.print_exc()
        return -1
    
    return result
    
if __name__ == '__main__':
    result = main()
    sys.exit(result)
