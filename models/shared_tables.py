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
                Field('email_template','string'),
                Field('email_template_dict','json'),
                Field('sent','boolean'),
                Field('status', 'string'),
                Field('message_date','datetime'))
