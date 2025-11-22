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
    
To prevent encoding issues when logging output to a file on Windows, use this command first:
    set PYTHONIOENCODING=utf_8
    
KJS 2025-11-17 Added <hr> elements around h2 elements to set them off for longer listings. Note that putting the <hr> tags inside the <h2>s works fine in a browser but does not work when pasted into substack. Substack reverts the text to plain text, not H2. So the <hr> tags are outside. Still experimenting with getting Substack to respect extra blank lines.
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
import pandas as pd
import os

# Added 2025-11-13 KJS
import argparse
import time
import traceback
import json

################################################################################
''' Default settings used for runstring and for interactive '''
DEFAULT_DAYS_BACK=7;       MAX_DAYS_BACK=2000   # Use MAX_PER_AUTHOR=1 with MAX_DAYS_BACK to get the latest for each newsletter+author, even if not recent
DEFAULT_FEATURED_COUNT=5;  MAX_FEATURED_COUNT=20
DEFAULT_WILDCARD_PICKS=1;  MAX_WILDCARD_PICKS=20
DEFAULT_RETRY_COUNT=3;     MAX_RETRY_COUNT=10
DEFAULT_PER_AUTHOR=0;      MAX_PER_AUTHOR=20  # each RSS file seems to max out at 20 articles regardless, and this limit is per newsletter-author combo
VERBOSE_DEFAULT=False
INTERACTIVE_DEFAULT=False
NORMALIZE_DEFAULT=True
MATCH_AUTHORS_DEFAULT=True
REUSE_ARTICLES_DEFAULT=False
SHOW_SCORES_DEFAULT=True
SUBSTACK_API_DEFAULT=False
SCORING_CHOICE_DEFAULT='1'
CSV_PATH_DEFAULT="my_newsletters.csv"
ARTICLES_CSV_DEFAULT="my_articles.csv"
OUTPUT_HTML_DEFAULT="digest_output.html"
OUTPUT_CSV_DEFAULT="digest_articles.csv"

WARNING_TRIANGLE_ICON="⚠️ "
GREEN_CHECKMARK_ICON="✅ "
RED_X_FAILURE_ICON="❌ "
STOPWATCH_ICON="⏱ "

DG_VERSION="1.0.1" 

''' Markdown link utilities '''
def get_from_markdown(md_string:str, verbose=VERBOSE_DEFAULT):
    """
    Extracts the title and link from a markdown string of the form [title](link).
    Args: md_string (str): A string containing a markdown link.
    Returns: tuple: (title, link) if found, else (None, None).
    Problem: Does not work well on markdown strings where the title inside the [] contains its own [ or ].
    """
    try:
        # Text is in the pattern '[title](link)'
        pattern = r'\[([^\]]+)\]\(([^)]+)\)'
        match = re.search(pattern, md_string)
        if match:
            title, link = match.groups()
            return title, link
    except Exception as e:
        if verbose: print(f"Exception parsing name and link from markdown text: {md_string}")

    # No exception, but it didn't match, either
    if verbose: print(f"Unable to parse name and link from markdown: wrong format {md_string}")
    return None, None

def make_markdown_link(title:str, url:str):
    ''' KJS 2025-11-17 Create a markdown link string that handles a title which has its own [] inside '''
    if title and url:
        escaped_title=title.replace("[","\[")
        escaped_title=escaped_title.replace("]","\]")
        md_string = f"[{escaped_title}]({url})"
    elif title:
        md_string=title
    else:
        md_string=""
    return md_string

