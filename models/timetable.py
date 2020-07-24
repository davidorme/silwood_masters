from gluon.utils import web2py_uuid

##
## Tables are all signed, but the app isn't currently using record
## versioning. That seems like overkill and much of the damage done in the
## original data was simply because it was in Excel. The tables also turn 
## off cascade delete - we don't want details to disappear if a course
## module or events is removed - but...

## TODO we shouldn't need to delete events - conceal instead

# add edit details to each table
db._common_fields.append(auth.signature)

db.define_table('locations',
                Field('title', 'string'),
                Field('capacity', 'integer'),
                Field('celcat_code', 'string'),
                Field('external', 'boolean', default=False),
                format = lambda row: f"{row.title}")

db.define_table('teaching_staff',
                Field('title', 'string'),
                Field('firstname', 'string'),
                Field('lastname', 'string'),
                Field('email', 'string'),
                Field('phone', 'string'),
                Field('specialisation', 'text'),
                Field('external', 'boolean', default=False),
                format = lambda row: f"{row.title} {row.firstname} {row.lastname}")

db.define_table('courses',
                Field('fullname', 'string'),
                Field('abbrname', 'string'),
                Field('convenor', 'reference teaching_staff'),
                Field('coconvenor', 'reference teaching_staff'),
                ondelete='SET NULL',
                format = lambda row: f"{row.abbrname}")

db.define_table('modules',
                Field('uuid', default=web2py_uuid),
                Field('title', 'string'),
                Field('module_week', 'integer'),
                Field('module_dayofweek', 'integer'),
                Field('module_ndays', 'integer'),
                Field('convenor_id', 'reference teaching_staff'),
                Field('description', 'text'),
                Field('aims', 'text'),
                Field('reading', 'text'),
                Field('other_notes', 'text'),
                Field('examstyle', 'string', 
                      requires=IS_EMPTY_OR(IS_IN_SET(['Essay','Computer']))),
                Field('courses', 'list:reference courses', 
                      widget=SQLFORM.widgets.checkboxes.widget),
                ondelete='SET NULL',
                format= lambda row: f"{row.title}")

# TODO don't think we need a uuid here, now that ids are all generated server side
db.define_table('module_events',
                Field('uuid', default=web2py_uuid), 
                Field('module_id', 'reference modules'),
                Field('teacher_id', 'reference teaching_staff'),
                Field('title', 'string'),
                Field('event_type', 'string'),
                Field('description', 'text'),
                Field('event_day', 'integer'),
                Field('start_time', 'time'),
                Field('duration', 'double'),
                Field('courses', 'list:reference courses', 
                      #widget=SQLFORM.widgets.checkboxes.widget
                      ),
                Field('location_id', 'list:reference locations',
                       #widget=SQLFORM.widgets.checkboxes.widget
                       ),
                ondelete='SET NULL')

# TODO blocking events and repeating events (Weds pm and Seminars)
db.define_table('college_dates',
                Field('name', 'string'),
                Field('event_startdate', 'date'),
                Field('event_duration', 'integer'))
