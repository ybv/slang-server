import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
from tornado import gen
import motor
from passlib.hash import md5_crypt
import ConfigParser
import settings as Settings
from bson.objectid import ObjectId
import hashlib
import requests
import urlparse

requests = requests.Session()

from tornado.options import define, options

define("port", default=8888, help="run on the given port", type=int)

class BaseHandler(tornado.web.RequestHandler):
    @property
    def db(self):
        return self.application.db

    def get_current_user(self):
        if self.get_secure_cookie("shoot_user"):
            return self.get_secure_cookie("shoot_user")
        else:
            return None

#handle a new question
class NewQuestionHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        question_id = self.get_argument("id", None)
        err = self.get_argument("error","")
        if question_id:
            document = yield self.db.questions.find_one({'_id':ObjectId(question_id)},{'_id': False })
            ret = {"status":"ok","post":document}
            self.write_response(200,'application/json',tornado.escape.json_encode(ret))
        else:
            self.render("compose.html",errormessage=err)

    def write_response(self,status,ctype,resp):
        self.set_status(status)
        self.set_header("Content-Type",ctype)
        self.write(resp)

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self):
        question_id = self.get_argument("id", None)
        question_title = self.get_argument("question_title")
        question_desc = self.get_argument("question_desc")
        question_expires_in = int(self.get_argument("question_ttl_mins"))*60
        if question_id:
            self.db.questions.update({'_id':ObjectId(question_id)},{'$set':{'question_title':question_title,'question_desc':question_desc,'deleteIn':question_expires_in}})
        else:
            question_id = yield self.db.questions.insert({'question_title':question_title,'question_desc':question_desc,'deleteIn':question_expires_in})
        self.redirect("/question/?id=" + str(question_id))


class MainHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        email = tornado.escape.xhtml_escape(self.current_user)
        self.render("index.html", email = email)


class AuthLoginHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        errormessage = self.get_argument("error","")
        self.render("login.html", errormessage = errormessage)

    @gen.coroutine
    def check_permission(self, password, email):
        #en_password = bcrypt.encrypt(password)
        try:
            q = {'email':email}
            user_existing = yield self.db['shoot_users'].find_one(q)
        except Exception as e:
            print "exception",e
            raise gen.Return(False)
        else:
            if user_existing and len(user_existing)>0  and md5_crypt.verify(password, user_existing['password']):
                raise gen.Return(True)
            else:
                raise gen.Return(False)

    @gen.coroutine
    def post(self):
        email = self.get_argument("email", "")
        password = self.get_argument("password", "")
        auth = yield self.check_permission(password,email)
        if auth:
            self.set_current_user(email)
            self.redirect(self.get_argument("next", u"/"))
        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Login incorrect")
            self.redirect(u"/auth/login/" + error_msg)

    @gen.coroutine
    def set_current_user(self, user_email):
        if user_email:
            self.set_secure_cookie("shoot_user", tornado.escape.json_encode(user_email))
        else:
            self.clear_cookie("shoot_user")


class AuthLogoutHandler(BaseHandler):
    @gen.coroutine
    def get(self):
        self.clear_cookie("shoot_user")
        self.redirect(self.get_argument("next", "/"))


class AuthSignupHandler(BaseHandler):
    @tornado.gen.coroutine
    def get(self):
        check_mail_msg = self.get_argument("msg",None)
        self.render("signup.html", check_msg = check_mail_msg)

    @gen.coroutine
    def check_user(self, email):
        #en_password = bcrypt.encrypt(password)
        try:
            q = {'email':email,'verified':True}
            user_existing = yield self.db['shoot_users'].find_one(q)
        except Exception as e:
            print "exception",e
            raise gen.Return(False)
        else:
            if user_existing:
                raise gen.Return(True)
            else:
                raise gen.Return(False)

    # hard coding host
    @gen.coroutine
    def send_email(self,name,email,activation_code):
        to_field = name + '<' + email.strip() + '>'
        activation_link = "http://localhost:8888/auth/verify/?act_code="+activation_code
        return requests.post(
            "https://api.mailgun.net/v2/sandbox5b7e7483cc7a4cf2944d11f4bcd65d2a.mailgun.org/messages",
            auth=("api", "key-70deff7942b004e9af160b3bb4463a85"),
            data={"from": "Mailgun Sandbox <postmaster@sandbox5b7e7483cc7a4cf2944d11f4bcd65d2a.mailgun.org>",
              "to": to_field,
              "subject": "Hello Vaibhav Krishna",
              "text": "Congratulations Vaibhav Krishna, you just sent an email with Mailgun!  You are truly awesome!  You can see a record of this email in your logs: https://mailgun.com/cp/log .  You can send up to 300 emails/day "+ activation_link +" from this sandbox server.  Next, you should add your own domain so you can send 10,000 emails/month for free."})


    @gen.coroutine
    def post(self):
        email = self.get_argument("email", "")
        name = self.get_argument("name","")
        user_existing = yield self.check_user(email)

        if user_existing:
            error_msg = u"?error=" + tornado.escape.url_escape("Email Already exists try logging in")
            self.redirect(u"/auth/login/" + error_msg)
        else:
            check_msg = u"?msg=" + tornado.escape.url_escape("Check your email")
            activation_code = hashlib.sha224(email).hexdigest()
            q = { 'email':email, 'verified':False, 'activation_code':activation_code }
            self.db['shoot_users'].insert({'email': email, 'verified':False, 'activation_code':activation_code })
            resp= yield self.send_email(name,email,activation_code)
            print resp
            self.redirect(u"/auth/signup/" + check_msg)