''' Digest Generator '''
class DigestGenerator:
    """Standalone newsletter digest generator"""

    def __init__(self):
        self.newsletters = []
        self.articles = []

    ''' Add one newsletter (from input CSV file OR reconstructed from articles CSV file) '''
    def _add_newsletter(self, newsletter_name, website_url, writer_name='', writer_handle='', category='', collections='', verbose=VERBOSE_DEFAULT):

        # Extract base URL and build RSS feed
        # Handle both custom domains and substack.com URLs
        # Note: Custom domains (e.g., insights.priva.cat) still use /feed endpoint
        if website_url.startswith('http'):
            base_url = website_url.rstrip('/')
        else:
            base_url = f"https://{website_url}"                
        rss_url = f"{base_url}/feed"
        
        # KJS: It's possible for a newsletter to be in a list twice with different writer names,
        # or with the same writer name if it's an alias for multiple people who write in it.
        # If the same, don't duplicate it in our list. We'd just do extra work for nothing
        # and end up with duplicate articles in the digest.
        duplicate=False
        for newsletter in self.newsletters:
            duplicate = newsletter_name==newsletter['name'] and writer_name==newsletter['writer_name']
            if duplicate: break
            # Also note the possibility that a newsletter could be in here twice: once
            # with a name and once with blank (no matching). Going to ignore that for now.
        if duplicate: 
            #if verbose: print(f"  Skipping newsletter {newsletter_name} and writer '{writer_name}' (duplicate)")
            return None

        # Not a duplicate - add it
        newsletter = {
            'name': newsletter_name,
            'url': website_url,
            'rss_url': rss_url,
            'category': category,
            'collections': collections,
            'writer_name': writer_name,
            'writer_handle': writer_handle,
            'article_count': 0,
        }                
        self.newsletters.append(newsletter)

        #if verbose: print(f"  Added newsletter {newsletter} to list")
        return newsletter

    ''' Process one newsletter row (from input CSV file OR reconstructed from articles CSV file) '''
    def _process_newsletter(self, row, verbose=VERBOSE_DEFAULT):

        # Get the required columns
        website_url = row['Website URL'].strip()
        newsletter_name = row['Newsletter Name'].strip()
        
        # KJS Handle blank lines in the input file (e.g. rows with an author name but no newsletter)
        if len(website_url) < 1: 
            return None

        # Get the optional columns
        category = row.get('Category', 'Uncategorized').strip()
        collections = row.get('Collections', '').strip()
        writer_name = row.get('Author', '').strip()     # KJS 2025-11-13 input from newsletter CSV file
        writer_handle = row.get('Substack Handle', '').strip() # KJS 2025-11-17 input from newsletter CSV file

        newsletter=self._add_newsletter(newsletter_name, website_url, writer_name, writer_handle, category, collections, verbose)
        return newsletter

    def load_newsletters_from_csv(self, csv_path=CSV_PATH_DEFAULT, verbose=VERBOSE_DEFAULT):
        """Load newsletters from CSV export"""
        csv_file = Path(csv_path)
        if not csv_file.exists():
            print(f"{RED_X_FAILURE_ICON}Error: {csv_path} not found!")
            print(f"   Please create a CSV file with your newsletter subscriptions.")
            return False

        # Note that if the user wants to feed in CSV article data but forgets to set the
        # --reuse_csv_data runstring option, this section will choke on trying to find 
        # 'Website URL'. That's sort of ok, although it would be nicer to detect this
        # and tell them to set the runstring option.
        try:
            with open(csv_file, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                for row in reader:
                    self._process_newsletter(row, verbose)

        except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
            print(f"\n{RED_X_FAILURE_ICON}ERROR: Reading from CSV newsletter data file '{csv_path}' failed: \n{e}\n")
            if verbose: traceback.print_exc()
            return False

        # Check added 2025-11-13 KJS
        if len(self.newsletters) < 1: # no errors, but no newsletters found
            print(f"{RED_X_FAILURE_ICON}No newsletters to scan; stopping digest generation")
            return False

        print(f"{GREEN_CHECKMARK_ICON}Loaded {len(self.newsletters)} newsletters from CSV")
        return True

    def _api_call_retries(self, headers, url, max_retries=DEFAULT_RETRY_COUNT, verbose=VERBOSE_DEFAULT):
        ''' Retry API calls with increasing delays if we get 429 (or other) errors '''

        retry_count=0; delay=2.0 # KJS 2025-11-18 Wait 2 sec initially, instead of 1, if a timeout
        while retry_count <= max_retries:  # Make sure we go through here once even if max_retries=0
            response=None
            try:
                response = requests.get(url, headers=headers, timeout=10)

                if response.status_code == 200: 
                    #if verbose and retry_count>0: print(f"\nCall succeeded after {retry_count} retries.")
                    return response
                # If we got a response other than 200, fall through to the error handling below

            except (requests.exceptions.HTTPError, requests.exceptions.ConnectionError, requests.exceptions.RequestException) as e:
                # If offline, calls seem to fail with 11001, getaddrinfo failed 
                print(f"\n{WARNING_TRIANGLE_ICON}API call failed with request connection error")
                # Certain HTTP errors will return exception details in a response object - use if available
                if e.response:
                    if e.response.text: print(f"Request Exception on API call:\n{e.response.text}\n")
                if verbose: print(f"\n{e}\n")
                # This could be intermittent - keep trying?
                print(f"\n{WARNING_TRIANGLE_ICON}Check your network connection.")
                # KJS 2025-11-20 Fall through to error handling below to wait before retrying

            except Exception as e:
                print(f"{WARNING_TRIANGLE_ICON}Other Exception on API call:")
                print(f"\n{e}\n")
                if verbose: traceback.print_exc()
                print(f"\n{WARNING_TRIANGLE_ICON}Check your network connection.")
                # KJS 2025-11-20 Fall through to error handling below to wait before retrying
                
            # KJS 2025-11-13 If response is 429, Too Many Requests, wait
            # a while and then try again. We don't want to omit anyone.
            # (This might induce retry delays for unrecoverable errors such as 404,
            # but we accept that. This way it handles other intermittent errors 
            # as well as 429.)

            # Suppress error codes other than 429 if we will retry - just show the stopwatch (waiting) below, instead
            retry_count += 1            
            if retry_count <= max_retries:
                #if verbose: print(f"\nWaiting {delay} seconds before retry #{retry_count} ... ")
                print(STOPWATCH_ICON,end='', flush=True)                    
                time.sleep(delay) 
                delay *= 2.0  # double the delay for next time if this try fails
            else:
                # not retrying or no more retries; show the error code
                if response: print(f" {WARNING_TRIANGLE_ICON}HTTP {response.status_code}", end='', flush=True)
                break

        # If we get here, we exceeded our max retries. Give up on this call.
        print(f" {WARNING_TRIANGLE_ICON}Unable to complete API call to {url} after {retry_count} retries.")
        return None
        
    def _author_newsletter_count(self, newsletter_name, authors, articles, verbose=VERBOSE_DEFAULT):
        ''' see if we have hit our limit of articles per author-newsletter combo '''
        count=0
        for article in articles:
            if article['newsletter_name']==newsletter_name:
                # this also works if author is unknown; limit to one of these per newsletter, too
                if article['authors']==authors: count += 1
        return count
        
    def _compare_author_name(self, authors, writer_name):
        ''' compare specific full or partial writer name to the list of article authors '''
        match=False
        for author in authors:
            # allow for partial name matches, i.e. writer_name can be 'Nadina'
            # while full author name on the article is '*** Nadina Lisbon ***'
            if writer_name.lower() in author.lower(): match=True
        return match

    def fetch_articles(self, days_back=DEFAULT_DAYS_BACK, use_Substack_API=SUBSTACK_API_DEFAULT, max_retries=MAX_RETRY_COUNT, match_authors=MATCH_AUTHORS_DEFAULT, max_per_author=DEFAULT_PER_AUTHOR, verbose=VERBOSE_DEFAULT):
        """Fetch recent articles from all newsletters"""
        print(f"\n📰 Fetching articles from past {days_back} days...")

        # Use date boundaries (midnight to midnight) not current time
        # Example: If today is Nov 10 at 5pm and days_back=7,
        # include all articles from Nov 4 00:00 onwards, not from Nov 3 5pm
        # TO DO: Allow user specification of exact start datetime and end datetime
        today = datetime.now(timezone.utc).date()
        cutoff_date = datetime.combine(today - timedelta(days=days_back), datetime.min.time()).replace(tzinfo=timezone.utc)

        print(f"   Date range: {cutoff_date.strftime('%Y-%m-%d')} to {today.strftime('%Y-%m-%d')}\n")

        articles = []
        success_count = 0
        entry_count=0

        for i, newsletter in enumerate(self.newsletters, 1):
            try:
                # Include author name if we are going to match on it
                writer_name=newsletter['writer_name']     # KJS partial or full name of writer to match on
                writer_handle=newsletter['writer_handle'] # KJS 2025-11-17 writer handle in Substack
                handle_text = f" @{writer_handle}" if len(writer_handle)>0 else ""
                author_text = f" ({writer_name}{handle_text})" if match_authors and len(writer_name)>0 else ''

                print(f"  [{i}/{len(self.newsletters)}] {newsletter['name']}{author_text} ...", end='', flush=True)

                # Fetch RSS feed; retry if it times out or is overloaded
                headers = {'User-Agent': 'Mozilla/5.0 (compatible; DigestBot/1.0)'}
                response = self._api_call_retries(headers, newsletter['rss_url'], max_retries=max_retries, verbose=verbose)
                if not response:
                    print(f"\n{RED_X_FAILURE_ICON}RSS API call failed with {max_retries} retries; skipping this newsletter")
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

                    # Can't do much without a date
                    if not pub_date:
                        if verbose: 
                            print(f"{WARNING_TRIANGLE_ICON}Warning: Unable to find publication date for RSS entry:\n{entry}")
                        continue

                    # Skip old articles (could break out of RSS reading to speed things up?)
                    if pub_date < cutoff_date:
                        continue

                    # Extract author(s) from RSS feed
                    authors = []
                    if hasattr(entry, 'author') and entry.author:
                        authors.append(entry.author)
                    elif hasattr(entry, 'authors') and entry.authors:
                        authors.extend([a.get('name', a) if isinstance(a, dict) else a for a in entry.authors])
                    elif len(writer_name)>0: 
                        # KJS 2025-11-17 If no byline in article, try using the name of the Newsletter Author if known
                        # Only concern is if more than one named writer is on a newsletter, the first one will always
                        # be credited. Better than no one being credited??
                       authors.append(writer_name)
                       if verbose: print(f"️\n{WARNING_TRIANGLE_ICON}No author name found; defaulting to writer name {writer_name} for newsletter {newsletter['name']}")
                    else:
                        # Some articles don't have bylines or a single known publisher.
                        authors.append('') # ensure authors[0] references will always work

                    # KJS 2025-11-15 If the input CSV has an Author column, match on it (allow partial matches)
                    if match_authors and len(writer_name)>0 and not self._compare_author_name(authors, writer_name):
                        # This author is not the writer we want; skip it
                        #if verbose: print(f" {WARNING_TRIANGLE_ICON}Looking in {newsletter['name']} for {writer_name}, found {authors}; skipping article")
                        continue

                    # KJS 2025-11-18 If we have a limit per newsletter/author, enforce it here. RSS file is always
                    # in descending order by date, so that means we automatically keep the most recent article(s).
                    if max_per_author and self._author_newsletter_count(newsletter['name'], authors, articles, verbose)>=max_per_author:
                        #if verbose: print(f" {WARNING_TRIANGLE_ICON}Limit of {max_per_author} articles exceeded for {authors} in {newsletter['name']}; skipping article")
                        # Keep looking in this newsletter if it's possible that we have multiple authors
                        if match_authors: break;
                        # We're not matching on author name. Go on to the next entry in the RSS file.
                        continue

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
                    title = entry.get('title', '')
                    article = {
                        'title': title,
                        'link': entry.get('link', ''),
                        'summary': self._clean_summary(entry.get('summary', '')),
                        'published': pub_date,
                        'authors': authors,  # List of article author names 
                        'newsletter_name': newsletter['name'], 
                        'newsletter_link': newsletter['url'], 
                        'newsletter_category': newsletter['category'],
                        'writer_name': writer_name, # KJS 2025-11-17  (not necessarily article author; may be blank)
                        'writer_handle': writer_handle, # KJS 2025-11-17 newsletter author handle
                        'word_count': word_count,
                        'comment_count': 0,
                        'reaction_count': 0,
                        'restack_count': 0,
                        # no placeholders for raw_score and score in article yet
                        'filename': '' if len(self.temp_folder)==0 else self._make_unique_temp_filename (title, authors[0], verbose)
                    }

                    # Added 2025-11-13 KJS - before we make API calls, give Substack an extra breather 
                    # to try to minimize 429 errors when processing large lists of newsletters 
                    # 2025-11-18: or using long lookback periods
                    if ((i+entry_count) % 20 == 0): 
                        print(STOPWATCH_ICON,end='', flush=True)
                        time.sleep(5.0)
                    entry_count += 1

                    # Get engagement metrics from HTML, not Substack API
                    # 2025-11-21 Always fetch, and optionally save, the HTML.
                    self._fetch_engagement_from_html(article, max_retries, verbose)

                    # Try to fill in restacks - optionally save the JSON too
                    if use_Substack_API:
                        self._fetch_engagement_metrics_substack_api(article, max_retries, verbose)

                    articles.append(article)
                    article_count += 1
                    print(GREEN_CHECKMARK_ICON, end='', flush=True) # Print a checkmark for each article

                newsletter['article_count']=article_count
                if article_count > 0:
                    print(f" - {article_count} article{'s' if article_count>1 else ''}")
                    success_count += 1
                else:
                    print(f" - (no recent articles)")

            except Exception as e:
                print(f"\n{RED_X_FAILURE_ICON}Error on retrieving newsletter articles for {newsletter}:\n{e}")
                if verbose: traceback.print_exc()
                newsletter['article_count']=-1
                continue

        print(f"\n{GREEN_CHECKMARK_ICON}Fetched {len(articles)} total articles from {success_count} newsletters")
        self.articles = articles
        return articles

    def _fetch_engagement_metrics_substack_api(self, article, max_retries=MAX_RETRY_COUNT, verbose=VERBOSE_DEFAULT):
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

            # KJS added retries on Substack API for engagement metrics
            response = self._api_call_retries(headers, api_url, max_retries=max_retries, verbose=verbose)
            if response:
                post_data = response.json()

                # KJS 2025-11-21 Save API call response as JSON file, if enabled
                self._save_article_json(post_data, article['filename'], verbose=verbose)
                
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
            else:
                if verbose: print(f" {WARNING_TRIANGLE_ICON}Warning: Substack API call for {api_url} failed after {max_retries} retries. No engagement metrics available.")
                
        except Exception as e:
            # Silently fail? engagement metrics are optional
            if verbose: print(f" {WARNING_TRIANGLE_ICON}Warning: exception on engagement metrics API call to Substack for {api_url}:\n{e}")
            pass
            
    def _make_unique_temp_filename (self, title, author, verbose=VERBOSE_DEFAULT):
        ''' Do NOT overwrite an existing file. We could have two articles with the same title
        (e.g. Coming Soon). If it's not unique as is, add the lead author name to it.
        If that fails, add an incrementing number to the file until we get to a unique name.
        Problem: How to keep the JSON and HTML file numbering in sync?
        Solution: Check for existence under both extensions, once, before creating either one.
        '''

        if len(self.temp_folder)==0: return ''  # not saving temp files

        sanitized_author=make_valid_filename (author if len(author)>0 else 'Unknown')
        sanitized_title=make_valid_filename (title) 
        sanitized_filename=sanitized_author+"_"+sanitized_title
        
        number_text=''; number=0
        MAXTRIES=10
        while number < MAXTRIES:
            json_output_path = os.path.join(self.temp_folder,number_text+sanitized_filename+".json")        
            html_output_path = os.path.join(self.temp_folder,number_text+sanitized_filename+".html")        
            full_json_path = Path(json_output_path)
            full_html_path = Path(html_output_path)

            if not full_json_path.exists() and not full_html_path.exists():
                return os.path.join(self.temp_folder,number_text+sanitized_filename) # exclude extension

            # Start adding numbers to the filename.
            number += 1
            number_text=f'{number}_'
            # Try again

        # If we get here, we failed
        if verbose: 
            print(f"{WARNING_TRIANGLE_ICON}Warning: Unable to create unique temp file name for {author} {title} after {MAXTRIES} tries")
        return ''

    def _save_article_json(self, data, filename, indent=4, verbose=VERBOSE_DEFAULT):
        '''Save individual article engagement data from Substack API to JSON file. Assume filename includes folder path. '''
        if len(filename)==0: return False

        # Assume we have pre-checked for safe overwrite outside of this.
        output_path = filename+".json"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=indent, ensure_ascii=False)
            return True
                        
        except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
            if verbose: print(f"\n{WARNING_TRIANGLE_ICON} WARNING: Saving article JSON data to file '{output_path}' failed: \n{e}\n")
            return False

    def _save_article_html(self, html, filename, verbose=VERBOSE_DEFAULT):
        """Save individual article to HTML file"""
        if len(filename)==0: return False

        output_path = filename+".html"
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(html)
            return True
        except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
            if verbose: print(f"\n{WARNING_TRIANGLE_ICON} WARNING: Saving article to file '{output_path}' failed: \n{e}\n")
            return False

    def _fetch_engagement_from_html(self, article, max_retries=DEFAULT_RETRY_COUNT, verbose=VERBOSE_DEFAULT):
        """Fetch engagement metrics by parsing the article page HTML"""
        try:
            headers = {'User-Agent': 'Mozilla/5.0 (compatible; DigestBot/1.0)'}
            # KJS 2025-11-17 Add retry handling here too. Engagement metrics are sort of optional, 
            # but the consequences could be misrepresenting an author's article as having no engagement.
            response = self._api_call_retries(headers, article['link'], max_retries=max_retries, verbose=verbose)
            if not response:
                if verbose: print(f" {WARNING_TRIANGLE_ICON}Warning: HTML page request for {article['link']} failed after {max_retries} retries. No engagement metrics available.")
                return

            # To better support development, provide an option to save a copy of the HTML files we fetch
            self._save_article_html(response.text, article['filename'], verbose=verbose)

            soup = BeautifulSoup(response.text, 'html.parser')

            # Method 1: Parse interactionStatistic meta tag (structured data)
            meta_tag = soup.find('meta', {'property': 'interactionStatistic'})
            if meta_tag and meta_tag.get('content'):
                try:
                    stats = json.loads(meta_tag['content'])
                    for stat in stats:
                        if stat.get('interactionType') == 'https://schema.org/LikeAction':
                            article['reaction_count'] = stat.get('userInteractionCount', 0)
                        elif stat.get('interactionType') == 'https://schema.org/CommentAction':
                            article['comment_count'] = stat.get('userInteractionCount', 0)
                        # restack_count is not available (ShareAction doesn't work).
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

            # KJS 2025-11-22 WIP - TO DO: Save the JSON Preload block as a _HTML.JSON file?
            #json_preloads = soup.find('script', {'window._preloads        = JSON.parse\((*)\)'})
            #if json_preloads:
            #    self._save_article_json(json_preloads, article['filename']+"_html", verbose=verbose)
                                        
        except Exception as e:
            if verbose: print(f" {WARNING_TRIANGLE_ICON}Warning: exception on engagement metrics HTML page request from Substack:\n{e}")
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

    def score_articles(self, use_daily_average=True, normalize=NORMALIZE_DEFAULT, verbose=VERBOSE_DEFAULT):
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
        norm_text=f" with{'' if normalize else 'out'} normalization"
        if use_daily_average:
            print(f"\n📊 Scoring articles using Daily Average model (engagement + length){norm_text} ...")
        else:
            print(f"\n📊 Scoring articles using Standard model (total engagement + length){norm_text} ...")

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
                (article['restack_count'] * RESTACK_WEIGHT)
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

             # KJS 2025-11-16 handle outlier case (eg 400+) skewing all other scores low
            min_score = min(min(raw_scores),100.0)
            max_score = min(max(raw_scores),100.0) 

            # Handle edge case where all scores are the same
            score_range = max_score - min_score
            if score_range == 0:
                for article in self.articles:
                    article['score'] = 50.0  # All get mid-range score
            else:
                # KJS 2025-11-22
                # We may not actually want to normalize the top scores to 100 if all are below 100.
                # We might only want to cap articles exceeding 100 so they don't ruin the curve.
                for article in self.articles:
                    # Normalize to 1-100 range, or use the raw score but cap it
                    capped_score = min(article['raw_score'],100)
                    if normalize:
                        capped_score = ((capped_score - min_score) / score_range) * 99 + 1
                    article['score'] = capped_score

        # Sort by raw score descending (this way if we've normalized
        # more than one high-scoring post and capped them all at 100, 
        # the highest will still come out on top)
        self.articles.sort(key=lambda x: x['raw_score'], reverse=True)

        print(f"{GREEN_CHECKMARK_ICON}Scored {len(self.articles)} articles")

        # Show top 5 scores
        if self.articles:
            print("\n🏆 Top 5 articles:")
            for i, article in enumerate(self.articles[:5], 1):
                now = datetime.now(timezone.utc)
                days_old = (now - article['published']).days  # use max (, 1) here?
                print(f"   {i}. {article['title'][:75]}") # handle unicode chars in article titles
                restack_text = f", {article['restack_count']} restacks" if article['restack_count']>0 else "" 
                author_text = ' & '.join(article['authors'])
                print(f"      In newsletter: {article['newsletter_name']} | by Author(s): {author_text}")
                print(f"      Score: {article['score']:.1f} | "
                      f"{article['reaction_count']} likes, "
                      f"{article['comment_count']} comments"
                      f"{restack_text} | "
                      f"{article['word_count']} words | "
                      f"{days_old}d old ({article['published'].strftime('%Y-%m-%d %H:%M')})\n") # KJS Added actual date published

    def generate_digest_html(self, featured_count, include_wildcards, days_back, scoring_method='daily_average', show_scores=SHOW_SCORES_DEFAULT, normalize=NORMALIZE_DEFAULT, verbose=VERBOSE_DEFAULT):
        """Generate Substack-ready HTML digest with clean formatting"""
        print(f"\n📝 Generating digest HTML...")

        # Select featured articles
        featured = []
        if featured_count>0:
            featured = self.articles[:featured_count]

        # Select wildcard (1 random from next 10)
        wildcards = []
        if include_wildcards>0 and len(self.articles) > featured_count:
            import random
            wildcard_max = min(10*include_wildcards,len(self.articles)-featured_count) # KJS Adjust pool for multiple wildcards
            wildcard_pool = self.articles[featured_count:featured_count + wildcard_max]
            num_wildcards = min(include_wildcards, int(len(wildcard_pool)/2))
            if wildcard_pool:
                for i in range(num_wildcards):
                    wildcard = random.choice(wildcard_pool)
                    wildcards.append(wildcard)

        # Group remaining articles by category
        # TO DO: Take the parameter to be categorized by as a configuration parameter
        # e.g. instead of newsletter_category, maybe author, or no categorization,
        # just in order by score
        categorized = defaultdict(list)
        for article in self.articles:
            if article not in featured and article not in wildcards:
                categorized[article['newsletter_category']].append(article)

        # Build HTML with inline styles (Substack-friendly)
        html_parts = ["<html>","<body>"] 

        # Container with max-width for readability (why not use 100% or EM/VW units?)
        html_parts.append('<div style="font-family: Georgia, serif; max-width: 700px; margin: 0 auto; line-height: 1.7; color: #1a1a1a;">')

        # Header
        now = datetime.now() # in local time, not UTC, for display purposes (switch to UTC?)
        scoring_label = "Daily Average" if scoring_method == 'daily_average' else "Standard"
        lookback_text = f"• {days_back} day lookback" if days_back>0 else ""
        wildcard_text = f"• {len(wildcards)} Wildcard Pick(s) " if len(wildcards)>0 else "" # KJS 2025-11-17 added
        norm_text=f" with{'' if normalize else 'out'} normalization"

        html_parts.append(f'''
        <div style="text-align: center; padding: 40px 20px; margin-bottom: 40px;">
            <h1 style="font-size: 36px; font-weight: 700; color: #1a1a1a; margin: 0 0 10px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif;">Newsletter Digest</h1>
            <div style="font-size: 16px; color: #666; margin-bottom: 8px;">{now.strftime('%A, %B %d, %Y')}</div>
            <div style="font-size: 14px; color: #666; margin-bottom: 8px;">{len(featured)} Featured Articles {wildcard_text}• {len(self.articles)} Total Articles</div>
            <div style="font-size: 13px; color: #888; font-style: italic;">{scoring_label} scoring (engagement + length) {norm_text} {lookback_text} • {len(self.newsletters)} newsletters</div>
        </div>
        ''')
        
        # KJS 2025-11-16 Inline styles for article headers (consider adding id={id} so we can add clickable TOC later)
        h2_style_start='<br> <hr><h2 style="font-size: 24px; font-weight: 700; color: #1a1a1a; margin: 0 0 0 0; font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;">'
        h2_style_end='</h2><hr style="margin-bottom: 10px">'
        # Adding spacing before and after H2 with <p> or <div> or <br> or style padding & margin works well in a normal browser.
        # But Substack ignores padding & margin and does not respect the spacing before or after the end of the H2 with any of 
        # these methods. Haven't yet found a way to make it work well. Will keep experimenting.
        
        # Featured Section
        if featured:
            html_parts.append(f'{h2_style_start}Featured Articles{h2_style_end}')

            for i, article in enumerate(featured, 1):
                html_parts.append(self._format_article_featured(article, number=i))

        # Wildcard Section
        if len(wildcards)>0:
            html_parts.append(f'{h2_style_start}Wildcard Pick{"s" if len(wildcards)>1 else ""}{h2_style_end}')

            for i, article in enumerate(wildcards, 1):
                html_parts.append(self._format_article_featured(article, number=(i if len(wildcards)>1 else None), wildcard=True, verbose=verbose))

        # Categorized Sections
        for category in sorted(categorized.keys()):
            articles = categorized[category]

            if articles:
                html_parts.append(f'{h2_style_start}{category} ({len(articles)}){h2_style_end}') # KJS add category count to title

                # TO DO: If not showing scores, consider grouping by newsletter and then ordering by date descending
                for article in articles:
                    html_parts.append(self._format_article_compact(article,show_scores=show_scores,verbose=verbose))

        html_parts.append('</div>')
        html_parts.append('</body>')
        html_parts.append('</html>')

        return '\n'.join(html_parts)

    def _format_article_line0(self, article, number=None, wildcard=False):
        '''
        KJS 2025-11-16 Refactored line0 formatting out from featured and compact functions
        Makes the article title a hyperlink with mouseover text
        '''

        # Augment title with number and/or wildcard indicator if appropriate
        title_text = article['title']
        if number:
            title_text = f"{number}. {title_text}"
        if wildcard:
            title_text = f"🎲 {title_text}"
        
        line0_style_start='<span style="font-size: 20px; font-weight: 700; line-height: 1.3; margin-bottom: 8px;">'
        line0_style_end='</span>'

        # create title hyperlink; add mouseover text for accessibility
        line0_content = f"<a title=\"{article['title']}\" href=\"{article['link']}\" style=\"color: #1a1a1a; text-decoration: none;\">{title_text}</a>"

        return f"{line0_style_start}{line0_content}{line0_style_end}"
        
    def _format_article_line1(self, article, add_newsletter_links=True, verbose=VERBOSE_DEFAULT):
        ''' KJS 2025-11-13 Refactored line1 formatting out from featured and compact functions
        Handles newsletter name, author name, date (days ago and publication date) '''
        
        ''' Style definitions for line1, shared among featured/wildcard and compact articles '''
        ARTICLE_LINE1_STYLE_START="<span style=\"margin-bottom: 40px; padding: 15px 0; font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', sans-serif; font-size: 18px; color: #666; line-height: 1.6;\">"
        ARTICLE_LINE1_STYLE_END="</span>"

        # First line: Newsletter name, author(s), and date
        #first_line_parts = [article["newsletter_name"]] 
        # KJS 2025-11-16 make newsletter name a hyperlink
        newsletter_name = article['newsletter_name']
        newsletter_url = ''
        for newsletter in self.newsletters:
            if newsletter['name']==newsletter_name:
                newsletter_url = newsletter['url']
                #if verbose: print(f"Matched newsletter {newsletter_name} to url {newsletter_url}")
        if len(newsletter_url)>0 and add_newsletter_links:
            newsletter_link = f"In <a title=\"Newsletter: {newsletter_name}\" href=\"{newsletter_url}\" style=\"color: #1a1a1a; font-weight: bold; text-decoration: none;\">{newsletter_name}</a>"
        else:
            newsletter_link = f"In <b>{newsletter_name}</b>"
        first_line_parts=[f"{newsletter_link}"]

        # KJS Prepare to hyperlink the first author's name to their Substack profile handle
        if article.get('authors') and len(article['authors']) > 0:
            author_text = ' & '.join(article['authors'])
            first_line_parts.append(f"by <b><a style='color: #1a1a1a; font-weight: bold; text-decoration: none;' title='Author: {author_text}'>{author_text}</a></b>")
        # Otherwise author(s) are unknown, maybe no byline in the article.
        # Possible contingency: use the author name and handle from the newsletter, if it's available?

        days_ago = (datetime.now(timezone.utc) - article['published']).days  # use max (, 1) here?

        first_line_parts.append(f" {days_ago}d ago ({article['published'].strftime('%Y-%m-%d %H:%M %Z')})") # KJS Add actual date published (show it's UTC)

        line1_style_start=ARTICLE_LINE1_STYLE_START
        line1_style_end=ARTICLE_LINE1_STYLE_END
        line1_content = f'{" • ".join(first_line_parts)}'

        return f'{line1_style_start}{line1_content}{line1_style_end}'
              
    def _format_engagement_metrics_and_score(self, article, number=None, show_scores=SHOW_SCORES_DEFAULT):
        ''' KJS 2025-11-13 Refactored formatting of engagement metrics out from featured and compact functions '''
        ENGAGEMENT_STYLE_START = '<span style="font-size: 16px; color: #666; line-height: 1.6;">'
        ENGAGEMENT_STYLE_END = '</span>'

        # Add engagement metrics if present and non-zero
        engagement_html = ''
        metrics = []
        if article['reaction_count'] > 0:
            metrics.append(f"{int(article['reaction_count']):,} likes")
        if article['comment_count'] > 0:
            metrics.append(f"{int(article['comment_count']):,} comments")
        if article['restack_count'] > 0:
            metrics.append(f"{int(article['restack_count']):,} restacks")

        engagement_html = ENGAGEMENT_STYLE_START
        if metrics:
            engagement_html += f'{" • ".join(metrics)}'
            
        # Add word count and score
        word_count = int(article.get('word_count', 0))
        if word_count > 0:
            # KJS 2025-11-17 Avoid the leading * if there are no metrics (no likes, comments, or restacks)
            words_line = f'{" • " if len(metrics)>0 else ""}{word_count:,} words'
            engagement_html += words_line
        if show_scores:
            score = article.get('score', 0)
            score_line = f' • Score: {score:.1f}' if score>0 else ''  # KJS 2025-11-17 only show score if non-zero
            engagement_html += score_line
        engagement_html += ENGAGEMENT_STYLE_END

        return engagement_html

    def _format_article_summary(self, article):
        ''' Format article summary (only used on featured and wildcard articles, at present). 
            May be empty; avoid blank line if so. 
        '''
        summary_html = f'<br><span style="font-size: 18px; font-style:italic; line-height: 1.3; color: #1a1a1a; margin-top: 12px;">{article["summary"]}</span>' if article["summary"] else ''
        return summary_html

    def _format_article_featured(self, article, number=None, wildcard=False, verbose=VERBOSE_DEFAULT):
        '''Format a featured article with full details
        Featured articles include numbers or wildcard designators with the article title, and the article summary. 
        They are otherwise the same as compact articles.
        '''

        # Title
        line0_html = self._format_article_line0(article, number, wildcard)

        # First line: Newsletter name, author(s), and date
        line1_html = self._format_article_line1(article, verbose)

        # Build engagement lines (TO DO: Make font size and line height responsive)
        # Add line with engagement metrics and score 
        engagement_html = self._format_engagement_metrics_and_score(article, show_scores=True)        
        # Add summary if available (only for featured and wildcard)
        summary_html = self._format_article_summary(article)

        # Build HTML - treat the title like a header
        return f'''
        <h4>{line0_html}</h4>
        <div>{line1_html}
        <br>{engagement_html}{summary_html}
        <br>&nbsp;</div>
        '''

    def _format_article_compact(self, article, show_scores=SHOW_SCORES_DEFAULT, verbose=VERBOSE_DEFAULT):
        ''' Format a compact article (for category sections) - no numbers, summary, different HTML styling '''

        """Format a compact article with fewer details, no numbering"""
        # Title as hyperlink
        line0_html = self._format_article_line0(article, number=None, wildcard=False)

        # First line: Newsletter name, author(s), and date
        line1_html = self._format_article_line1(article, verbose)

        # Build engagement lines (TO DO: Make font size and line height responsive)
        # Add line with engagement metrics and score 
        engagement_html = self._format_engagement_metrics_and_score(article, show_scores=show_scores)
        
        # No summary for compact

        # Build HTML
        return f'''
        <h4>{line0_html}</h4>
        <div>
        {line1_html}
        <br>{engagement_html}
        <br>&nbsp;
        </div>
        '''

    def _count_article_for_newsletter(self, name, verbose=VERBOSE_DEFAULT):
        ''' count one more article found for a newsletter '''
        for newsletter in self.newsletters:
            if newsletter['name']==name:
                newsletter['article_count'] += 1
                return 1
        if verbose:
            print(f"{WARNING_TRIANGLE_ICON}Logic error: article in newsletter {name} cannot be counted, not found in list")
            print(f"{self.newsletters}")
        return 0
                
    def _read_articles_from_csv(self, csv_path, verbose=VERBOSE_DEFAULT):
        ''' Read digest data from CSV file for reprocessing (reformatting) '''

        articles_df=pd.DataFrame()
        try:
            articles_df = pd.read_csv(csv_path)
        except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
            print(f"\n{RED_X_FAILURE_ICON}ERROR: Reading from CSV digest data file '{csv_path}' failed: \n{e}\n")
            if verbose: traceback.print_exc()
            return (-1)

        if len(articles_df)<1:
            print(f"{RED_X_FAILURE_ICON}Error: No article rows read from CSV digest data file {csv_path}")
            return -1
        if verbose:
            print(f"{GREEN_CHECKMARK_ICON}Read from CSV article file: {articles_df.head()}")
        
        # Sanity check: Maybe this is a newsletter file and they set the runstring flag the wrong way
        if "Newsletter Name" in articles_df.columns and "Website URL" in articles_df.columns:
            print(f"{RED_X_FAILURE_ICON}Error: Newsletter data, not article data, detected in file {csv_path}")
            print(f"Please unset reuse_csv_data to fetch articles for these newsletters, or set --csv_path to specify an article data file from a previous run.")
            return -1
            
        articles=[]
        newsletters=[]
        try:
            # Repopulate the articles object from the dataframe
            for i in range(len(articles_df)):
                
                # Extract article data from file data
                #   Category	Date Published	Authors	Article Link	Newsletter Link	
                #   Summary	Words	Likes	Comments	Restacks	Raw Score	Score
                # 'Article Link' contains article title and link in markdown format
                # 'Newsletter Link' contains newsletter name and url in markdown format

                # KJS 2025-11-17 Incorporate author and handle
                writer_name = str(articles_df.at[i,'Writer Name']).strip()
                writer_handle = str(articles_df.at[i,'Writer Handle']).strip()
                title = str(articles_df.at[i,'Article Title']).strip()
                link = str(articles_df.at[i,'Article URL']).strip()
                name = str(articles_df.at[i,'Newsletter Name']).strip()
                url = str(articles_df.at[i,'Newsletter URL']).strip()      
                authors = str(articles_df.at[i,'Authors']).strip()
                category = str(articles_df.at[i,'Category']).strip()                
                datetime_value = datetime.fromisoformat(articles_df.at[i,'Date Published'])

                # First, add the newsletter if new. Ignore author name for now (we are not matching) and collections.
                self._add_newsletter(name, url, writer_name=writer_name, writer_handle=writer_handle, category=category, collections='', verbose=verbose)  # partially blank

                # Now do the article, and count it
                article = {
                    'title':               title,
                    'link':                link,
                    'summary':             articles_df.at[i,'Summary'].strip(),
                    'published':           datetime_value,
                    'newsletter_name':     name, 
                    'newsletter_link':     url, 
                    'writer_name':         writer_name, 
                    'writer_handle':       writer_handle, 
                    'newsletter_category': category,
                    'authors':             [authors], # only 1 name, put in array (stub for now)
                    'word_count':          int(articles_df.at[i,'Words']),
                    'comment_count':       int(articles_df.at[i,'Comments']),
                    'reaction_count':      int(articles_df.at[i,'Likes']),
                    'restack_count':       int(articles_df.at[i,'Restacks']),
                    'filename':            '',  # unused here
                    'raw_score':           articles_df.at[i,'Raw Score'],
                    'score':               articles_df.at[i,'Score'],
                }
                articles.append(article)            

                # Need to find the right newsletter to bump its count.
                self._count_article_for_newsletter(name, verbose)

        except Exception as e:        
            # Most likely: this isn't a valid saved article data file - one or more column names were not found
            print(f"\n{RED_X_FAILURE_ICON}ERROR: Exception while processing CSV digest data file '{csv_path}': \n{e}\n")
            if verbose: traceback.print_exc()
            return (-1)
       
        print(f"\n{GREEN_CHECKMARK_ICON}Data for {len(articles)} digest articles in {len(self.newsletters)} newsletters read from: {csv_path}")
        self.articles=articles
        return len(self.articles)

    def _save_articles_to_csv(self, csv_digest_file, verbose=VERBOSE_DEFAULT):
        '''Save digest data to CSV file '''
        
        # Save articles to a dataframe
        if not self.articles: 
            print(f"{RED_X_FAILURE_ICON}Error: No articles to save to CSV file {csv_digest_file}")
            return 0
        
        # Ignore len(self.articles)<1 and go ahead & make an empty file in the right format
        # Save the dataframe to the CSV file specified
        articles_df = pd.DataFrame()
        try:
            # Rename and reformat columns, eg the list of authors, and make two links display-ready (markdown-compatible)            
            i=0
            for article in self.articles:
                articles_df.at[i,'Category']        = article['newsletter_category']
                articles_df.at[i,'Date Published']  = article['published'].isoformat()
                articles_df.at[i,'Authors']         = ' & '.join(article['authors'])
                
                articles_df.at[i,'Article Title']   = article['title'] # Store separately so we don't have to re-parse markdown
                articles_df.at[i,'Article URL']     = article['link']
                articles_df.at[i,'Article Link']    = make_markdown_link(article['title'],article['link'])

                articles_df.at[i,'Newsletter Name'] = article['newsletter_name']
                articles_df.at[i,'Newsletter URL']  = article['newsletter_link']
                articles_df.at[i,'Newsletter Link'] = make_markdown_link(article['newsletter_name'],article['newsletter_link'])

                articles_df.at[i,'Writer Name'] = article['writer_name']      # from newsletter CSV file
                articles_df.at[i,'Writer Handle'] = article['writer_handle']  # from newsletter CSV file

                articles_df.at[i,'Summary']   = article['summary']

                articles_df.at[i,'Words']     = int(article['word_count'])
                articles_df.at[i,'Likes']     = int(article['reaction_count'])
                articles_df.at[i,'Comments']  = int(article['comment_count'])
                articles_df.at[i,'Restacks']  = int(article['restack_count'])

                articles_df.at[i,'Raw Score'] = article['raw_score']
                articles_df.at[i,'Score']     = article['score']
                i += 1
        except Exception as e:        
            print(f"\n{RED_X_FAILURE_ICON}EXCEPTION while preparing data to write to CSV article file '{csv_digest_file}': \n{e}\n")
            #if verbose: traceback.print_exc()
            return (-1)
            
        # articles_df is ready to write out
        try:
            # all done; save to file
            articles_df.to_csv(csv_digest_file, index=False)

        except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
            print(f"\n{RED_X_FAILURE_ICON}ERROR: Writing to CSV article file '{csv_digest_file}' failed: \n{e}\n")
            #if verbose: traceback.print_exc()
            return (-1)
        except Exception as e:        
            print(f"\n{RED_X_FAILURE_ICON}EXCEPTION while writing CSV article file '{csv_digest_file}': \n{e}\n")
            #if verbose: traceback.print_exc()
            return (-1)
       
        print(f"\n💾 Article data saved to: {csv_digest_file}.")
        print("   This file can be used for further analysis or to regenerate HTML with setting --reuse_csv_data.")
        return len(self.articles)
        
    def save_digest_html(self, html, filename=OUTPUT_HTML_DEFAULT, verbose=VERBOSE_DEFAULT):
        """Save digest to HTML file"""
        output_path = Path(filename)

        with open(output_path, 'w', encoding='utf-8') as f:  # use outer level exception handling
            f.write(html)

        print(f"\n💾 Digest page saved to: {output_path.absolute()}")
        print(f"\n📋 To use in Substack:")
        print(f"   1. Open {filename} in a browser")
        print(f"   2. Select all (Cmd/Ctrl + A)")
        print(f"   3. Copy (Cmd/Ctrl + C)")
        print(f"   4. Paste into Substack editor")
        print(f"   5. Substack will preserve all formatting!")

        return len(self.articles)

