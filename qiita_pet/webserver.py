#!/usr/bin/env python

__author__ = "Joshua Shorenstein"
__copyright__ = "Copyright 2013, The QiiTa-pet Project"
__credits__ = ["Joshua Shorenstein", "Antonio Gonzalez",
               "Jose Antonio Navas Molina"]
__license__ = "BSD"
__version__ = "0.2.0-dev"
__maintainer__ = "Joshua Shorenstein"
__email__ = "Joshua.Shorenstein@colorado.edu"
__status__ = "Development"

#login code modified from https://gist.github.com/guillaumevincent/4771570

import tornado.auth
import tornado.escape
import tornado.httpserver
import tornado.ioloop
import tornado.options
import tornado.web
import tornado.websocket
from tornado.options import define, options
from hashlib import sha512
from qiita_pet.settings import (DEBUG, STATIC_PATH, TEMPLATE_PATH,
                                COOKIE_SECRET, SINGLE, COMBINED)
from qiita_pet.app.tasks import delete_job
from qiita_pet.app.analysis import switchboard
from qiita_pet.push import MessageHandler
from qiita_pet.app.utils import MetaAnalysisData
from qiita_pet.app.connections import postgres
from psycopg2.extras import DictCursor
#following only needed for filehandler
from os.path import splitext
from random import randint
from psycopg2 import Error as PostgresError

define("port", default=8888, help="run on the given port", type=int)

metaAnalysis = MetaAnalysisData()


class BaseHandler(tornado.web.RequestHandler):
    def get_current_user(self):
        '''Overrides default method of returning user curently connected'''
        user = self.get_secure_cookie("user")
        if user is None:
            self.clear_cookie("user")
            return ''
        else:
            return user.strip('" ')

    def write_error(self, status_code, **kwargs):
        '''Overrides the error page created by Tornado'''
        from traceback import format_exception
        if self.settings.get("debug") and "exc_info" in kwargs:
            exc_info = kwargs["exc_info"]
            trace_info = ''.join(["%s<br />" % line for line in
                                 format_exception(*exc_info)])
            request_info = ''.join(["<strong>%s</strong>: %s<br />" %
                                    (k, self.request.__dict__[k]) for k in
                                    self.request.__dict__.keys()])
            error = exc_info[1]

            self.render('error.html', error=error, trace_info=trace_info,
                        request_info=request_info,
                        user=self.get_current_user())


class MainHandler(BaseHandler):
    '''Index page'''
    @tornado.web.authenticated
    def get(self):
        username = self.get_current_user()
        SQL = """SELECT DISTINCT analysis_name, analysis_id FROM qiita_analysis
            WHERE qiita_username = %s AND analysis_done = true ORDER BY
            analysis_name"""
        try:
            pgcursor = postgres.cursor(cursor_factory=DictCursor)
            pgcursor.execute(SQL, (username,))
            completed_analyses = pgcursor.fetchall()
            postgres.commit()
            pgcursor.close()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()

        if completed_analyses is None:
            completed_analyses = []

        self.render("index.html", user=username, analyses=completed_analyses)


class AuthCreateHandler(BaseHandler):
    '''User Creation'''
    def get(self):
        try:
            error_message = self.get_argument("error")
        except:
            error_message = ""
        self.render("create.html", user=self.get_current_user(),
                    errormessage=error_message)

    def post(self):
        username = self.get_argument("username", "")
        passwd = sha512(self.get_argument("password", "")).hexdigest()
        created, error = self.create_user(username, passwd)

        if created:
            self.redirect(u"/auth/login/?error=User+created")
        else:
            error_msg = u"?error=" + tornado.escape.url_escape(error)
            self.redirect(u"/auth/create/" + error_msg)

    def create_user(self, username, password):
        if username == "":
            return False, "No username given!"
        if password == sha512("").hexdigest():
            return False, "No password given!"

        # Check to make sure user does not already exist
        SQL = "SELECT count(1) FROM qiita_users WHERE qiita_username = %s"
        try:
            pgcursor = postgres.cursor()
            pgcursor.execute(SQL, (username,))
            exists = pgcursor.fetchone()[0]
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            return False, "Database query error! %s" % str(e)

        if exists:
            return False, "Username already exists!"

        SQL = """INSERT INTO qiita_users (qiita_username, qiita_password)
            VALUES (%s, %s)"""
        try:
            # THIS IS THE ONLY PLACE THAT SHOULD MODIFY THE DB IN THIS CODE!
            # ALL OTHERS GO THROUGH THE MIDDLEWARE!!!!!
            # THIS PROBABLY SHOULD BE MIDDLEWARE TOO!
            pgcursor.execute(SQL, (username, password))
            postgres.commit()
            pgcursor.close()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            return False, "Database set error! %s" % str(e)

        return True, ""


