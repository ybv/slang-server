import json
import os

import concurrent.futures
import tornado.ioloop
import tornado.web

from tornado import gen
from tornado.process import Subprocess
from subprocess import PIPE

import newspaper_helper
import translation_helper

thread_pool = concurrent.futures.ThreadPoolExecutor(4)

@gen.coroutine
def run_command(command):
  process = Subprocess([command], stdout=PIPE, stderr=PIPE, shell=True)
  yield process.wait_for_exit() 
  out, err = process.stdout.read(), process.stderr.read()
  print "output", out
  print "err", err


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
    link = self.get_argument('link') if 'link' in self.request.arguments else None
    to_lang = self.get_argument('to_lang') if 'to_lang' in self.request.arguments else None
    clean_text = yield thread_pool.submit(newspaper_helper.extract_text_from_link, link)
    trans_text = yield thread_pool.submit(translation_helper.translate, clean_text, to_lang)
    command = "echo \"{trans}\" | gsutil -h \"Content-Type:text/html; charset=utf-8\" cp - gs://slang-data-store/{link}:{lang}.html".format(trans=trans_text.encode('utf8'), link=link, lang=to_lang.encode('utf8'))
    print command
    run_command(command)
    self.write(trans_text)

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
  lang_data = load_langs('langs.json')
  app = make_app(lang_data)
  app.listen(int(os.environ.get("PORT", 80)))
  tornado.ioloop.IOLoop.current().start()