def automated_digest(csv_path, days_back, featured_count, include_wildcards, use_daily_average, scoring_method, show_scores, use_Substack_API, verbose, max_retries, match_authors, max_per_author, output_file, csv_digest_file, reuse_csv_data=REUSE_ARTICLES_DEFAULT, normalize=NORMALIZE_DEFAULT, temp_folder=''):
    ''' Non-Interactive function for digest generation (so it can be scripted and scheduled) '''

    generator = DigestGenerator()
    generator.temp_folder=temp_folder

    if reuse_csv_data:
        # skip some steps (this lets us run and test the scoring and HTML generation offline)
        if verbose: print(f"Skipping Steps 1-4 for newsletter RSS reading and metrics gathering")
        
        result = generator._read_articles_from_csv(csv_path, verbose)
        if verbose: print(f"Result from _read_articles_from_csv: {result}")
        if result <= 0:
            return result
        
    else:
        # Step 2: Load newsletters
        print("Step 2: Load Newsletters")
        print("-" * 80)

        if not generator.load_newsletters_from_csv(csv_path, verbose):
            return -1
        print()

        # Step 3: Fetch articles
        print("Step 3: Fetch Articles")
        print("-" * 80)
        articles = generator.fetch_articles(days_back=days_back, use_Substack_API=use_Substack_API, max_retries=max_retries, match_authors=match_authors, max_per_author=max_per_author, verbose=verbose) # TO DO: Update to handle start date-end date

        if not articles:
            print(f"\n{RED_X_FAILURE_ICON}No articles found! Try increasing the lookback period.")
            return -1

        print()

        # Step 4: Score articles (TO DO: let reuse_csv_data repeat the scoring once the rest is working)
        print("Step 4: Score Articles")
        print("-" * 80)
        generator.score_articles(use_daily_average=use_daily_average, normalize=normalize, verbose=verbose)

        print()

    # Step 5: Generate digest HTML and CSV and save them
    # Save the data on the articles to a dataframe, then to CSV (if option selected by user)
    print("Step 5: Save Digest")
    print("-" * 80)

    # Save CSV data (even if reusing, in case scoring changed)
    if csv_digest_file and len(csv_digest_file)>0:
        print(f"Saving article data to {csv_digest_file}")
        generator._save_articles_to_csv(csv_digest_file, verbose)
        print("-" * 80)
    else:
        if verbose: print(f"No output_file_csv name specified; not saving article data")

    # Now the HTML page, using possibly-new scores and options
    html = generator.generate_digest_html(
        featured_count=featured_count,
        include_wildcards=include_wildcards,
        days_back=days_back,
        scoring_method=scoring_method,
        show_scores=show_scores,
        normalize=normalize,
        verbose=verbose
    )
    result = generator.save_digest_html(html, output_file, verbose=verbose)

    return result