class AuthLoginHandler(BaseHandler):
    '''Login Page'''
    def get(self):
        try:
            error_message = self.get_argument("error")
        # Tornado can raise an Exception directly, not a defined type
        except Exception, e:
            error_message = ""

        self.render("login.html", user=self.get_current_user(),
                    errormessage=error_message)

    def check_permission(self, username, password):
        SQL = """SELECT qiita_password from qiita_users WHERE
            qiita_username = %s"""
        try:
            pgcursor = postgres.cursor()
            pgcursor.execute(SQL, (username,))
            dbpass = pgcursor.fetchone()[0]
            postgres.commit()
            pgcursor.close()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            return False

        if password == dbpass:
            return True

        return False

    def post(self):
        username = self.get_argument("username", "")
        passwd = sha512(self.get_argument("password", "")).hexdigest()
        auth = self.check_permission(username, passwd)
        if auth:
            self.set_current_user(username)
            self.redirect(self.get_argument("next", u"/"))
        else:
            error_msg = u"?error=%s" % \
                tornado.escape.url_escape("Login incorrect")
            self.redirect(u"/auth/login/" + error_msg)

    def set_current_user(self, user):
        if user:
            self.set_secure_cookie("user", tornado.escape.json_encode(user))
        else:
            self.clear_cookie("user")


class AuthLogoutHandler(BaseHandler):
    '''Logout handler, no page necessary'''
    def get(self):
        self.clear_cookie("user")
        self.redirect("/")


class WaitingHandler(BaseHandler):
    '''Waiting Page'''
    @tornado.web.authenticated
    def get(self, analysis):
        username = self.get_current_user()
        SQL = """SELECT analysis_done, analysis_id FROM qiita_analysis WHERE
            qiita_username = %s AND analysis_name = %s"""

        try:
            pgcursor = postgres.cursor(cursor_factory=DictCursor)
            pgcursor.execute(SQL, (username, analysis))
            job_hold = pgcursor.fetchone()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            raise RuntimeError("Analysis info can not be retrieved: %s" %
                               str(e))

        analysis_done = bool(job_hold[0])
        analysis_id = job_hold[1]

        if analysis_done:
            self.redirect('/completed/'+analysis)
        else:
            SQL = """SELECT job_datatype, job_type FROM qiita_job
                WHERE analysis_id = %s"""
            try:
                pgcursor.execute(SQL, (analysis_id,))
                job_hold = pgcursor.fetchall()
                postgres.commit()
                pgcursor.close()
            except PostgresError, e:
                pgcursor.close()
                postgres.rollback()
                raise RuntimeError("Job info can not be retrieved: %s" %
                                   str(e))

            jobs = []
            for j in job_hold:
                jobs.append("%s:%s" % (j[0], j[1]))
            self.render("waiting.html", user=username, analysis=analysis,
                        jobs=jobs)

    @tornado.web.authenticated
    #This post function takes care of actual job submission
    def post(self, page):
        username = self.get_current_user()
        jobs = metaAnalysis.options.keys()
        jobs.sort()
        self.render("waiting.html", user=username,
                    analysis=metaAnalysis.get_analysis(), jobs=jobs)
        # Must call IPython after page call!
        switchboard(username, metaAnalysis)


class RunningHandler(BaseHandler):
    '''Currently running jobs list handler'''
    @tornado.web.authenticated
    def get(self):
        username = self.get_current_user()
        SQL = """SELECT analysis_name, analysis_timestamp FROM qiita_analysis
            WHERE qiita_username = %s AND analysis_done = false"""
        try:
            pgcursor = postgres.cursor(cursor_factory=DictCursor)
            pgcursor.execute(SQL, (username,))
            analyses = pgcursor.fetchall()
            postgres.commit()
            pgcursor.close()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            raise RuntimeError("Job info can not be retrieved: %s" % str(e))

        if analyses is None:
            analyses = []

        self.render("runningmeta.html", user=username, analyses=analyses)


class FileHandler(BaseHandler):
    '''File upload handler'''
    def get(self):
        pass

    @tornado.web.authenticated
    def post(self):
        upfile = self.request.files['file'][0]
        fname = upfile['filename']
        extension = splitext(fname)[1]
        newname = self.get_argument('filename')
        if newname == '':
            newname = ''.join([str(randint(0, 9)) for x in range(0, 10)])
        newname += extension
        output_file = open("uploads/" + newname, 'w')
        output_file.write(upfile['body'])
        output_file.close()
        self.redirect("/")


