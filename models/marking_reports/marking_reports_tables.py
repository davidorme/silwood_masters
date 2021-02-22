from marking_reports_functions import (div_radio_widget, 
                                      div_checkbox_widget, 
                                      div_checkbox_widget_wide)

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

db.define_table('markers',
                Field('first_name','string'),
                Field('last_name','string'),
                Field('email', 'string', requires=IS_EMAIL()),
                Field('marker_access_token',length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                format='%(first_name)s %(last_name)s')

# This table maintains a editable list of marking 'presentations'. This
# is basically a combination of course and coursework.

db.define_table('presentations',
                Field('name', 'string', notnull=True),
                format = "%(name)s")

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

db.define_table('students',
                Field('student_cid','integer', notnull=True),
                Field('student_first_name','string', notnull=True),
                Field('student_last_name','string', notnull=True),
                Field('student_email','string', notnull=True, requires=IS_EMAIL()),
                Field('student_access_token',length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                Field('course', 'string'),
                format = '%(student_last_name)s, %(student_first_name)s ')


db.define_table('assignments',
                Field('student', 'reference students'), 
                # Field('student_cid','integer', notnull=True),
                # Field('student_first_name','string', notnull=True),
                # Field('student_last_name','string', notnull=True),
                # Field('student_email','string', notnull=True, requires=IS_EMAIL()),
                # Field('course_presentation','string'),
                Field('course_presentation_id','reference presentations'),
                Field('academic_year','integer', notnull=True),
                Field('marker','reference markers'),
                # Field('marker_role','string'),
                Field('marker_role_id','reference marking_roles'),
                Field('assignment_data','json'),
                Field('due_date','date', notnull=True, requires=IS_DATE()),
                # Access and record fields
                # Field('staff_access_token',length=64, default=uuid.uuid4,
                #      readable=False, writable=False),
                # Field('public_access_token',length=64, default=uuid.uuid4,
                #      readable=False, writable=False),
                Field('submission_date','datetime', readable=False, writable=False),
                Field('submission_ip','string', readable=False, writable=False),
                Field('status', requires=IS_IN_SET(list(status_dict.keys())),
                      default='Created', writable=False),
                #migrate=False, fake_migrate=True,
                # By default hide previous years,
                common_filter = lambda query: db.assignments.academic_year >= datetime.datetime.now().year)

## -----------------------------------------------------------------------------
## Project proposals
## - db table to capture possible projects for students
## -----------------------------------------------------------------------------


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

db.define_table('project_proposals',
                Field('contact_name', 'string', notnull=True),
                Field('contact_email', 'string', notnull=True, requires=IS_EMAIL()),
                Field('imperial_email', 'string', requires=IS_NULL_OR(IS_EMAIL())),
                Field('project_base', 'string', notnull=True),
                Field('project_title', 'string', notnull=True),
                Field('project_description', 'text', notnull=True),
                Field('project_length', 'list:string', 
                      requires=IS_IN_SET(lengths, multiple=True),
                      widget =  div_checkbox_widget, notnull=True),
                Field('available_project_dates', 'list:string', 
                      requires=IS_IN_SET(avail, multiple=True),
                      widget =  div_checkbox_widget, notnull=True),
                Field('project_type', 'list:string', 
                      requires=IS_IN_SET(types, multiple=True),
                      widget = div_checkbox_widget, notnull=True),
                Field('course_restrictions', 'list:string', 
                      requires=IS_IN_SET(restrict, multiple=True),
                      widget = div_checkbox_widget_wide),
                Field('requirements', 'text'),
                Field('support', 'text'),
                Field('eligibility', 'text'),
                Field('date_created', 'date'),
                Field('project_filled_token',length=64, default=uuid.uuid4, 
                      readable=False, writable=False),
                Field('project_filled', 'boolean', default=False))

# style the filled status as an icon
filled_icons = {True: SPAN(_class='fa fa-times-circle',
                           _style='color:red;font-size: 1.3em;',
                           _title='Filled'),
                False: SPAN(_class='fa fa-check-circle', 
                            _style='color:green;font-size: 1.3em;',
                            _title='Available'),
                None: SPAN(_class='fa fa-question-circle', 
                           _style='color:orange;font-size: 1.3em;',
                           _title='Unknown')}

db.project_proposals.project_filled.represent = lambda value, row: filled_icons[value]

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)
