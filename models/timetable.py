from timetable_functions import get_year_start_date, update_event_record_with_dates
##
## Tables are all signed, but the app isn't currently using record
## versioning. That seems like overkill and much of the damage done in the
## original data was simply because it was in Excel. The tables also turn 
## off cascade delete - we don't want details to disappear if a course
## module or events is removed - but...

## The auth.signature includes an is_active field but this is only visible
## and editable by appadmin and not to any normal user. The course, module
## and events tables include a 'conceal' field and common filters to allow
## user level retirement of details from public view. Courses and modules
## can only be concealed by an admin user, but events can be concealed by 
## registered users, to retain details for following years.

db._common_fields.append(auth.signature)

db.define_table('locations',
                Field('title', 'string'),
                Field('capacity', 'integer'),
                Field('celcat_code', 'string'),
                Field('is_external', 'boolean', default=False),
                format = lambda row: f"{row.title}")

db.define_table('teaching_staff',
                Field('title', 'string'),
                Field('firstname', 'string'),
                Field('lastname', 'string'),
                Field('email', 'string'),
                Field('phone', 'string'),
                Field('specialisation', 'text'),
                Field('is_external', 'boolean', default=False),
                format = lambda row: f" {row.lastname}, {row.firstname}")

db.define_table('courses',
                Field('fullname', 'string'),
                Field('abbrname', 'string'),
                Field('convenor', 'reference teaching_staff', 
                      ondelete='SET NULL'),
                Field('coconvenor', 'reference teaching_staff', 
                      ondelete='SET NULL'),
                Field('conceal', 'boolean', default=False),
                common_filter = lambda query: db.courses.conceal == False,
                format = lambda row: f"{row.abbrname}")

db.define_table('modules',
                Field('title', 'string'),
                Field('convenor_id', 'reference teaching_staff',
                      ondelete='SET NULL'),
                Field('description', 'text'),
                Field('aims', 'text'),
                Field('reading', 'text'),
                Field('other_notes', 'text'),
                Field('examstyle', 'string', 
                      requires=IS_EMPTY_OR(IS_IN_SET(['Essay','Computer']))),
                Field('courses', 'list:reference courses', 
                      widget=SQLFORM.widgets.checkboxes.widget,
                      ondelete='SET NULL'),
                Field('conceal', 'boolean', default=False),
                common_filter = lambda query: db.modules.conceal == False,
                format= lambda row: f"{row.title}")

db.define_table('events',
                Field('module_id', 'reference modules'),
                Field('teacher_id', 'reference teaching_staff',
                      ondelete='SET NULL'),
                Field('academic_week', 'integer'),
                Field('day_of_week', 'integer'),
                Field('start_time', 'time'),
                Field('duration', 'double'),
                Field('title', 'string'),
                Field('event_type', 'string'), # TODO constrain this
                Field('description', 'text'),
                Field('courses', 'list:reference courses', 
                      #widget=SQLFORM.widgets.checkboxes.widget
                      ondelete='SET NULL'),
                Field('location_id', 'list:reference locations',
                       #widget=SQLFORM.widgets.checkboxes.widget
                       ondelete='SET NULL'),
                Field('conceal', 'boolean', default=False),
                common_filter = lambda query: db.events.conceal == False)

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


## Virtual field - can't get this to work

# def module_start(row):
#     """Calculates the start and end date of a module from the module events
#     and inserts it into the record object in place."""
#
#     events = row.events.select()
#     [update_event_record_with_dates(ev) for ev in events]
#
#     if len(events):
#         return min([ev.start for ev in events]).date()
#     else:
#         return current.FIRST_DAY


# db.modules.test = Field.Virtual(lambda row: module_start(row))
