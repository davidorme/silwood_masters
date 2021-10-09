from marking_functions import (div_radio_widget, 
                                       div_checkbox_widget, 
                                       div_checkbox_widget_wide,
                                       div_checkbox_widget_list_group)

from collections import OrderedDict

## Turn on signed tables
db._common_fields.append(auth.signature)

## --------------------------------------------------------------------------------
## GLOBAL LIST DEFINITIONS
## --------------------------------------------------------------------------------

# An assignment is first created, then set to the marker (becoming Not started).
# Once someone has saved a partial record it becomes Started and then once
# Submitted it becomes readonly to all but admins. Once Released, students are
# able to download it. Arguably this is CSS. Okay, not arguably. It _is_ CSS.

status_dict =  {'Created': SPAN('',_class="fa fa-check",
                                  _style="color:grey;font-size: 1.3em;",
                                  _title='Created'),
                'Not started': SPAN('',_class="fa fa-pencil-square-o",
                                  _style="color:#ca0020;font-size: 1.3em;",
                                  _title='Not started'),
                'Started': SPAN('',_class="fa fa-pencil-square-o",
                                  _style="color:#f4a582;font-size: 1.3em;",
                                  _title='Started'),
                'Submitted': SPAN('',_class="fa fa-pencil-square-o",
                                  _style="color:#0571b0;font-size: 1.3em;",
                                  _title='Submitted'),
                'Released': SPAN('',_class="fa fa-eye",
                                  _style="color:green;font-size: 1.3em;",
                                  _title='Released')}

## --------------------------------------------------------------------------------
## TABLE DEFINITIONS
## --------------------------------------------------------------------------------

#
# Refactor to integrated marking/projects notes and magic_links 
# - db.markers -> db.project_staff?
# - Add fields to db.project_staff: 
#    - Location/Institution. 
#    - Research Interests.
#    - Internal (can supervise as sole)

# - Update authenticate to use magic_link and finesse session expiry and inactivity settings.
# - Update projects to link to project_staff. 
#    - add lead supervisor field and
#    - add lead_is_internal field?
#    - add interal supervisor field then internal
#    - add status: Saved/Available/Filled/Hidden
#   - Cannot publish a project without an internal.
#
#   Provide a review projects link (or allow project_staff a less filtered view
#   of project_proposals), so that they can see _all_ projects including unpublished 
#   ones, so internals can review external projects?

# Links through to replace project database:
#  - Add filled_by field to link to student?
#    This makes a project a specific project in a specific year. 
#  - Add a clone option to my_projects.
#  - Project then needs ability to update - who can change? Simplest to 
#    have this being supervisor, otherwise need student validation
#    and review. Does it actually need _versioning_? Only really to 
#    preserve historical record but could have save with filled mark
#    as hidden and create copy? 
#  - Also needs option to _withdraw_ student. Again - save record but
#    archive? This may need _admin_ approval.

