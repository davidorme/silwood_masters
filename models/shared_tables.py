import secrets
from timetabler_functions import get_year_start_date
from marking_functions import get_project_rollover_date, div_checkbox_widget_list_group

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
                Field('token', 'string', default=secrets.token_urlsafe(nbytes=32),
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
                Field('student_access_token', 'string', default=secrets.token_urlsafe(nbytes=32),
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
# - Primarily used by timetabler but used to define three global variables:
#     FIRST_DAY: timetabler first day of autumn term
#     PROJECT_ROLLOVER_DAY: when do current projects and marking become last year's
#     CURRENT_PROJECT_YEAR: what is the academic year.
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

# Calculate the global time variables - don't cache these as the update should be
# immediate when they change and the functions aren't complex. Ideally something should
# watch the relevant entries in the college dates table and update the cache when they
# are changed.

FIRST_DAY = get_year_start_date()
PROJECT_ROLLOVER_DAY = get_project_rollover_date()

# Use the first day to get the current project year: 2021 - 2022 students have an
# academic year of 2021 and will have a project rollover day in Sept 2022.
CURRENT_PROJECT_YEAR = FIRST_DAY.year

# Store FIRST_DAY  so it can be accessed in modules/timetabler_functions.py
current.FIRST_DAY = FIRST_DAY

## Turn on signed tables
db._common_fields.append(auth.signature)

bases = ['Silwood Park (Imperial)', 'South Kensington (Imperial)',
         'Natural History Museum', 'Royal Botanic Gardens, Kew',
         'Zoological Society of London', 'Durrell Wildlife Conservation Trust',
         'Other']

lengths = ['3.5 months', '5 months', '9 months']
avail =  ['Autumn (Sept-Oct)', 'Winter (January)', 'Spring (April-May)']
restrict = ['Ecology Evolution and Conservation',  'Conservation Science',
        'Computational Methods in Ecology and Evolution (MSc)',
        'Computational Methods in Ecology and Evolution (MRes)',
        'Ecological Applications',  'Tropical Forest Ecology MRes',
        'Ecosystem and Environmental Change MRes',
        'Taxonomy and Biodiversity [NHM MSc]',  'Biosystematics [NHM MRes]']

types = ['Fieldwork', 'Social surveys', 'Molecular biology', 'Morphometrics',
         'Bioinformatics', 'Desk-based analysis', 'Lab-based experiments',
         'Mathematical modelling']


db.define_table('projects',
                Field('project_student', 'reference student_presentations',
                      requires= IS_IN_DB(db, 'student_presentations.id', 
                                         "%(student)s, %(course_presentation)s")),
                Field('lead_supervisor', 'reference teaching_staff', 
                      requires= IS_IN_DB(db, 'teaching_staff.id', 
                                         "%(last_name)s, %(first_name)s (%(email)s)")),
                Field('internal_supervisor', 'reference teaching_staff', 
                      requires= IS_NULL_OR(IS_IN_DB(db(db.teaching_staff.is_internal == True),
                                                   'teaching_staff.id', 
                                                   "%(last_name)s, %(first_name)s (%(email)s)"))),
                Field('internal_approval_date', 'datetime', default=None),
                Field('internal_approval_token', 'string', default=None),
                Field('other_supervisors', 'list:reference  teaching_staff', 
                      requires= IS_IN_DB(db, 'teaching_staff.id', 
                                         "%(last_name)s, %(first_name)s (%(email)s)",
                                         multiple=True)),
                Field('project_title', 'string', requires=IS_NOT_EMPTY()),
                Field('project_description', 'text', requires=IS_NOT_EMPTY()),
                Field('project_base', 'string', 
                      requires=[IS_IN_SET(bases), IS_NOT_EMPTY()],
                      widget=SQLFORM.widgets.options.widget),
                Field('project_type', 'list:string', 
                      requires=[IS_IN_SET(types, multiple=True),
                                IS_NOT_EMPTY()],
                      widget = div_checkbox_widget_list_group),
                Field('project_length', 'list:string', 
                      requires=IS_IN_SET(lengths, multiple=True),
                      widget =  div_checkbox_widget_list_group),
                Field('available_project_dates', 'list:string', 
                      requires=IS_IN_SET(avail, multiple=True),
                      widget =  div_checkbox_widget_list_group),
                Field('course_restrictions', 'list:string', 
                      requires=IS_IN_SET(restrict, multiple=True),
                      widget = div_checkbox_widget_list_group),
                Field('requirements', 'text'),
                Field('support', 'text'),
                Field('eligibility', 'text'),
                Field('date_created', 'date'),
                Field('concealed', 'boolean', default=False, required=True))

