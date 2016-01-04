"""Provides helper methods on newspaper's api"""

import json
from newspaper import Article
import requests

# import translation_helper

def convert(url):
    if url.startswith('http://www.'):
        return 'http://' + url[len('http://www.'):]
    if url.startswith('www.'):
        return 'http://' + url[len('www.'):]
    if not url.startswith('http://'):
        return 'http://' + url
    return url

def get_article_text(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.title, article.text

def extract_text_from_link(link):
    clear_title_text = get_article_text(convert(link))
    return clear_title_text
