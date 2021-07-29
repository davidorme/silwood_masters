# -*- coding: utf-8 -*-

import uuid
import datetime
import time

# -------------------------------------------------------------------------
# AppConfig configuration made easy. Look inside private/appconfig.ini
# Auth is for authenticaiton and access control
# -------------------------------------------------------------------------
from gluon.contrib.appconfig import AppConfig
from gluon.tools import Auth, Service, Recaptcha2

# Expose services
service = Service()

# -------------------------------------------------------------------------
# This scaffolding model makes your app work on Google App Engine too
# File is released under public domain and you can use without limitations
# -------------------------------------------------------------------------

if request.global_settings.web2py_version < "2.15.5":
    raise HTTP(500, "Requires web2py 2.15.5 or newer")

# -------------------------------------------------------------------------
# if SSL/HTTPS is properly configured and you want all HTTP requests to
# be redirected to HTTPS, uncomment the line below:
# -------------------------------------------------------------------------
# request.requires_https()

# -------------------------------------------------------------------------
# once in production, remove reload=True to gain full speed
# -------------------------------------------------------------------------
configuration = AppConfig(reload=True)

db = DAL(configuration.get('db.uri'),
         pool_size=configuration.get('db.pool_size'),
         migrate_enabled=configuration.get('db.migrate'),
         check_reserved=['all'])

# Use the database for sessions, rather than spamming the inodes
session.connect(request, response, db)

# Store db and config in the current object so it can be imported by modules
from gluon import current
current.db = db
current.configuration = configuration

# -------------------------------------------------------------------------
# by default give a view/generic.extension to all actions from localhost
# none otherwise. a pattern can be 'controller/function.extension'
# -------------------------------------------------------------------------
response.generic_patterns = [] 
if request.is_local and not configuration.get('app.production'):
    response.generic_patterns.append('*')

# -------------------------------------------------------------------------
# choose a style for forms
# -------------------------------------------------------------------------
response.formstyle = 'bootstrap4_inline'
response.form_label_separator = ''

# -------------------------------------------------------------------------
# (optional) optimize handling of static files
# -------------------------------------------------------------------------
# response.optimize_css = 'concat,minify,inline'
# response.optimize_js = 'concat,minify,inline'

# -------------------------------------------------------------------------
# (optional) static assets folder versioning
# -------------------------------------------------------------------------
# response.static_version = '0.0.0'

# -------------------------------------------------------------------------
# Create ane use an overloaded Auth class that uses our own Mail class
# -------------------------------------------------------------------------

from mailer import Mail

class Auth_Mail(Auth):
    
    def email_reset_password(self, user):
        reset_password_key = str(int(time.time())) + '-' + str(uuid.uuid4())
        link = self.url(self.settings.function,
                        args=('reset_password',), vars={'key': reset_password_key},
                        scheme=True)
        
        d = dict(user)
        d.update(dict(key=reset_password_key, link=link))
        
        mailer = Mail()
        success = mailer.sendmail(to=user.email,
                                  subject=self.messages.reset_password_subject,
                                  text=self.messages.reset_password % d)
        
        if success:
            user.update_record(reset_password_key=reset_password_key)
            return True
        
        return False

# Configure auth to use that new Auth class and to use the admin controller
# and marking_reports index
auth = Auth_Mail(db, 
                 host_names=configuration.get('host.names'),
                 controller='sm_admin',
                 url_index=URL('marking_reports', 'index'))

# -------------------------------------------------------------------------
# create all tables needed by auth, maybe add a list of extra fields
# -------------------------------------------------------------------------
auth.settings.extra_fields['auth_user'] = []
auth.define_tables(username=False, signature=False)
auth.settings.create_user_groups = False

# -------------------------------------------------------------------------
# configure auth policy
# -------------------------------------------------------------------------
auth.settings.registration_requires_verification = False
auth.settings.registration_requires_approval = True
auth.settings.reset_password_requires_verification = True

if configuration.get('recaptcha.use'):
    auth.settings.captcha = Recaptcha2(request,
                                       configuration.get('recaptcha.site_key'),
                                       configuration.get('recaptcha.secret_key'))

# -------------------------------------------------------------------------  
# read more at http://dev.w3.org/html5/markup/meta.name.html               
# -------------------------------------------------------------------------
response.meta.author = configuration.get('app.author')
response.meta.description = configuration.get('app.description')
response.meta.keywords = configuration.get('app.keywords')
response.meta.generator = configuration.get('app.generator')
response.show_toolbar = configuration.get('app.toolbar')

# -------------------------------------------------------------------------
# your http://google.com/analytics id                                      
# -------------------------------------------------------------------------
response.google_analytics_id = configuration.get('google.analytics_id')

# -------------------------------------------------------------------------
# maybe use the scheduler
# -------------------------------------------------------------------------
if configuration.get('scheduler.enabled'):
    from gluon.scheduler import Scheduler
    scheduler = Scheduler(db, heartbeat=configuration.get('scheduler.heartbeat'))


# -------------------------------------------------------------------------
# after defining tables, uncomment below to enable auditing
# -------------------------------------------------------------------------
# auth.enable_record_versioning(db)
