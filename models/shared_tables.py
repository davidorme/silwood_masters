from timetabler_functions import get_year_start_date

## -----------------------------------------------------------------------------
# Email log
# - db table just to record who got emailed what and when. Doesn't record message
#   content since these emails are all from templates - record the template and
#   the dictionary of info used to fill out the template to save bits.
## -----------------------------------------------------------------------------

db.define_table('email_log',
                Field('subject', 'string'),
                Field('email_to', 'text'),
                Field('email_cc', 'text'),
                Field('email_template','string'),
                Field('email_template_dict','json'),
                Field('sent','boolean'),
                Field('status', 'string'),
                Field('message_date','datetime'))

## --------------------------------------------------------------------------------
# SECURITY AND STAFF AUTHENTICATION
# - The staff ae _deliberately_ not all signed up in db.auth_user. We want a curated
#   list of staff that do project supervision and marking and we also want to separate
#   staff in marking roles from the same staff with higher privileges for admin 
#   or timetabling.
# - We also want a low-friction passwordless approach for adding markers - not have
#   to rely on people signing up before we can assign project marking etc. 
# - The security system has evolved. Initially there was a single static access token,
#   which is not ideal. It then used a static token with an emailed 2FA code to confirm,
#   but that is clumsy and caused some (not much) friction. It now uses a single access
#   token but which expires - you can only get in for 60 minutes after the request.
# - All of the security relies on the user email being secure, but so does _anything_
#   that doesn't rely on having a second device and we're not in a position to do that.
## --------------------------------------------------------------------------------

db.define_table('teaching_staff',
                # Field('title', 'string'),
                Field('first_name', 'string', notnull=True),
                Field('last_name', 'string', notnull=True),
                Field('institution', 'string'),
                Field('email', 'string', requires=IS_EMAIL(), notnull=True, unique=True),
                Field('phone', 'string'),
                Field('specialisation', 'text'),
                Field('is_internal', 'boolean', default=True),
                Field('can_supervise', 'boolean', default=True),
                format = lambda row: f" {row.last_name}, {row.first_name}")


db.define_table('magic_links',
                Field('staff_id','reference teaching_staff'),
                Field('token', length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                Field('expires','datetime', 
                      default=datetime.datetime.now() + datetime.timedelta(minutes=60),
                      readable=False, writable=False))

## -----------------------------------------------------------------------------
# Courses
# - A table of the courses
# - A table of coursework presentations to courses, which are things that can
#   be assessed.
## -----------------------------------------------------------------------------

db.define_table('courses',
                Field('fullname', 'string'),
                Field('abbrname', 'string'),
                Field('convenor', 'reference teaching_staff', 
                      ondelete='SET NULL'),
                Field('coconvenor', 'reference teaching_staff', 
                      ondelete='SET NULL'),
                Field('is_active', 'boolean', default=True),
                common_filter = lambda query: db.courses.is_active == True,
                format = lambda row: f"{row.abbrname}")


db.define_table('course_presentations',
                Field('course', 'reference courses'),
                Field('name', 'string'),
                Field('is_active', 'boolean', default=True),
                format = "%(name)s")

## -----------------------------------------------------------------------------
# Students
# - A table of the students - who take courses
# - A table of individual combinations of students and a coursework presentation
#   (which might be multiple presentations per course).
## -----------------------------------------------------------------------------

db.define_table('students',
                Field('student_cid','integer', notnull=True),
                Field('student_first_name','string', notnull=True),
                Field('student_last_name','string', notnull=True),
                Field('student_email','string', notnull=True, requires=IS_EMAIL()),
                Field('student_access_token',length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                Field('course', 'reference courses', notnull=True),
                Field('academic_year', 'integer', notnull=True, default=2021),
                format = '%(student_last_name)s, %(student_first_name)s ')


db.define_table('student_presentations',
                Field('student','reference students', notnull=True),
                Field('academic_year','integer', notnull=True),
                Field('course_presentation','reference course_presentations', notnull=True))

## -----------------------------------------------------------------------------
# Dates
# - Primarily used by timetabler but also need to define the start of term for 
#   identifying recent project proposals. Bit of a sledgehammer/nut, but the FIRST_DAY
#   global variable is already used for timetabling and is the correct thing to use.
## -----------------------------------------------------------------------------

# TODO blocking events and repeating events (Weds pm and Seminars)
db.define_table('college_dates',
                Field('name', 'string'),
                Field('event_startdate', 'date'),
                Field('event_enddate', 'date'),
                Field('event_starttime', 'time'),
                Field('event_duration', 'float'),
                Field('all_day', 'boolean', default=False),
                Field('recurring', 'boolean', default=False),
                Field('recur_end', 'date'))

db.define_table('recurring_events',
                Field('title', 'string'),
                Field('recur_startdate', 'date'),
                Field('recur_enddate', 'date'),
                Field('day_of_week', 'integer'),
                Field('all_day', 'boolean', default=True),
                Field('start_time', 'time'),
                Field('end_time', 'time'))


db.define_table('freezer',
                Field('is_frozen', 'boolean', default=False))

# Cache the academic year
FIRST_DAY = cache.ram('first_day', lambda : get_year_start_date(), None)
current.FIRST_DAY = FIRST_DAY