class AuthVerifyHandler(BaseHandler):
    @gen.coroutine
    def set_current_user(self, user_email):
        if user_email:
            self.set_secure_cookie("shoot_user", tornado.escape.json_encode(user_email))
        else:
            self.clear_cookie("shoot_user")


    @tornado.gen.coroutine
    def get(self):
        act_code = self.get_argument("act_code", None)
        if act_code:
            user = yield self.check_user(act_code)
            if user:
                self.db.shoot_users.update({'activation_code':act_code},{'$set':{'verified':True}})
                self.render('verify.html')
        else:
            error_msg = u"?error=" + tornado.escape.url_escape("Login incorrect")
            self.redirect(u"/auth/login/" + error_msg)

    @tornado.gen.coroutine
    def check_user(self,act_code):
        try:
            q = {'activation_code':act_code,'verified':False}
            user_existing = yield self.db['shoot_users'].find_one(q)
        except Exception as e:
            print "exception",e
            raise gen.Return(False)
        else:
            if user_existing:
                raise gen.Return(user_existing)
            else:
                raise gen.Return(False)

    @gen.coroutine
    def post(self):
        referrer_url = self.request.headers.get('Referer')
        origin = self.request.headers.get('Origin')
        parsed = urlparse.parse_qs(referrer_url)
        pwrd = self.get_argument("pwrd", None)
        try:
            act_code = parsed[origin+"/auth/verify/?act_code"][0]
            if not pwrd or not act_code:
                error_msg = u"?error=" + tornado.escape.url_escape("Something went wrong")
                self.redirect(u"/auth/signup/" + error_msg)
            else:
                user = yield self.db.shoot_users.find_and_modify(query={u'activation_code':act_code} ,update={'$set':{'password':md5_crypt.encrypt(pwrd) }  }, full_response= True)
                print user
                self.set_current_user(user['value']['email'])
                self.redirect(self.get_argument("next", u"/"))
        except Exception as e:
            print e
            error_msg = u"?error=" + tornado.escape.url_escape("Something went wrong")
            self.redirect(u"/auth/signup/" + error_msg)


class upVoteHandler(BaseHandler):
    @tornado.web.authenticated
    @tornado.gen.coroutine
    def post(self):
        question_id = self.get_argument("q_id", None)
        upvote_count = self.get_argument("upvotes",1)
        if question_id:
            self.db.questions.update({'_id':ObjectId(question_id)},{'$incr':{'upvotes':int(upvote_count)}})
            ret = {"status":"ok"}
            self.write_response(200,'application/json',tornado.escape.json_encode(ret))
        else:
            ret = {"status":"err"}
            write_response(500,'application/json',ornado.escape.json_encode(ret))

        email = tornado.escape.xhtml_escape(self.current_user)
        self.render("index.html", email = email)

    def write_response(self,status,ctype,resp):
        self.set_status(status)
        self.set_header("Content-Type",ctype)
        self.write(resp)

    @tornado.web.authenticated
    @tornado.gen.coroutine
    def get(self):
        question_id = self.get_argument("q_id", None)
        if question_id:
            document = yield self.db.questions.find_one({'_id':ObjectId(question_id)},{'upvotes': True })
            ret = {"status":"ok","upvotes":document}
            self.write_response(200,'application/json',tornado.escape.json_encode(ret))
        else:
            ret = {"status":"err"}
            write_response(500,'application/json',ornado.escape.json_encode(ret))


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/auth/signup/", AuthSignupHandler),
            (r"/auth/verify/", AuthVerifyHandler),
            (r"/question/", NewQuestionHandler),
            (r"/upvote/", NewQuestionHandler)
        ]
        settings = {
            "template_path":Settings.TEMPLATE_PATH,
            "static_path":Settings.STATIC_PATH,
            "debug":Settings.DEBUG,
            "cookie_secret": Settings.COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers, **settings)

        Config = ConfigParser.ConfigParser()
        Config.read("/etc/shoot.conf")
        uri = Config.get("mongo", "uri")
        c = motor.MotorClient(uri)
        self.db = c['shoot']


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
