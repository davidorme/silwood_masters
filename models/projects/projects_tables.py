from marking_functions import (div_checkbox_widget_list_group)


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