def set_int_arg(arg_name, arg_value, default_value: int, min_value=None, max_value=None):    
    ''' do validity checks (int and within range) and set argument value '''
    if arg_value is None:
        print(f"📧️ Defaulting {arg_name} value to {default_value}") # use GREEN_CHECKMARK_ICON instead?
        return default_value
    try:
        arg_num=int(arg_value)
    except ValueError:
        if len(arg_value)>0:
            print(f"{WARNING_TRIANGLE_ICON}Warning: {arg_name} value {arg_value} not an integer")
        print(f"📧️ Defaulting {arg_name} value to {default_value}") # use GREEN_CHECKMARK_ICON instead?
        return default_value
        
    if (min_value>=0 and arg_num<min_value):
        print(f"{WARNING_TRIANGLE_ICON}Warning: {arg_name} value {arg_value} out of range {min_value} to {max_value}; using min={min_value}")
        return min_value

    if (max_value>=1 and arg_num>max_value):
        print(f"{WARNING_TRIANGLE_ICON}Warning: {arg_name} value {arg_value} out of range {min_value} to {max_value}; using max={max_value}")
        return max_value

    return arg_num

def interactive_cli(reuse_csv_data=False, verbose=VERBOSE_DEFAULT):
    ''' Get all inputs interactively up front '''

    # Skip some of these prompts if we are reusing existing article data
    if reuse_csv_data:
        # Consider adding these as parameters in the CSV file just so we can fetch them back?
        # Days_back goes into the headers of the page, so we sort of need it, or the start-end dates.
        # We also don't know the date the data extraction was run. We could estimate from the
        # latest publication date on all of the articles, but it's likely off by some amount.
        days_back=None 
        use_daily_average=SCORING_CHOICE_DEFAULT
        csv_path = input(f"Path to CSV file with article data (press Enter for '{ARTICLES_CSV_DEFAULT}'): ").strip()
        if not csv_path:
            csv_path = ARTICLES_CSV_DEFAULT
    else:
        csv_path = input(f"Path to CSV file with newsletter list (press Enter for '{CSV_PATH_DEFAULT}'): ").strip()
        if not csv_path:
            csv_path = CSV_PATH_DEFAULT

        days_str = input(f"\nHow many days back to fetch articles? (default={DEFAULT_DAYS_BACK}, max={MAX_DAYS_BACK}): ").strip()
        days_back = set_int_arg("Days Back", days_str, DEFAULT_DAYS_BACK, 1, MAX_DAYS_BACK)
        
        # When reusing articles, we do not currently prompt for other data reading and processing options, like retries.
        # Consider adding later?

    # These prompts pertain to scoring and generating the HTML after the data is fetched, so ask them
    print("\nScoring method:")
    print("  1. Standard - Favors total engagement (50 likes last week > 10 likes today)")
    print("  2. Daily Average - Favors recent articles (10 likes today > 50 likes last week)")
    scoring_choice = input("Choose scoring method (1/2, default: 1): ").strip()
    use_daily_average = scoring_choice == '2'
    scoring_method = 'daily_average' if use_daily_average else 'standard'
    print(f"Using {scoring_method} scoring method")

    featured = input(f"\nHow many Featured Articles? (default={DEFAULT_FEATURED_COUNT}, max={MAX_FEATURED_COUNT}): ").strip()
    featured_count = set_int_arg("Featured Count", featured, DEFAULT_FEATURED_COUNT, 0, MAX_FEATURED_COUNT)

    wildcard = input(f"\nHow many Wildcard Picks? (default={DEFAULT_WILDCARD_PICKS}, max={MAX_WILDCARD_PICKS}): ").strip()
    include_wildcards = set_int_arg("Wildcard Picks", wildcard, DEFAULT_WILDCARD_PICKS, 0, MAX_WILDCARD_PICKS)

    scoring = input("\nShow scores on non-featured articles? (y/n, default: y): ").strip().lower()
    show_scores = (len(scoring)>0 and scoring[0] != 'n')

    output_file = input(f"\nOutput HTML filename (default: {OUTPUT_HTML_DEFAULT}): ").strip()
    if not output_file:
        output_file = OUTPUT_HTML_DEFAULT # TO DO: Include datetimestamp as part of default output filename?
        
    # We do not currently prompt for CSV article data filename in interactive mode. Could add?

    return csv_path, days_back, featured_count, include_wildcards, use_daily_average, show_scores, output_file

