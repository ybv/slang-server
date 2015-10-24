"""Provides helper methods on newspaper's api"""

import json
from newspaper import Article
import requests

# import translation_helper

def get_article_text(url):
    article = Article(url)
    article.download()
    article.parse()
    return article.title, article.text

def extract_text_from_link(link):
    clear_title_text = get_article_text(link)
    return clear_title_text
