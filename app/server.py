import json
import os

import concurrent.futures
import tornado.ioloop
import tornado.web

from tornado import gen
from gcloud import storage
from tornado.process import Subprocess
from subprocess import PIPE
import hashlib

import newspaper_helper
import translation_helper

thread_pool = concurrent.futures.ThreadPoolExecutor(4)
client = storage.Client('slang-instance')
bucket = client.get_bucket('slang-data')

@gen.coroutine
def save_article(link, lang, content):
  hashed = hashlib.sha1(b'{0}:{1}.html'.format(link, lang))
  hex_dig = hashed.hexdigest()
  blob = bucket.blob(hex_dig)
  print content
  blob.upload_from_string(content, content_type='text/html;charset=utf-8')
  return blob.public_url

def load_langs(filen):
  lang_data = {}
  with open(filen) as data_file:
    lang_data = json.load(data_file)
  lang_data = {v: k for k, v in lang_data.items()}
  return lang_data

class ClearHandler(tornado.web.RequestHandler):
  @tornado.gen.coroutine
  def get(self):
    link = self.get_argument('link') if 'link' in self.request.arguments else None
    ret = yield thread_pool.submit(newspaper_helper.extract_text_from_link, link)
    self.write(ret)

class TransHandler(tornado.web.RequestHandler):

  @tornado.gen.coroutine
  def get(self):
    resp = {}
    link = self.get_argument('link') if 'link' in self.request.arguments else None
    to_lang = self.get_argument('to_lang') if 'to_lang' in self.request.arguments else None

    clean_title, clean_text = yield thread_pool.submit(newspaper_helper.extract_text_from_link, link)

    if clean_title:
      trans_title = yield thread_pool.submit(translation_helper.translate, clean_title, to_lang)
      resp['title'] = trans_title

    trans_text = yield thread_pool.submit(translation_helper.translate, clean_text, to_lang)

    if trans_text:
      resp['text'] = trans_text

    try:
      resp['sharable_link'] = yield save_article(link, to_lang, trans_text)
    except Exception as e:
      print "exception when saving via gsutil", e

    self.write(json.dumps(resp, ensure_ascii=False))

class LangListHandler(tornado.web.RequestHandler):
  @tornado.gen.coroutine
  def get(self):
    self.write(lang_data)

def make_app(lang_data):
  app = tornado.web.Application([
                                 (r"/get_clear_text/", ClearHandler),
                                 (r"/get_trans_text/", TransHandler),
                                 (r"/get_langs/", LangListHandler)
                                 ], lang_data)

  return app

if __name__=="__main__":
  lang_data = load_langs('../langs.json')
  app = make_app(lang_data)
  app.listen(int(os.environ.get("PORT", 80)))
  tornado.ioloop.IOLoop.current().start()