def validate_output_file(filename, verbose=VERBOSE_DEFAULT):
    ''' Before pulling data via API calls, pre-test whether output file can be written to '''
    output_file = Path(filename)
    try:
        with open(output_file, 'w', encoding='utf-8') as f:
            if verbose: print(f"💾 Will save digest data to {output_file}")
        return True

    except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
        print(f"\n{RED_X_FAILURE_ICON}ERROR: Unable to initialize output file '{output_file}': \n{e}\n")
        #if verbose: traceback.print_exc()
        return False    

INVALID_FOLDER_CHARS = r'[:*?"<>|]'  # treat \ and / as valid for folder, since we will treat string as a path & subfolders are potentially ok
INVALID_FILE_CHARS = r'[\\/:*?"<>|]' # replace these in the filename

def make_valid_filename (filename):
    ''' change an article title which might have invalid characters in it to a suitable filename '''
    sanitized = re.sub(INVALID_FILE_CHARS, "_", filename.strip())
    return sanitized

def validate_output_folder(folder_name, base_path=".", verbose=VERBOSE_DEFAULT) -> str:
    ''' For temp folder location and, in future, output folder location '''
    ''' Create a subfolder under current base_path if valid and not existing. (OK if it exists) '''
    output_folder = Path(folder_name)

    if re.search(INVALID_FOLDER_CHARS, folder_name): 
        if verbose: print(f"Invalid folder name: {folder_name}")
        return None

    full_path = os.path.join(base_path, folder_name)
    try:
        os.makedirs(full_path, exist_ok=True)
        #if verbose: print(f"💾 Will use folder {full_path}")
        return full_path

    except (FileNotFoundError, IOError, OSError, PermissionError) as e:        
        print(f"\n{RED_X_FAILURE_ICON}ERROR: Unable to initialize output folder '{output_folder}': \n{e}\n")
        #if verbose: traceback.print_exc()
        return None

