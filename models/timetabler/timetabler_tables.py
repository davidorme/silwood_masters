
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

# db.define_table('teaching_staff',
#                 Field('title', 'string'),
#                 Field('firstname', 'string'),
#                 Field('lastname', 'string'),
#                 Field('email', 'string'),
#                 Field('phone', 'string'),
#                 Field('specialisation', 'text'),
#                 Field('is_external', 'boolean', default=False),
#                 format = lambda row: f" {row.lastname}, {row.firstname}")
#
# db.define_table('courses',
#                 Field('fullname', 'string'),
#                 Field('abbrname', 'string'),
#                 Field('convenor', 'reference teaching_staff',
#                       ondelete='SET NULL'),
#                 Field('coconvenor', 'reference teaching_staff',
#                       ondelete='SET NULL'),
#                 Field('conceal', 'boolean', default=False),
#                 common_filter = lambda query: db.courses.conceal == False,
#                 format = lambda row: f"{row.abbrname}")

db.define_table('modules',
                Field('title', 'string'),
                Field('is_series', 'boolean'), # Workshop series, reading groups etc.
                Field('placeholder_week', 'integer'), # If no events, use these two
                Field('placeholder_n_weeks', 'integer', default=1),
                Field('convenors', 'list:reference teaching_staff',
                      requires = IS_IN_DB(db, 'teaching_staff.id', 
                                          db.teaching_staff._format, 
                                          sort=True, multiple=True),
                      ondelete='SET NULL'),
                Field('description', 'text'),
                Field('aims', 'text'),
                Field('reading', 'text'),
                Field('delivery', 'text'),
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
                Field('teacher_id', 'list:reference teaching_staff',
                      requires = IS_IN_DB(db, 'teaching_staff.id', 
                                          db.teaching_staff._format, 
                                          sort=True, multiple=True),
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


