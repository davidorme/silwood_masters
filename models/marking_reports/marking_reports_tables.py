from marking_reports_functions import (div_radio_widget, 
                                      div_checkbox_widget, 
                                      div_checkbox_widget_wide)

## --------------------------------------------------------------------------------
## GLOBAL LIST DEFINITIONS
## --------------------------------------------------------------------------------

course_presentation_list = ['EEC MSc', 'EEC MRes Winter', 'EEC MRes Summer', 'TFE MRes',
                            'CMEE MSc','CMEE MRes Mid-term', 'CMEE MRes',
                            'Cons Sci MSc','eeChange MRes', 'EA MSc']

role_list = ['Marker', 'Supervisor']

## Dictionary to map course presentation and marker role onto form template and marking criteria

form_data_dict = {('EEC MSc', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('EEC MRes Winter',  'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('EEC MRes Summer',  'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('TFE MRes', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('CMEE MSc', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('CMEE MRes Mid-term', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('CMEE MRes Final', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('CMEE MRes', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('Cons Sci MSc', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('eeChange MRes',  'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('EA MSc', 'Supervisor'): {'form':'supervisor.json',
                                              'criteria':'Supervisor_Marking_Criteria.pdf'},
                  ('EEC MSc', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('EEC MRes Winter',  'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('EEC MRes Summer',  'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('TFE MRes', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('CMEE MSc', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('CMEE MRes Mid-term', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('CMEE MRes Final', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('CMEE MRes', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('Cons Sci MSc', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('eeChange MRes',  'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'},
                  ('EA MSc', 'Marker'): {'form':'marker.json',
                                              'criteria':'Project_Marking_Criteria.pdf'}}

# Store this in current for use in modules.
from gluon import current
current.form_data_dict = form_data_dict

# An assignment is first created, then set to the marker (becoming Not started).
# Once someone has saved a partial record it becomes Started and then once
# Submitted it becomes readonly to all but admins. Once Released, students are
# able to download it.

status_dict =  {'Created': SPAN('',_class="glyphicon glyphicon-upload",
                                  _style="color:grey;font-size: 1.3em;",
                                  _title='Created'),
                'Not started': SPAN('',_class="glyphicon glyphicon-pencil",
                                  _style="color:red;font-size: 1.3em;",
                                  _title='Not started'),
                'Started': SPAN('',_class="glyphicon glyphicon-edit",
                                  _style="color:orange;font-size: 1.3em;",
                                  _title='Started'),
                'Submitted': SPAN('',_class="glyphicon glyphicon-check",
                                  _style="color:green;font-size: 1.3em;",
                                  _title='Submitted'),
                'Released': SPAN('',_class="glyphicon glyphicon-ok-sign",
                                  _style="color:green;font-size: 1.3em;",
                                  _title='Released')}

grade_options = ['100% (A*)', '95% (A*)', '90% (A*)', '85% (A*)',
                 '80% (A)', '76% (A)', '72% (A)',
                 '68% (B)', '65% (B)', '62% (B)',
                 '58% (C)', '55% (C)', '52% (C)',
                 '48% (D)', '45% (D)', '42% (D)', '35% (D)', '30% (D)', '25% (D)',
                 '20% (D)', '15% (D)', '10% (D)', '5% (D)', '0% (D)']


## --------------------------------------------------------------------------------
## TABLE DEFINITIONS
## --------------------------------------------------------------------------------

db.define_table('markers',
                Field('first_name','string'),
                Field('last_name','string'),
                Field('email', 'string', requires=IS_EMAIL()),
                format='%(first_name)s %(last_name)s')

# This table records what the assignments are and provides access tokens
# to act as locks on individual records. The data field holds a JSON object
# containing the content of the variables listed in the correct report
# template - which is assigned by the combination of the course presentation
# and marker role.

db.define_table('assignments',
                Field('student_cid','integer', notnull=True),
                Field('student_first_name','string', notnull=True),
                Field('student_last_name','string', notnull=True),
                Field('student_email','string', notnull=True, requires=IS_EMAIL()),
                Field('course_presentation','string', 
                      requires=IS_IN_SET(course_presentation_list)),
                Field('year','integer', notnull=True),
                Field('marker','reference markers'),
                Field('marker_role','string', requires=IS_IN_SET(role_list)),
                Field('data','json'),
                Field('due_date','date', notnull=True, requires=IS_DATE()),
                # Access and record fields
                Field('staff_access_token',length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                Field('public_access_token',length=64, default=uuid.uuid4,
                      readable=False, writable=False),
                Field('submission_date','datetime', readable=False, writable=False),
                Field('submission_ip','string', readable=False, writable=False),
                Field('status', requires=IS_IN_SET(list(status_dict.keys())),
                      default='Created', writable=False),
                migrate=False, fake_migrate=True,
                # By default hide previous years,
                common_filter = lambda query: db.assignments.year >= datetime.datetime.now().year)

## -----------------------------------------------------------------------------
## Email log
## - db table just to record who got emailed what and when. Doesn't record message
##   content since these emails are all from templates - record the template and
##   the dictionary of info used to fill out the template to save bits.
## -----------------------------------------------------------------------------

db.define_table('email_log',
                Field('subject', 'string'),
                Field('email_to', 'text'),
                Field('email_cc', 'text'),
                Field('template','string'),
                Field('template_dict','json'),
                Field('sent','boolean'),
                Field('status', 'string'),
                Field('message_date','datetime'))

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
filled_icons = {True: SPAN(_class='glyphicon glyphicon-remove-circle', _style='color:red'),
                False: SPAN(_class='glyphicon glyphicon-ok-circle', _style='color:green'),
                None: SPAN(_class='glyphicon glyphicon-question-sign', _style='color:orange')}

db.project_proposals.project_filled.represent = lambda value, row: filled_icons[value]

## after defining tables, uncomment below to enable auditing
# auth.enable_record_versioning(db)