def change_file_extension(base_filepath, new_extension):
    ''' create new filename based on specified filename - assumes filename HAS an extension you want to replace '''
    base_name, _ = os.path.splitext(base_filepath)
    new_file_path = base_name + "." + new_extension
    return new_file_path

def yesno (flag: bool):
    return 'Yes' if flag else 'No'

def main():
    ''' main(): Handle interactive mode or scriptable runstring '''
    
    # 2025-11-13 KJS Runstring options added. If we have them, use them.
    # Allow interactive mode to be an option.
    parser = argparse.ArgumentParser(description="Generate newsletter digest.")
    # Put these in alphabetical order, except for interactive, to make it easier for users to understand the help text
    parser.add_argument("-i", "--interactive", help=f"Use interactive prompting for inputs.", action="store_true")
    parser.add_argument("-a", "--articles_per_author", help=f"Maximum number of articles to include for each newsletter and author combination. 0=no limit, 1=most recent only, 2-max={MAX_PER_AUTHOR} ok. (Substack RSS file max is {MAX_PER_AUTHOR}.) Default={DEFAULT_PER_AUTHOR}.", type=int, default=DEFAULT_PER_AUTHOR) #, choices=range(0,MAX_PER_AUTHOR+1))
    parser.add_argument("-c", "--csv_path", help=f"Path to CSV file with newsletter list (OR saved article data, with --reuse_CSV_data Y). Default='{CSV_PATH_DEFAULT}'", default=CSV_PATH_DEFAULT)
    parser.add_argument("-d", "--days_back", help=f"How many days back to fetch articles. Default={DEFAULT_DAYS_BACK}, min=1.", type=int, default=DEFAULT_DAYS_BACK)
    parser.add_argument("-f", "--featured_count", help=f"How many articles to feature. Default={DEFAULT_FEATURED_COUNT}, min=0 (none), max={MAX_FEATURED_COUNT}.", type=int, default=DEFAULT_FEATURED_COUNT)
    parser.add_argument("-hs", "--hide_scores", help=f"Hide scores on articles outside the Featured and Wildcard sections", action="store_true")
    parser.add_argument("-nm", "--no_name_match", help=f"Do not use Author column in CSV newsletter file to filter articles (partial matching). Matching is on by default if Author column is in the newsletter file. It has no effect if the cell is blank for a newsletter row.", action="store_true")
    parser.add_argument("-nn", "--no_normalization", help=f"Suppress normalization of final scores to 1-100 range. (Raw scores over 100 are still capped at final score=100 regardless.)", action="store_true")
    parser.add_argument("-oc", "--output_file_csv", help=f"Output CSV filename for digest article data (e.g., '{OUTPUT_CSV_DEFAULT}'). Default=none. Use '.' for a default filename based on csv_path, timestamp, and settings.", default="")
    parser.add_argument("-oh", "--output_file_html", help=f"Output HTML filename (e.g., '{OUTPUT_HTML_DEFAULT}' in interactive mode). Omit or use '.' in runstring for a default name based on csv_path, timestamp, and settings.", default="")
    parser.add_argument("-ra", "--reuse_article_data", help=f"Read article data from CSV Path instead of newsletter data.", action="store_true")
    parser.add_argument("-r", "--retries", help=f"Number of times to retry failed API calls with increasing delays. Default={DEFAULT_RETRY_COUNT}. Retries will be logged as ⏱ .", type=int, default=DEFAULT_RETRY_COUNT) #, choices=range(0,MAX_RETRY_COUNT+1))
    parser.add_argument("-s", "--scoring_choice", help=f"Scoring method: 1=Standard, 2=Daily Average. Default={SCORING_CHOICE_DEFAULT}.",default=SCORING_CHOICE_DEFAULT, choices=['1', '2'])
    parser.add_argument("-t", "--temp_folder", help=f"Subfolder for saving temporary HTML and JSON files (results of API calls), e.g. 'temp'. Default='' (no temp files saved)", default="")
    parser.add_argument("-u", "--use_substack_api", help=f"Use Substack API to get engagement metrics. (Default is to get metrics from HTML (faster, but restack counts are not available)", action="store_true")
    parser.add_argument("-v", "--verbose", help=f"More detailed outputs while program is running.", action="store_true")
    parser.add_argument("-w", "--wildcards", help=f"Number of wildcard picks to include. Default={DEFAULT_WILDCARD_PICKS}, min=0 (none), max={MAX_WILDCARD_PICKS}.", type=int, default=DEFAULT_WILDCARD_PICKS)

    print("=" * 80)
    print("📧 Standalone Newsletter Digest Generator") # if you get an encoding error here, set PYTHONIOENCODING=utf_8 in your environment
    print("=" * 80)
    print()

    # Step 1: Configuration
    print("Step 1: Digest Configuration")
    print("-" * 80)
    print()

    result=0
    try:
        now = datetime.now() # KJS in local time, not UTC, for display and file naming purposes (switch to UTC?)
        run_time = now.strftime('%Y%m%dT%H%M')
        
        args = parser.parse_args()
 
        # Confirm that csv_path file exists; others ok to not exist (can use . for default name)
        csv_path          = args.csv_path.strip()
        output_file       = args.output_file_html.strip()
        csv_digest_file   = args.output_file_csv.strip()
        temp_folder       = args.temp_folder.strip()

        days_back         = set_int_arg("Days Back",      args.days_back,      DEFAULT_DAYS_BACK,      1, MAX_DAYS_BACK)
        featured_count    = set_int_arg("Featured Count", args.featured_count, DEFAULT_FEATURED_COUNT, 0, MAX_FEATURED_COUNT)
        include_wildcards = set_int_arg("Wildcard Picks", args.wildcards,      DEFAULT_WILDCARD_PICKS, 0, MAX_WILDCARD_PICKS)
        max_retries       = set_int_arg("Max Retries",    args.retries,        DEFAULT_RETRY_COUNT,    0, MAX_RETRY_COUNT)
        max_per_author    = set_int_arg("Max Articles Per Author", args.articles_per_author, DEFAULT_PER_AUTHOR, 0, MAX_PER_AUTHOR) 
        
        verbose           = args.verbose
        reuse_csv_data    = args.reuse_article_data
        use_Substack_API  = args.use_substack_api
        match_authors     = not args.no_name_match
        show_scores       = not args.hide_scores
        normalize         = not args.no_normalization
        
        use_daily_average = (args.scoring_choice == '2')

        # KJS file csv_path is dual purpose: It's either a list of newsletters 
        # or a set of previously saved article data.
        # Usage depends on whether reuse_csv_data is set to Y.
        if len(csv_path)<5:
            print(f"{RED_X_FAILURE_ICON}Cannot use {csv_path} as file path for newsletter CSV input or article data. Aborting.")
            return -1

        if reuse_csv_data:
            print(f"Reusing article data from {csv_path}")
            print(f"Ignoring Days Back, Match Authors, Use Substack API, Scoring Method, Normalize, and Max Retries (not relevant)")
        else:
            print(f"Reading newsletter data from {csv_path}")

        # Include days_back, scoring method & normalization, and max_per_author in default output filenames
        default_extension = f"digest{days_back}d_s{2 if use_daily_average else 1}n{yesno(normalize)[0]}_m{max_per_author}.{run_time}"
        
        # Set default HTML output filename based on the CSV input name
        if not output_file or len(output_file) < 5:  
            # use a default name with the feature & wildcard counts
            output_file = change_file_extension(csv_path, default_extension+f".f{featured_count}w{include_wildcards}.html")
        
        # Handle CSV filename defaults (updated KJS)
        if not csv_digest_file or len(csv_digest_file)<1:
            csv_digest_file = ''        # default is no CSV output file
        elif len(csv_digest_file)==1 and csv_digest_file[0]=='.':  # create a default name based on input file name
            csv_digest_file = change_file_extension(csv_path, default_extension+".csv")

        interactive=args.interactive
        if interactive:
            # prompt for key settings (not everything)
            csv_path, days_back, featured_count, include_wildcards, use_daily_average, show_scores, output_file = interactive_cli(reuse_csv_data, verbose=verbose)
            print("\nRunning digest generator with defaults and settings from interactive prompts\n")
        else:
            print("\nRunning digest generator with defaults and settings from runstring.")
            print("(Use --interactive to be prompted.)\n")

        # Make sure both output files can be written to
        if len(output_file) > 0 and not validate_output_file(output_file, verbose):
            return -1

        if len(csv_digest_file) > 0 and not validate_output_file(csv_digest_file, verbose):
            return -1

        if len(temp_folder) > 0:
            if not validate_output_folder(temp_folder, '.', verbose):
                return -1
            #if verbose: print(f"Temp folder {temp_folder} name is ok.")

        scoring_method = ('daily_average' if use_daily_average else 'standard')
        if reuse_csv_data:
            print(f"Will reuse article data from {csv_path} for generating digest HTML.")
        else:
            if not interactive:
                print(f"Will fetch article data via RSS for generating digest HTML.")
                print(f"  List of newsletters: {csv_path}")
                print(f"  Days to look back: {days_back}")
                print(f"  Scoring method? {scoring_method}")

            # These are not currently prompted for, so show the values we're going to use
            print(f"  Match author names against Author column in newsletter file? {yesno(match_authors)}")
            print(f"  Max articles per newsletter and author: {max_per_author if max_per_author>0 else 'No limit'}")
            print(f"  Use Substack API for engagement metrics? {yesno(use_Substack_API)}")
            print(f"  Max retries on Substack RSS feed and API calls? {max_retries}")
            print(f"  Normalize scores? {yesno(normalize)}")
            if len(temp_folder)>0: 
                print(f"  Temp folder for API call results ({'JSON' if use_Substack_API else 'HTML'} files): {temp_folder}")
            else:
                if verbose: print("  Not saving article API call results to a temp folder.")
            print()

        # These parameters are for generating the HTML, so always show them
        print(f"Digest formatting options:")
        feature_text=f"Top {featured_count} based on score" if featured_count>0 else "None"
        wildcard_text=f"{include_wildcards}" if include_wildcards>0 else "None"
        print(f"  Featured Articles: {feature_text}")
        print(f"  Wildcard Articles: {wildcard_text}")
        print(f"  Show scores on non-featured articles? {yesno(show_scores)}")
        print(f"\nOutput file HTML: {output_file}")
        if len(csv_digest_file)>0: 
            print(f"Output file CSV: {csv_digest_file}")
        print()
        
        result=automated_digest(csv_path, days_back, featured_count, include_wildcards, use_daily_average,
                scoring_method, show_scores, use_Substack_API, verbose, max_retries, match_authors,
                max_per_author, output_file, csv_digest_file, reuse_csv_data, normalize, temp_folder)

        if result >= 0:
            temp_status=(f"{result} articles saved to {temp_folder}" if len(temp_folder)>0 else "")
            print("\n" + "=" * 80)
            print(f"{GREEN_CHECKMARK_ICON}Digest generation complete!",temp_status)
            print("=" * 80)
            if verbose: 
                print(f"Result: {result}")
        return result
    
    except KeyboardInterrupt:
        print("\n\n👋 Cancelled by user")
        return 0

    except Exception as e:
        print(f"\n{RED_X_FAILURE_ICON}Error: {e}\n")
        traceback.print_exc()
        return -1
    
if __name__ == '__main__':

    date_format='%Y-%m-%d %H:%M'
    now = datetime.now() # in local time, not UTC, for display purposes
    print("\n" + "*" * 80)
    print(f"Digest generator v{DG_VERSION} starting at {now.strftime(date_format)}\n")
    
    result = main()
    
    now = datetime.now() # in local time, not UTC, for display purposes
    print(f"\nDigest generator v{DG_VERSION} finished at {now.strftime(date_format)}")
    print("*" * 80,"\n")
    sys.exit(result)
