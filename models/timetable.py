from timetable_functions import get_year_start_date
##
## Tables are all signed, but the app isn't currently using record
## versioning. That seems like overkill and much of the damage done in the
## original data was simply because it was in Excel. The tables also turn 
## off cascade delete - we don't want details to disappear if a course
## module or events is removed - but...

## TODO we shouldn't need to delete events - conceal instead

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
                format = lambda row: f"{row.title} {row.firstname} {row.lastname}")

db.define_table('courses',
                Field('fullname', 'string'),
                Field('abbrname', 'string'),
                Field('convenor', 'reference teaching_staff', 
                      ondelete='SET NULL'),
                Field('coconvenor', 'reference teaching_staff', 
                      ondelete='SET NULL'),
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
                       ondelete='SET NULL'))

# TODO blocking events and repeating events (Weds pm and Seminars)
db.define_table('college_dates',
                Field('name', 'string'),
                Field('event_startdate', 'date'),
                Field('event_duration', 'integer'))

db.define_table('freezer',
                Field('is_frozen', 'boolean', default=False))


# Cache the academic year
FIRST_DAY = cache.ram('first_day', lambda : get_year_start_date(), None)
current.FIRST_DAY = FIRST_DAY
