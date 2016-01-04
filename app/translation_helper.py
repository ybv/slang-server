import configparser # pip install configparser
import json
import random
import requests
import urllib

Config = configparser.ConfigParser()
session = requests.Session()

PROVIDERS = ['msft']
AC_REFRESH_COUNT = 10

# count = 0
# ac_map = {}

def get_config(provider, section, key):
  Config.read("config/{p}.ini".format(p=provider))
  return Config.get(section, key)

def _get_ac(provider):
  try:
    ac_url = get_config(provider, 'access_token', 'url')
    pay_load = dict(Config.items('access_token_payload'))
    req_headers = dict(Config.items('access_token_headers'))
    print "pay_load,", pay_load
    print "req_headers,", req_headers
    print "ac_url,", ac_url
    r = session.post(ac_url, data=pay_load, headers=req_headers)
    act = json.loads(r.text)['access_token']
    return act
  except Exception as e:
    print "exception", e

def get_access_token(provider):
  ac = _get_ac(provider)
  return ac
  #   if ac:
  #     ac_map[provider] = ac
  #     return ac
  #   else:
  #     return None

  # elif count < AC_REFRESH_COUNT:
  #   count = count + 1
  #   return ac_map[provider]

  # else:
  #   count = 0
  #   get_access_token(provider)

def get_split_texts(text, cap):
  splits = len(text) / cap;
  if splits <= 1:
    return [text]
  else:
    cursor = 0
    texts = [text[i:i+cap] for i in range(0, len(text), cap)]
    return texts

def _trans_req(provider, text, to_lang, ac_token):
  if not text or text == '':
    return None
  tr_url = get_config(provider, 'service', 'translate_url')
  tr_payload = {'to': to_lang, 'text': text }
  auth_header = get_config(provider, 'service_headers', 'Authorization')
  auth_header = auth_header.format(ac=ac_token)
  tr_header = {'Authorization' : auth_header}
  for k,v in tr_payload.iteritems():
   tr_payload[k] = unicode(v).encode('utf-8')
  req_url = tr_url + '?' + urllib.urlencode(tr_payload)
  print "req ms", req_url
  tr_resp = session.get(req_url, headers=tr_header)
  return tr_resp

def translate(text, lang):
  prov = random.choice(PROVIDERS)
  ac = get_access_token(prov)
  translated_text = ''

  for text in get_split_texts(text, 1000):
    tr_resp = _trans_req(prov, text, lang, ac)

    if not tr_resp:
      tr_resp = _trans_req(prov, 'Could not translate; please try again', lang, ac)
      tr_resp = tr_resp.text.replace('<string xmlns="http://schemas.microsoft.com/2003/10/Serialization/">',"")
      tr_resp = tr_resp.replace("</string>","")
      translated_text = tr_resp
      break

    tr_resp = tr_resp.text.replace('<string xmlns="http://schemas.microsoft.com/2003/10/Serialization/">',"")
    tr_resp = tr_resp.replace("</string>","")
    translated_text += tr_resp

  return translated_text

if __name__ == '__main__':
  translate("hello world")