class ShowJobHandler(BaseHandler):
    '''Completed job page'''
    @tornado.web.authenticated
    def get(self, analysis):
        user = self.get_current_user()
        SQL = """SELECT analysis_id FROM qiita_analysis WHERE
            qiita_username = %s AND analysis_name = %s"""
        try:
            pgcursor = postgres.cursor(cursor_factory=DictCursor)
            pgcursor.execute(SQL, (user, analysis))
            analysis_id = pgcursor.fetchone()[0]
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            raise RuntimeError("Analysis info can not be retrieved: %s" %
                               str(e))

        SQL = "SELECT * FROM qiita_job WHERE analysis_id = %s"
        try:
            pgcursor.execute(SQL, (analysis_id,))
            analysis_info = pgcursor.fetchall()
            postgres.commit()
            pgcursor.close()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            raise RuntimeError("Job info can not be retrieved: %s" % str(e))

        self.render("analysisinfo.html", user=user, analysis=analysis,
                    analysisinfo=analysis_info)

    @tornado.web.authenticated
    def post(self, page):
        analysis = self.get_argument('analysis')
        user = self.get_current_user()
        SQL = "SELECT * FROM qiita_job WHERE analysis_id = %s"
        try:
            pgcursor = postgres.cursor(cursor_factory=DictCursor)
            pgcursor.execute(SQL, (analysis,))
            analysis_info = pgcursor.fetchall()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            raise RuntimeError("Analysis info can not be retrieved: %s" %
                               str(e))

        SQL = "SELECT analysis_name FROM qiita_analysis WHERE analysis_id = %s"
        try:
            pgcursor.execute(SQL, (analysis,))
            name = pgcursor.fetchone()[0]
            postgres.commit()
            pgcursor.close()
        except PostgresError, e:
            pgcursor.close()
            postgres.rollback()
            raise RuntimeError("Analysis info can not be retrieved: %s" %
                               str(e))

        self.render("analysisinfo.html", user=user, analysis=name,
                    analysisinfo=analysis_info)


class DeleteJobHandler(BaseHandler):
    @tornado.web.authenticated
    def post(self):
        user = self.get_current_user()
        analysisid = self.get_argument('analysis')
        delete_job(user, analysisid)
        self.redirect('/')


#ANALYSES and COMBINED lists are set in settings.py
class MetaAnalysisHandler(BaseHandler):
    def prepare(self):
        self.user = self.get_current_user()

    @tornado.web.authenticated
    def get(self, page):
        if page != '1':
            self.write('YOU SHOULD NOT ACCESS THIS PAGE DIRECTLY<br \>')
            self.write("You requested form page " + page + '<br \>')
            self.write('<a href="/">Home</a>')
        else:
            #global variable that is wiped when you start a new analysis
            metaAnalysis = MetaAnalysisData()
            metaAnalysis.set_user(self.user)
            self.render('meta1.html', user=self.user)

    @tornado.web.authenticated
    def post(self, page):
        if page == '1':
            pass
        elif page == '2':
            metaAnalysis.set_analysis(self.get_argument('analysisname'))
            metaAnalysis.set_studies(self.get_arguments('studiesView'))

            if metaAnalysis.get_studies() == []:
                raise ValueError('Need at least one study to analyze.')

            metaAnalysis.set_metadata(self.get_arguments('metadataUse'))

            if metaAnalysis.get_metadata() == []:
                raise ValueError('Need at least one metadata selected.')

            metaAnalysis.set_datatypes(self.get_arguments('datatypeView'))

            if metaAnalysis.get_datatypes() == []:
                raise ValueError('Need at least one datatype selected.')

            self.render('meta2.html', user=self.user,
                        datatypes=metaAnalysis.get_datatypes(), single=SINGLE,
                        combined=COMBINED)

        elif page == '3':
            for datatype in metaAnalysis.get_datatypes():
                metaAnalysis.set_jobs(datatype, self.get_arguments(datatype))

            self.render('meta3.html', user=self.user,
                        analysisinfo=metaAnalysis)

        elif page == '4':
            #set options
            for datatype in metaAnalysis.get_datatypes():
                for analysis in metaAnalysis.get_jobs(datatype):
                    metaAnalysis.set_options(datatype, analysis,
                                             {'Option A': 'default',
                                              'Option B': 'default'})

            self.render('meta4.html', user=self.user,
                        analysisinfo=metaAnalysis)

        else:
            raise NotImplementedError("MetaAnalysis Page "+page+" missing!")


class MockupHandler(BaseHandler):
    def get(self):
        self.render("mockup.html", user=self.get_current_user())


class Application(tornado.web.Application):
    def __init__(self):
        handlers = [
            (r"/", MainHandler),
            (r"/auth/login/", AuthLoginHandler),
            (r"/auth/logout/", AuthLogoutHandler),
            (r"/auth/create/", AuthCreateHandler),
            (r"/waiting/(.*)", WaitingHandler),
            (r"/running/", RunningHandler),
            (r"/consumer/", MessageHandler),
            (r"/fileupload/", FileHandler),
            (r"/completed/(.*)", ShowJobHandler),
            (r"/meta/([0-9]+)", MetaAnalysisHandler),
            (r"/del/", DeleteJobHandler),
            (r"/mockup/", MockupHandler),
        ]
        settings = {
            "template_path": TEMPLATE_PATH,
            "static_path": STATIC_PATH,
            "debug": DEBUG,
            "cookie_secret": COOKIE_SECRET,
            "login_url": "/auth/login/"
        }
        tornado.web.Application.__init__(self, handlers, **settings)


def main():
    tornado.options.parse_command_line()
    http_server = tornado.httpserver.HTTPServer(Application())
    http_server.listen(options.port)
    print "Tornado started on port", options.port
    tornado.ioloop.IOLoop.instance().start()

if __name__ == "__main__":
    main()