db.define_table('markers',
                Field('first_name','string'),
                Field('last_name','string'),
                Field('email', 'string', requires=IS_EMAIL()),
                Field('is_internal', 'boolean', default=False),
                Field('marker_access_token',length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                format='%(first_name)s %(last_name)s')


# - Add request_magic_link?email=marker@inst.it.ution Throttle this by existing
#   unexpired link 
# - Add table db.magic_links:
#
# db.define_table('magic_links',
#                 Field('staff_id','reference markers'),
#                 Field('token', length=64, default=uuid.uuid4,
#                       readable=False, writable=False),
#                 Field('expires','datetime', default=datetime.datetime.now() + datetime.timedelta(minutes=60),
#                       readable=False, writable=False))
# #
# These tables maintains a editable list courses and marking 'presentations'. This
# is basically a combination of course and coursework.
#
#
# db.define_table('presentations',
#                 Field('course', 'reference courses'),
#                 Field('name', 'string'),
#                 format = "%(name)s")

# This table maintains a list of available marking roles and the form
# and marking criteria associated with each
db.define_table('marking_roles',
                Field('name', 'string', notnull=True),
                Field('marking_criteria', 'string', notnull=True),
                Field('form_file', 'string', notnull=True),
                Field('form_json', 'json', notnull=True),
                format = "%(name)s")

# This table records what the assignments are and provides a public access token
# to act as locks on individual records. Access for markers uses a marker specific
# access token stored in the markers table. The data field holds a JSON object
# containing the content of the variables listed in the correct report
# template which is defined by the marking form.

# db.define_table('students',
#                 Field('student_cid','integer', notnull=True),
#                 Field('student_first_name','string', notnull=True),
#                 Field('student_last_name','string', notnull=True),
#                 Field('student_email','string', notnull=True, requires=IS_EMAIL()),
#                 Field('student_access_token',length=64, default=uuid.uuid4,
#                       readable=False, writable=False),
#                 Field('course', 'reference courses', notnull=True),
#                 format = '%(student_last_name)s, %(student_first_name)s ')
#
# db.define_table('student_presentation',
#                 Field('student','reference students', notnull=True),
#                 Field('course_presentation','reference presentations', notnull=True))


db.define_table('assignments',
                Field('student_presentation', 'reference student_presentations'), 
                Field('marker','reference teaching_staff'),
                Field('marker_role_id','reference marking_roles'),
                Field('assignment_data','json'),
                Field('due_date','date', notnull=True, requires=IS_DATE()),
                Field('submission_date','datetime', readable=False, writable=False),
                Field('submission_ip','string', readable=False, writable=False),
                Field('status', requires=IS_IN_SET(list(status_dict.keys())),
                      default='Created', writable=False),
                #migrate=False, fake_migrate=True,
                # By default hide previous years,
                # common_filter = lambda query: db.assignments.academic_year >= datetime.datetime.now().year
                )


# This table stores data about the files held in sharepoint that are to be provided 
# to markers. Typically, this is thesis files to Markers, but could be any combination
# of presentation and role. The unique id provides a permanent reference to retrieve
# file details from the Sharepoint API

# The order here is a little bit arbitrary, but since the year and role are
# unlikely to change, they come further down the structure

# 'EEC_MSc/2020/Marker/Orme_EEC_MSc_00206010.pdf'

db.define_table('marking_files',
                Field('unique_id', length=64),
                Field('filename', 'string'),
                Field('relative_url', 'string'),
                Field('marker_role_id', 'reference marking_roles'),
                Field('student', 'reference student_presentations'))

# # This version of the table stores data about the files held in Box that are to be provided
# # to markers via BOX. Typically, this is thesis files to Markers, but could be any
# # combination of presentation and role. The directory structure is used to
# # identify the file and then the box unique id provides a permanent reference
# # to retrieve file details.
#
# db.define_table('marking_files_box',
#                 Field('box_id', 'integer'),
#                 Field('filename', 'string'),
#                 Field('filesize', 'integer'),
#                 Field('student', 'reference students'),
#                 Field('academic_year', 'integer'),
#                 Field('presentation_id', 'reference presentations'),
#                 Field('marker_role_id', 'reference marking_roles'))

## -----------------------------------------------------------------------------
## Project proposals
## - db table to capture possible projects for students
## -----------------------------------------------------------------------------

#
# bases = ['Silwood Park (Imperial)', 'South Kensington (Imperial)',
#          'Natural History Museum', 'Royal Botanic Gardens, Kew',
#          'Zoological Society of London', 'Durrell Wildlife Conservation Trust',
#          'Other']
#
# lengths = ['3.5 months', '5 months', '9 months']
# avail =  ['Autumn (Sept-Oct)', 'Winter (January)', 'Spring (April-May)']
# restrict = ['Ecology Evolution and Conservation',  'Conservation Science',
#         'Computational Methods in Ecology and Evolution (MSc)',
#         'Computational Methods in Ecology and Evolution (MRes)',
#         'Ecological Applications',  'Tropical Forest Ecology MRes',
#         'Ecosystem and Environmental Change MRes',
#         'Taxonomy and Biodiversity [NHM MSc]',  'Biosystematics [NHM MRes]']
#
# types = ['Fieldwork', 'Social surveys', 'Molecular biology', 'Morphometrics',
#          'Bioinformatics', 'Desk-based analysis', 'Lab-based experiments',
#          'Mathematical modelling']
#
# db.define_table('project_proposals',
#                 Field('contact_name', 'string', notnull=True),
#                 Field('contact_email', 'string', notnull=True, requires=IS_EMAIL()),
#                 Field('imperial_email', 'string', requires=IS_NULL_OR(IS_EMAIL())),
#                 Field('project_base', 'string', notnull=True),
#                 Field('project_title', 'string', notnull=True),
#                 Field('project_description', 'text', notnull=True),
#                 Field('project_length', 'list:string',
#                       requires=IS_IN_SET(lengths, multiple=True),
#                       widget =  div_checkbox_widget, notnull=True),
#                 Field('available_project_dates', 'list:string',
#                       requires=IS_IN_SET(avail, multiple=True),
#                       widget =  div_checkbox_widget, notnull=True),
#                 Field('project_type', 'list:string',
#                       requires=IS_IN_SET(types, multiple=True),
#                       widget = div_checkbox_widget, notnull=True),
#                 Field('course_restrictions', 'list:string',
#                       requires=IS_IN_SET(restrict, multiple=True),
#                       widget = div_checkbox_widget_wide),
#                 Field('requirements', 'text'),
#                 Field('support', 'text'),
#                 Field('eligibility', 'text'),
#                 Field('date_created', 'date'),
#                 Field('project_filled_token',length=64, default=uuid.uuid4,
#                       readable=False, writable=False),
#                 Field('project_filled', 'boolean', default=False))
#
# db.define_table('projects',
#                 Field('academic_year', 'integer', notnull=True),
#                 Field('lead_supervisor', 'reference markers',
#                       requires= IS_IN_DB(db, 'markers.id',
#                                          "%(last_name)s, %(first_name)s (%(email)s)")),
#                 Field('internal_supervisor', 'reference markers',
#                       requires= IS_IN_DB(db(db.markers.is_internal == True), 'markers.id',
#                                          "%(last_name)s, %(first_name)s (%(email)s)")),
#                 Field('other_supervisors', 'list:reference markers',
#                       requires= IS_IN_DB(db, 'markers.id',
#                                          "%(last_name)s, %(first_name)s (%(email)s)",
#                                          multiple=True)),
#                 Field('project_title', 'string', notnull=True),
#                 Field('project_description', 'text', notnull=True),
#                 Field('project_base', 'string', notnull=True),
#                 Field('project_length', 'list:string',
#                       requires=IS_IN_SET(lengths, multiple=True),
#                       widget =  div_checkbox_widget_list_group, notnull=True),
#                 Field('available_project_dates', 'list:string',
#                       requires=IS_IN_SET(avail, multiple=True),
#                       widget =  div_checkbox_widget_list_group, notnull=True),
#                 Field('project_type', 'list:string',
#                       requires=IS_IN_SET(types, multiple=True),
#                       widget = div_checkbox_widget_list_group, notnull=True),
#                 Field('course_restrictions', 'list:string',
#                       requires=IS_IN_SET(restrict, multiple=True),
#                       widget = div_checkbox_widget_list_group),
#                 Field('requirements', 'text'),
#                 Field('support', 'text'),
#                 Field('eligibility', 'text'),
#                 Field('date_created', 'date'),
#                 Field('project_student', 'reference students'),
#                 Field('course_presentation', 'reference presentations')
#                 )
#
#
# # style the filled status as an icon
# filled_icons = {True: SPAN(_class='fa fa-times-circle',
#                            _style='color:red;font-size: 1.3em;',
#                            _title='Filled'),
#                 False: SPAN(_class='fa fa-check-circle',
#                             _style='color:green;font-size: 1.3em;',
#                             _title='Available'),
#                 None: SPAN(_class='fa fa-question-circle',
#                            _style='color:orange;font-size: 1.3em;',
#                            _title='Unknown')}
#
# db.project_proposals.project_filled.represent = lambda value, row: filled_icons[value]

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)
