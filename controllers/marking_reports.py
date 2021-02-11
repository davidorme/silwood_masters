# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

import datetime
import io
import os
import csv
import itertools
import random
import simplejson as json
from marking_reports_functions import (create_pdf, release, distribute,
                                      zip_pdfs, download_grades, 
                                      query_report_marker_grades)

import markdown # gluon provides MARKDOWN but lacks extensions.
from mailer import Mail
from gluon.storage import Storage

def index():

    return dict()

def help():
    
    filepath = os.path.join(request.folder, 'static', 'docs', 'marking_reports_help.md')
    
    with open(filepath, encoding="utf-8-sig") as help_file:
        
        # OK - this is a hack. Simply reading and displaying static content from MD is
        # straightforward but now there is a dynamic element from the config. The right
        # way to do this would be either to write a markdown generic.view handler or
        # move the page to HTML and use the templating. But this is quicker and maintains
        # the MD for mostly static use.
        
        help_doc = help_file.read()
        help_doc = help_doc.replace('REPORT_FOLDER.LINK', configuration.get('report_drive.link'))
        help_doc = XML(markdown.markdown(help_doc))
    
    return dict(help_doc=help_doc)


## --------------------------------------------------------------------------------
## Expose the wiki - see models/db.py for customisations and notes
## --------------------------------------------------------------------------------

def wiki():
    
    if not request.args:
        slug = 'index'
    else:
        slug = request.args[0]
    
    # Try and get the content page
    content_row = db(db.wikicontent.slug == slug).select().first()
    
    if content_row is not None:
        # Get the main page content
        content = XML(markdown.markdown(content_row.wikicontent, extensions=['extra']))
        
        # Get the ToC
        toc_row = db(db.wikicontent.slug == content_row.toc_slug).select().first()
        if toc_row is not None:
            toc = XML(markdown.markdown(toc_row.wikicontent, extensions=['extra']))
            ftoc = FoldingTOC()
            ftoc.feed(toc)
            toc = XML(ftoc.get_toc())
        else:
            toc = 'Unknown toc slug'
    
    else:
        content = 'Unknown wiki slug'
        toc = 'Unknown toc slug'
    
    return dict(toc=toc, content=content)


def wikimedia():
    """
    Simple controller to stream a file from the wikimedia table to a client
    """

    media = db(db.wikimedia.slug == request.args[0]).select().first()
    
    if media is not None:
        path = os.path.join(request.folder, 'uploads', media.mediafile)
        response.stream(path)

@auth.requires_membership('wiki_editor')
def manage_wikimedia():
    """
    SQLFORM.grid interface to the contents of the wikimedia table
    """

    grid = SQLFORM.grid(db.wikimedia, create=True, csv=False)
    
    return dict(grid=grid)

@auth.requires_membership('wiki_editor')
def manage_wikicontent():
    """
    SQLFORM.grid interface to the contents of the wikicontent table
    """
    
    grid = SQLFORM.grid(db.wikicontent, create=True, csv=False)
    
    return dict(grid=grid)


# TODO - move this into the module when the site is a bit quieter!
from html.parser import HTMLParser 

class FoldingTOC(HTMLParser):
    """
    This parser scans html and inserts ids, classes and spans to turn
    <ul> or <ol> into a click to expand table of contents tree. The
    layout_wiki.html file contains JS and CSS to make it work.
    """
    
    def __init__(self):
        super().__init__()
        self.content = []
        self.depth = 0
        self.last_li_index = 0

    def handle_starttag(self, tag, attrs): 

        if tag in ['ul', 'ol']:
            if self.depth == 0:
                self.content.append(f'<{tag.upper()} id="root">')
            else:
                self.content.append(f'<{tag.upper()} class="nested">')
                self.content[self.last_li_index] = '<LI><SPAN class="caret"></SPAN>'
            self.depth += 1
        
        elif tag == 'li':
            self.content.append('<LI><SPAN class="end"></SPAN>')
            self.last_li_index = len(self.content) - 1
        
        else:
            self.content.append(self.get_starttag_text())
        
    def handle_data(self, data): 
        self.content.append(data)
    
    def handle_endtag(self, tag):
        if tag in ['ul', 'ol']:
            self.depth -= 1
        
        self.content.append(f'</{tag.upper()}>')
    
    def get_toc(self):
        
        return ''.join(self.content)


# ---- action to server uploaded static content (required) ---
@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)
    

## --------------------------------------------------------------------------------
## MARKERS DATABASE
## --------------------------------------------------------------------------------

@auth.requires_membership('admin')
def markers():
    
    # don't allow deleting as the referencing to project marks will 
    # drop referenced rows from marking tables
    form = SQLFORM.grid(db.markers, 
                        csv=False,
                        deletable=False)
    
    return dict(form=form)


## --------------------------------------------------------------------------------
## MARKING ASSIGNMENTS
## - ADMIN FUNCTIONS
## --------------------------------------------------------------------------------

@auth.requires_membership('admin')
def new_assignment():
    
    db.assignments.status.readable = False
    db.assignments.assignment_data.readable = False
    db.assignments.assignment_data.writable = False
    
    db.assignments.marker.requires = IS_IN_DB(db, 'markers.id', 
                                              '%(last_name)s, %(first_name)s (%(email)s)')
    
    form = SQLFORM(db.assignments)
    
    if form.process().accepted:
        response.flash = 'Assignment created'
        redirect(URL('assignments'))
    
    return dict(form=form)


@auth.requires_membership('admin')
def assignments():
    
    # look for the 'all' variable to allow the system to show older records.
    if 'all' in request.vars.keys():
        db.assignments._common_filter = None
    
    # reduce the set of fields shown in the grid
    db.assignments.id.readable = False
    db.assignments.student_email.readable = False
    db.assignments.student_first_name.readable = False
    db.assignments.student_cid.readable = False
    db.assignments.assignment_data.readable = False
    
    # and edit representations
    db.assignments.student_last_name.represent =  lambda id, row: row.student_last_name + ', ' + row.student_first_name
    db.assignments.status.represent = lambda id, row: status_dict[row.status]
    
    # link to a non-default new edit page
    links = [dict(header = 'Report', 
                  body = lambda row: A('View',_class='button btn btn-secondary',
                                       _href=URL("marking_reports", "write_report", 
                                                 vars={'record': row.id, 
                                                       'staff_access_token':row.staff_access_token}))),
             dict(header = 'Assignment', 
                  body = lambda row: A('Edit',_class='button btn btn-secondary',
                                       _href=URL("marking_reports", "edit_assignment", args=row.id)))]
    
    # create the SQLFORM grid to show the existing assignments
    # and set up actions to be applied to selected rows - these
    # are powered by action functions defined below
    grid = SQLFORM.grid(db.assignments,
                        csv=False,
                        deletable=False,
                        create=False,
                        details=False,
                        editable=False,
                        links=links,
                        headers= {'assignments.student_last_name': 'Student'},
                        selectable = [('Release to students', lambda ids: release(ids)), 
                                      ('Send to markers', lambda ids: distribute(ids)), 
                                      ('Download Confidential PDFs',lambda ids: zip_pdfs(ids, confidential=True)), 
                                      ('Download Public PDFs',lambda ids: zip_pdfs(ids)), 
                                      ('Download Grades',lambda ids: download_grades(ids))],
                        paginate = 50)
    
    # Edit the HTML of the web2py table, as long as a search hasn't created a set with no records
    if grid.element('div.web2py_counter').components != ['']:
        # insert a select all checkbox and the java to power it
        grid.element('th').insert(0, CAT(LABEL(INPUT(_type='checkbox', _id='checkAll'), XML('&nbsp;'), 'All'), XML('&nbsp;')*3))
        grid.append(SCRIPT('''$("#checkAll").change(function () {
                                $("[name='records']").prop('checked', $(this).prop("checked"));
                              });'''))
        # remove the submit buttons from the button and reinsert with nicer styling at the top of the table form
        table_start = grid.element('div.web2py_htmltable')
        buttons = (("submit_1", "Send to markers"),
                   ("submit_0", "Release to students"),
                   ("submit_2", "Download Confidential PDFs"),
                   ("submit_3", "Download Public PDFs"),
                   ("submit_4", "Download Grades"))
        for b in buttons:
            grid.element("[name=" +  b[0]+ "]", replace=None)
            table_start.insert(0, INPUT(_name=b[0], _type='submit', _value=b[1], 
                                        _style='padding:5px 15px;margin:10px;background:#6C757D;color:white'))
    
    # old records, turning off the common filter
    old_count = db(db.assignments.academic_year < datetime.datetime.now().year,
                   ignore_common_filters=True).count()
    
    return dict(form=grid, old_count=old_count)


@auth.requires_membership('admin')
def edit_assignment():
    
    db.assignments.assignment_data.readable = False
    db.assignments.assignment_data.writable = False
    
    db.assignments.marker.requires = IS_IN_DB(db, 'markers.id', 
                                              '%(last_name)s, %(first_name)s (%(email)s)')
    
    record = db.assignments[request.args[0]]
    
    db.assignments.marker.requires = IS_IN_DB(db, 'markers.id', '%(last_name)s, %(first_name)s (%(email)s)')
    
    if record.status in ['Created', 'Not started']:
        delete_ok = True
    else:
        delete_ok = False
    
    form = SQLFORM(db.assignments,
                   deletable=delete_ok,
                   record=record)
    
    if form.process(onvalidation=submit_validation).accepted:
        redirect(URL('assignments'))
    
    return dict(form = form)


@auth.requires_membership('admin')
def load_assignments():
    
    form = FORM(DIV(DIV('Upload File:', _class='col-sm-2'),
                    DIV(INPUT(_type='file', _name='myfile', id='myfile', 
                              requires=IS_NOT_EMPTY()), _class='col-sm-6'), 
                    DIV(INPUT(_type='submit',_value='Upload', _style='padding:5px 15px',
                              _class='btn btn-primary')
                        ,_class='col-sm-2'),
                    _class='row'))
    
    if form.accepts(request.vars):
        
        # get the data from the request, converting from uploaded bytes into StringIO
        data = io.StringIO(request.vars.myfile.value.decode('UTF-8-SIG'))
        data = csv.DictReader(data)
        
        # create an html upload report as the function runs
        html = ''
        
        # check the headers
        headers = data.fieldnames
        required = ['student_cid', 'student_first_name', 'student_last_name', 'student_email',
                    'course_presentation', 'academic_year', 'marker_email', 'due_date',
                    'marker_last_name', 'marker_first_name', 'marker_role']
        
        missing_headers = set(required).difference(headers)
        
        if len(missing_headers) > 0:
            
            html = CAT(html,
                       H2('Missing fields in file'),
                       P('These fields are missing from the upload file: ', ', '.join(missing_headers)))
        
        # extract the contents into a big list of dictionaries to work with
        # rather than having an iterator that runs through once
        data = [row for row in data]
        
        # - repackage the data into fields to do checks
        fields = {key:[item[key] for item in data] for key in headers}
        
        # - roles are recognized?
        unknown_roles = set(fields['marker_role']).difference(set(role_list))
        
        if len(unknown_roles) > 0:
            html = CAT(html,
                       H4('Unknown marking roles'),
                       P('These roles are found in the file but are not recognized: '),
                       P(', '.join(unknown_roles)),
                       P('Valid values are: ', ', '.join(role_list)))
        
        # - course presentations are recognized?
        unknown_presentations = set(fields['course_presentation']).difference(set(course_presentation_list))
        
        if len(unknown_presentations) > 0:
            html = CAT(html,
                       H4('Unknown course presentations'),
                       P('These course presentations are found in the file but are not recognized:'),
                       P(', '.join(unknown_presentations)),
                       P('Valid values are: ', ', '.join(course_presentation_list)))
        
        # bad student emails
        bad_emails = [IS_EMAIL()(x) for x in fields['student_email']]
        bad_emails = [x[0] for x in bad_emails if x[1] is not None]
        if len(bad_emails) > 0:
            html = CAT(html,
                       H4('Invalid student emails'),
                       P('The following are not well formatted emails: '), 
                       P(', '.join(set(bad_emails))))
            
        # bad marker emails
        bad_emails = [IS_EMAIL()(x) for x in fields['marker_email']]
        bad_emails = [x[0] for x in bad_emails if x[1] is not None]
        if len(bad_emails) > 0:
            html = CAT(html,
                       H4('Invalid marker emails'),
                       P('The following are not well formatted emails: '),
                       P(', '.join(set(bad_emails))))
        
        # due dates not formatted correctly
        bad_dates = [IS_DATE()(x) for x in fields['due_date']]
        bad_dates = [x[0] for x in bad_dates if x[1] is not None]
        if len(bad_dates) > 0:
            html = CAT(html,
                       H4('Invalid due dates'),
                       P('The following are not well formatted dates: '),
                       P(', '.join(set(bad_dates))))
        
        # non numeric years
        years = set(fields['academic_year'])
        bad_years = [ x for x in years if not x.isdigit() ]
        if len(bad_years) > 0:
            html = CAT(html,
                       H4('Invalid year'),
                       P('The following are not valid years: '),
                       P(', '.join(set(bad_years))))
        
        # non numeric CID
        cids = set(fields['student_cid'])
        bad_cids = [ x for x in cids if not x.isdigit() ]
        if len(bad_cids) > 0:
            html = CAT(html,
                       H4('Invalid student CID numbers'),
                       P('The following are not valid CIDs: '),
                       P(', '.join(set(bad_cids))))
        
        # empty names or just whitespace
        names = set(fields['student_first_name'] + fields['student_last_name']+
                    fields['marker_first_name'] + fields['marker_last_name'])
        bad_names = [ x for x in names if x.isspace() or x == '' ]
        if len(bad_names) > 0:
            html = CAT(html,
                       H4('Invalid student or marker names'),
                       P('The student and marker names data contains empty strings or text just consisting of spaces'))
        
        # Any problems detected
        if html != '':
            html = CAT(H2('Errors found in the uploaded file', _style='color:darkred'),
                       P('Please edit the file to fix these problems and then repeat the upload'),
                       html)
        else:
            # - get sets of records by marker email
            data.sort(key=lambda recs: recs['marker_email'])
            marker_blocks = {k:list(recs) for k, recs in itertools.groupby(data, lambda x: x['marker_email'].lower())}
            
            # - loop over those blocks, inserting into the marker database if 
            #   needed and then inserting the assignments
            for key, assignments in marker_blocks.items():
                marker_record = db.markers(email=key)
                
                if marker_record is None:
                    marker_record = db.markers.insert(email=key, 
                                                      last_name=assignments[0]['marker_last_name'],
                                                      first_name=assignments[0]['marker_first_name'])
                
                for a in assignments:
                    db.assignments.insert(marker=marker_record.id,
                                          **db.assignments._filter_fields(a))
            
            # load the assignments
            html = CAT(H2(str(len(fields['marker_email'])) + ' Assignments successfully uploaded'))
            
        
    else:
        
        html=''
    
    
    return dict(form=form, html=html)

## --------------------------------------------------------------------------------
## MARKING ASSIGNMENTS
## - MARKER FUNCTIONS - ALL OF THESE SHOULD USE THE 2FA MECHANISM VIA authenticate()
## --------------------------------------------------------------------------------

def authenticate():
    """Two factor authentication by email
    
    This page emails a numeric code to the marker, validates it and
    redirects to the referring page. It expects vars identifying
    'marker' and '_next'. It uses global session variables to track
    the authentication process and report that the per session code
    has been successfully entered.
    
    To use this, another controller needs to check the value of 
    session.tf_validated and redirect to /authenticate?marker=XX&_next=YY
    where YY is the URL of the controller to return to.
    """
    
    max_attempts = 3
    timeout = 10
    
    marker = request.vars['marker']
    marker = db.markers[marker]
    _next = request.vars['_next']
    
    # (Re)set if no code yet exists or timeout has expired
    if (session.tf_code is None or 
        (session.tf_timeout is not None and datetime.datetime.now() > session.tf_timeout)):
            session.tf_code = str(random.randint(100000, 999999))
            session.tf_attempts = max_attempts
            session.tf_validated = session.tf_validated or False
            session.tf_mailed = False
            session.tf_timeout = None
    
    if not session.tf_mailed:
        
        # Email code to the marker.
        email_dict = {'name': marker.first_name,
                      'code': session.tf_code}
        
        mailer = Mail()
        success = mailer.sendmail(subject='Marking report code',
                                  to=marker.email,
                                  email_template='marker_two_factor.html',
                                  email_template_dict=email_dict)
        session.tf_mailed = True
    
    if session.tf_attempts > 0:
        session.tf_attempts -= 1
        readonly=False
        comment = CAT('Please enter the authentication code', BR(), 
                      f'{session.tf_attempts} attempts remaining')
    else:
        readonly=True
        session.tf_timeout = datetime.datetime.now() + datetime.timedelta(minutes=timeout)
        comment = CAT('Three invalid codes entered', BR(), 
                      f'Try again in {timeout} minutes')
    
    # Create a form to get the verification code - this is still shown
    # but disabled when too many failed attempts have been made
    form = SQLFORM.factory(
                Field('authentication_code',
                      label=B('Enter authentication code'),
                      required=True,
                      comment=comment,
                      widget=lambda f, v: SQLFORM.widgets.string.widget(f, v, _disabled=readonly)),
                formstyle='bootstrap3_stacked')
    
    if readonly:
        submit = form.element('.btn')
        submit['_disabled'] = True
        submit['_class'] = 'btn btn-secondary' 
        
    if form.process(onsuccess=None).accepted:
        if form.vars.authentication_code == session.tf_code:
            session.tf_validated = True
            redirect(_next)

    return dict(html=form)


def my_assignments():
    
    """
    This controller allows a marker to access a table of assignments that have been
    assigned to them - like the admin assignments() controller - but with much reduced
    capabilities!
    """
    
    security = request.vars
    
    # is the marker id valid
    if security['marker'] is None:
        session.flash = 'No marker id provided'
        redirect(URL('index'))
    else:
        # Find the marker
        marker = db.markers(int(security['marker']))
        
        if marker is None:
            session.flash = 'Unknown marker id provided'
            redirect(URL('index'))
    
    # is there a matching access token
    if security['marker_access_token'] is None:
        session.flash = 'No marker access token provided'
        redirect(URL('index'))
    else:
        access_token = security['marker_access_token']
        
        if marker.marker_access_token != access_token:
            session.flash = 'Marker access token invalid'
            redirect(URL('index'))
    
    # Two factor authentication
    if not session.tf_validated:
        _next = URL(args=request.args, vars=request.vars)
        redirect(URL('authenticate', vars=dict(marker=marker.id, _next=_next)))
    
    # db.assignments._common_filter = None
    
    # reduce the set of fields shown in the grid
    db.assignments.id.readable = False
    db.assignments.student_email.readable = False
    db.assignments.student_first_name.readable = False
    db.assignments.student_cid.readable = False
    db.assignments.assignment_data.readable = False
    
    # and edit representations
    db.assignments.student_last_name.represent =  lambda id, row: row.student_last_name + ', ' + row.student_first_name
    db.assignments.status.represent = lambda id, row: status_dict[row.status]
    
    # link to a non-default new edit page
    links = [dict(header = 'Report', 
                  body = lambda row: A('View',
                                       _class='button btn btn-secondary',
                                       _href=URL("marking_reports", "write_report", 
                                                 vars={'record': row.id, 
                                                       'staff_access_token':row.staff_access_token}),
                                       _target='_blank'))]
    
    # create the SQLFORM grid to show the existing assignments
    # and set up actions to be applied to selected rows - these
    # are powered by action functions defined below
    grid = SQLFORM.grid(db.assignments.marker == marker.id,
                        csv=False,
                        deletable=False,
                        create=False,
                        details=False,
                        editable=False,
                        links=links,
                        headers= {'assignments.student_last_name': 'Student'},
                        paginate=False)
    
    return dict(name=marker.first_name + " " + marker.last_name, form=grid)

## --------------------------------------------------------------------------------
## WEB CONTROLLERS TO HANDLE TWO MODES
## - Report writing: provides a form to complete and then a static view for 
##                   submitted reports. This is only accessible to staff who 
##                   will need to have a link with the assignment record and 
##                   a matching access token
## - PDF download:   provides a link to pull down a generated PDF. This can 
##                   be a confidential version including private comments and
##                   grade or a public version for students.
## --------------------------------------------------------------------------------

def write_report():
    
    """
    This function generates a form dynamically from a JSON description
    and stores the data in a json field in the database. This approach
    avoids having to declare a bunch of different tables for different 
    forms and then handling the structure of each display. A user can 
    just provide a form definition and a marking criteria file and the
    forms are provided on the fly, with data stored in a single data 
    in the assignments table as a json object.
    """
    
    security = request.vars
    
    # is the record id valid
    if security['record'] is None:
        session.flash = 'No project marking record id provided'
        redirect(URL('index'))
    else:
        # allow old reports to be retrieved
        db.assignments._common_filter = None
        record = db.assignments(int(security['record']))
        
        if record is None:
            session.flash = 'Unknown project marking record id provided'
            redirect(URL('index'))
    
    # is there a matching access token
    if security['staff_access_token'] is None:
        session.flash = 'No staff access token provided'
        redirect(URL('index'))
    else:
        access_token = security['staff_access_token']
        
        if record.staff_access_token != access_token:
            session.flash = 'Staff access token invalid'
            redirect(URL('index'))
    
    # - load the correct form  and marking criteria from the definition string 
    #   and store it in the session to make it accessible to validation without having to reload
    style_dict = form_data_dict[(record.course_presentation, record.marker_role)] 
    form_json = style_dict['form']
    f = open(os.path.join(request.folder,'static','form_json', form_json))
    form_json = json.load(f)
    session.form_json = form_json
    
    # define the header block
    header_rows =   [('Student',  '{student_first_name} {student_last_name}'),
                     ('CID', '{student_cid}'),
                     ('Course Presentation', '{course_presentation}'),
                     ('Academic Year', '{academic_year}'),
                     ('Marker', '{marker.first_name} {marker.last_name}'),
                     ('Marker Role', '{marker_role}'),
                     ('Status', '{status}')]
     
    header_pack = [DIV(LABEL(l, _class='col-sm-3'), DIV(v.format(**record), _class='col-sm-9'), _class='row')
                       for l, v in header_rows]
    
    header_pack.append(DIV(LABEL('Marking critera', _class='col-sm-3'), 
                           DIV(A(style_dict['criteria'], 
                                 _href=URL('static','marking_criteria/' + style_dict['criteria']), 
                                 _target='blank'),
                               _class='col-sm-9'), _class='row'))
    
    # If the report has been submitted, edit the html to insert a PDF download link with 
    # staff security credentials. Otherwise, insert any instructions
    if record.status in ['Submitted','Released']:
        pdf_link = CAT(': click ', A('here', _href=URL('download_pdf', vars=security)),
                       ' to download a confidential pdf of the full report.')
        header_pack[5].elements()[2].append(pdf_link)
        header_pack.append(H4('Completed report'))
    else:
        header_pack.append(H4('Instructions'))
        header_pack.append(XML(form_json['instructions']))
    
    # set whether the form is editable or not, which is basically just submitted/not submitted
    # - allow authorised users to edit completed reports but warn them
    
    if auth.has_membership('admin'):
        warning = DIV(B('Reminder: '), "Logged in administrators have the ability to ",
                      "edit all reports in order to fix mistakes or unfortunate phrasing. ",
                      "Please do not do so lightly.", _class="alert alert-danger", _role="alert")
        header_pack.insert(0, warning)
        readonly=False
    elif record.status in ['Submitted','Released']:
        readonly = True
    else:
        readonly = False
    
    # - Extract the set of fields from the components section of the questions array
    #   This allows a question to have multiple bits (e.g. rubric + optional comments)
    fields=[]
    for q in form_json['questions']:
        for c in q['components']:
            if c['type'] == 'rubric':
                fields.append(Field(c['variable'], 
                              type='string', 
                              requires=IS_NULL_OR(IS_IN_SET(c['options'])),
                              widget=div_radio_widget))
            elif c['type'] == 'comment':
                # protect carriage returns in the display of the text but stop anybody using 
                # any other tags
                fields.append(Field(c['variable'], 
                              type='text', 
                              represent=lambda text: "" if text is None else XML(text.replace('\n', '<br />'),
                              sanitize=True, 
                              permitted_tags=['br/'])))
            elif c['type'] == 'select':
                fields.append(Field(c['variable'], 
                              type='string', 
                              requires=IS_NULL_OR(IS_IN_SET(c['options']))))
            else:
                # Other types that don't insert a form control- currently only 'query'
                pass
    
    # - provide a save and a submit button
    buttons =  [TAG.BUTTON('Save', _type="submit", _class="button btn btn-default",
                           _style='padding: 10px 15px 10px 15px;width:100px', _name='save'),
                XML('&nbsp;')*5,
                TAG.BUTTON('Submit', _type="submit", _class="button btn btn-default",
                               _style='padding: 10px 15px 10px 15px;width:100px', _name='submit')]
    
    # - define the form for IO using the fields object,
    #   preloading any existing data
    if record.assignment_data in [None, '']:
        data_json=None
    else:
        data_json=record.assignment_data
    
    form = SQLFORM.factory(*fields,
                           readonly=readonly,
                           buttons=buttons,
                           record=data_json,
                           showid=False)
    
    # process the form to handle storing the data, via a validation function
    # that checks required fields are complete when users press submit
    if form.process(onvalidation=submit_validation).accepted:
        
        # add the id from the record into the data (an id is needed by the form code)
        data = form.vars
        data['id'] = record.id
        
        if 'save' in list(request.vars.keys()):
            session.flash = 'Changes to report saved'
            record.update_record(assignment_data = data,
                                 status='Started')
        elif 'submit' in list(request.vars.keys()):
            session.flash = 'Report submitted'
            record.update_record(assignment_data = data,
                                 status='Submitted',
                                 submission_date = datetime.datetime.now(),
                                 submission_ip = request.client)
        
        redirect(URL('write_report', vars={'record':record.id, 
                                           'staff_access_token':record.staff_access_token}))
    
    # modify any widget settings for active forms
    if not readonly:
        for q in form_json['questions']:
            for c in q['components']:
                if 'nrow' in list(c.keys()):
                    form.custom.widget[c['variable']]['_rows'] = c['nrow']
                if 'placeholder' in list(c.keys()):
                    form.custom.widget[c['variable']].update(_placeholder=c['placeholder'])
                if 'value' in list(c.keys()):
                    form.custom.widget[c['variable']].components = [c['value']]
    
    # compile the laid out form in a list
    html = [H2(form_json['title'])] 
    [html.append(h) for h in header_pack]
    html.append(form.custom.begin)
    
    # add the questions in the order they appear in the JSON array
    for q in form_json['questions']:
        html.append(DIV(H4(q['title']), _style='background-color:lightgrey;padding:1px'))
        
        if q.get('info') is not None:
            html.append(DIV(XML(q.get('info'))))
        else:
            html.append(DIV(_style='min-height:10px'))
        
        for c in q['components']:
            
            # Insert either the form variable and stored data or the output of a 
            # query component.
            if c['type'] == 'query':
                # This is a tricky line. globals() contains globals functions, so needs
                # the appropriate query function to be imported. All such functions
                # get the assignment record as an input. You could use eval() here but
                # that has security risks - hard to see them applying here, but hey.
                query_data = globals()[c['query']](record)
                html.append(DIV(DIV(B(c['label']), _class='col-sm-2'),
                                DIV(query_data, _class='col-sm-10'),
                                _class='row'))
            else:
                html.append(DIV(DIV(B(c['label']), _class='col-sm-2'),
                                DIV(form.custom.widget[c['variable']], _class='col-sm-10'),
                                _class='row'))
            
            if c.get('info') is not None:
                html.append(DIV(XML(c.get('info'))))
            else:
                html.append(DIV(_style='min-height:10px'))
            
        html.append(DIV(_style='min-height:10px'))
    
        
    # finalise the form and send the whole thing back
    html.append(BR())
    html.append(form.custom.submit)
    html.append(form.custom.end)
    
    # Set the form title
    response.title = f"{record.student_last_name}: {record.marker_role}"
    
    return dict(html=CAT(*html))


# # This controller resets 2FA session tokens - useful in debugging
# def deauthenticate():
#
#     session.tf_code = None
#     session.tf_attempts = None
#     session.tf_validated = False


def write_report_2fa():
    
    """
    This function generates a form dynamically from a JSON description
    and stores the data in a json field in the database. This approach
    avoids having to declare a bunch of different tables for different 
    forms and then handling the structure of each display. A user can 
    just provide a form definition and a marking criteria file and the
    forms are provided on the fly, with data stored in a single data 
    in the assignments table as a json object.
    """
    
    security = request.vars
    
    # is the record id valid
    if security['record'] is None:
        session.flash = 'No project marking record id provided'
        redirect(URL('index'))
    else:
        # allow old reports to be retrieved
        db.assignments._common_filter = None
        record = db.assignments(int(security['record']))
        
        if record is None:
            session.flash = 'Unknown project marking record id provided'
            redirect(URL('index'))
    
    # is there a matching access token
    if security['staff_access_token'] is None:
        session.flash = 'No staff access token provided'
        redirect(URL('index'))
    else:
        access_token = security['staff_access_token']
        
        if record.staff_access_token != access_token:
            session.flash = 'Staff access token invalid'
            redirect(URL('index'))
    
    marker = db.markers[record.marker]
    
    # Two factor identification
    if not session.two_factor_validated:
        if session.two_factor_attempts > 0:
            # form to get the verification code
            form = SQLFORM.factory(
                Field('authentication_code',
                      label='Authentication code',
                      required=True,
                      comment='Please enter the authentication code'))
            
            if form.process().accepted:
            
                if form.vars.code == session.two_factor_code:
                    session.two_factor_validated = True
                    redirect()
                else:
                    session.two_factor_attempts -= 1
            
            # Email it to the marker.
            email_dict = {'name': marker.first_name,
                          'code': session.two_factor_code}
            
            mailer = Mail()
            success = mailer.sendmail(subject='Marking report code',
                                      to=marker.email,
                                      email_template='marker_two_factor.html',
                                      email_template_dict=email_dict)
            
            return dict(html=form)
        
        else:
            return dict(html='Incorrect code entered 3 times, try again later. ')
    
    # - load the correct form  and marking criteria from the definition string 
    #   and store it in the session to make it accessible to validation without having to reload
    style_dict = form_data_dict[(record.course_presentation, record.marker_role)] 
    form_json = style_dict['form']
    f = open(os.path.join(request.folder,'static','form_json', form_json))
    form_json = json.load(f)
    session.form_json = form_json
    
    # define the header block
    header_rows =   [('Student',  '{student_first_name} {student_last_name}'),
                     ('CID', '{student_cid}'),
                     ('Course Presentation', '{course_presentation}'),
                     ('Academic Year', '{academic_year}'),
                     ('Marker', '{marker.first_name} {marker.last_name}'),
                     ('Marker Role', '{marker_role}'),
                     ('Status', '{status}')]
     
    header_pack = [DIV(LABEL(l, _class='col-sm-3'), DIV(v.format(**record), _class='col-sm-9'), _class='row')
                       for l, v in header_rows]
    
    header_pack.append(DIV(LABEL('Marking critera', _class='col-sm-3'), 
                           DIV(A(style_dict['criteria'], 
                                 _href=URL('static','marking_criteria/' + style_dict['criteria']), 
                                 _target='blank'),
                               _class='col-sm-9'), _class='row'))
    
    # If the report has been submitted, edit the html to insert a PDF download link with 
    # staff security credentials. Otherwise, insert any instructions
    if record.status in ['Submitted','Released']:
        pdf_link = CAT(': click ', A('here', _href=URL('download_pdf', vars=security)),
                       ' to download a confidential pdf of the full report.')
        header_pack[5].elements()[2].append(pdf_link)
        header_pack.append(H4('Completed report'))
    else:
        header_pack.append(H4('Instructions'))
        header_pack.append(XML(form_json['instructions']))
    
    # set whether the form is editable or not, which is basically just submitted/not submitted
    # - allow authorised users to edit completed reports but warn them
    
    if auth.has_membership('admin'):
        warning = DIV(B('Reminder: '), "Logged in administrators have the ability to ",
                      "edit all reports in order to fix mistakes or unfortunate phrasing. ",
                      "Please do not do so lightly.", _class="alert alert-danger", _role="alert")
        header_pack.insert(0, warning)
        readonly=False
    elif record.status in ['Submitted','Released']:
        readonly = True
    else:
        readonly = False
    
    # - Extract the set of fields from the components section of the questions array
    #   This allows a question to have multiple bits (e.g. rubric + optional comments)
    fields=[]
    for q in form_json['questions']:
        for c in q['components']:
            if c['type'] == 'rubric':
                fields.append(Field(c['variable'], 
                              type='string', 
                              requires=IS_NULL_OR(IS_IN_SET(c['options'])),
                              widget=div_radio_widget))
            elif c['type'] == 'comment':
                # protect carriage returns in the display of the text but stop anybody using 
                # any other tags
                fields.append(Field(c['variable'], 
                              type='text', 
                              represent=lambda text: "" if text is None else XML(text.replace('\n', '<br />'),
                              sanitize=True, 
                              permitted_tags=['br/'])))
            elif c['type'] == 'select':
                fields.append(Field(c['variable'], 
                              type='string', 
                              requires=IS_NULL_OR(IS_IN_SET(c['options']))))
            else:
                # Other types that don't insert a form control- currently only 'query'
                pass
    
    # - provide a save and a submit button
    buttons =  [TAG.BUTTON('Save', _type="submit", _class="button btn btn-default",
                           _style='padding: 10px 15px 10px 15px;width:100px', _name='save'),
                XML('&nbsp;')*5,
                TAG.BUTTON('Submit', _type="submit", _class="button btn btn-default",
                               _style='padding: 10px 15px 10px 15px;width:100px', _name='submit')]
    
    # - define the form for IO using the fields object,
    #   preloading any existing data
    if record.assignment_data in [None, '']:
        data_json=None
    else:
        data_json=record.assignment_data
    
    form = SQLFORM.factory(*fields,
                           readonly=readonly,
                           buttons=buttons,
                           record=data_json,
                           showid=False)
    
    # process the form to handle storing the data, via a validation function
    # that checks required fields are complete when users press submit
    if form.process(onvalidation=submit_validation).accepted:
        
        # add the id from the record into the data (an id is needed by the form code)
        data = form.vars
        data['id'] = record.id
        
        if 'save' in list(request.vars.keys()):
            session.flash = 'Changes to report saved'
            record.update_record(assignment_data = data,
                                 status='Started')
        elif 'submit' in list(request.vars.keys()):
            session.flash = 'Report submitted'
            record.update_record(assignment_data = data,
                                 status='Submitted',
                                 submission_date = datetime.datetime.now(),
                                 submission_ip = request.client)
        
        redirect(URL('write_report', vars={'record':record.id, 
                                           'staff_access_token':record.staff_access_token}))
    
    # modify any widget settings for active forms
    if not readonly:
        for q in form_json['questions']:
            for c in q['components']:
                if 'nrow' in list(c.keys()):
                    form.custom.widget[c['variable']]['_rows'] = c['nrow']
                if 'placeholder' in list(c.keys()):
                    form.custom.widget[c['variable']].update(_placeholder=c['placeholder'])
                if 'value' in list(c.keys()):
                    form.custom.widget[c['variable']].components = [c['value']]
    
    # compile the laid out form in a list
    html = [H2(form_json['title'])] 
    [html.append(h) for h in header_pack]
    html.append(form.custom.begin)
    
    # add the questions in the order they appear in the JSON array
    for q in form_json['questions']:
        html.append(DIV(H4(q['title']), _style='background-color:lightgrey;padding:1px'))
        
        if q.get('info') is not None:
            html.append(DIV(XML(q.get('info'))))
        else:
            html.append(DIV(_style='min-height:10px'))
        
        for c in q['components']:
            
            # Insert either the form variable and stored data or the output of a 
            # query component.
            if c['type'] == 'query':
                # This is a tricky line. globals() contains globals functions, so needs
                # the appropriate query function to be imported. All such functions
                # get the assignment record as an input. You could use eval() here but
                # that has security risks - hard to see them applying here, but hey.
                query_data = globals()[c['query']](record)
                html.append(DIV(DIV(B(c['label']), _class='col-sm-2'),
                                DIV(query_data, _class='col-sm-10'),
                                _class='row'))
            else:
                html.append(DIV(DIV(B(c['label']), _class='col-sm-2'),
                                DIV(form.custom.widget[c['variable']], _class='col-sm-10'),
                                _class='row'))
            
            if c.get('info') is not None:
                html.append(DIV(XML(c.get('info'))))
            else:
                html.append(DIV(_style='min-height:10px'))
            
        html.append(DIV(_style='min-height:10px'))
    
        
    # finalise the form and send the whole thing back
    html.append(BR())
    html.append(form.custom.submit)
    html.append(form.custom.end)
    
    # Set the form title
    response.title = f"{record.student_last_name}: {record.marker_role}"
    
    return dict(html=CAT(*html))




def submit_validation(form):
    
    """
    Takes the submitted form and checks that all required components
    have been completed
    """
    
    if 'submit' in list(request.vars.keys()):
        for q in session.form_json['questions']:
            for c in q['components']:
                if c['required'] and form.vars[c['variable']] in [None, '']:
                    if c['type'] == 'rubric':
                        form.errors[c['variable']] = 'You must select an option'
                    elif c['type'] == 'comment':
                        form.errors[c['variable']] = 'Please provide comments'
                    elif c['type'] == 'select':
                        form.errors[c['variable']] = 'Please select a grade'

#
# Controller to display the structure of the marking forms
#


def show_form():
    
    """
    This function generates a form dynamically from a JSON description
    but as a simple static form with no submit method. This is a convenient
    way for students to be able to see the forms.
    """

    record = Storage(student_first_name='Awesome', student_last_name='Student', 
                     student_cid='00000000', course_presentation='EEC MSc',
                     academic_year=2020, status='Not started',
                     marker=Storage(first_name='Sir Alfred', last_name='Marker'),
                     marker_role=request.args[0])

    # - load the correct form  and marking criteria from the definition string 
    #   and store it in the session to make it accessible to validation without having to reload
    style_dict = form_data_dict[(record.course_presentation, record.marker_role)] 
    form_json = style_dict['form']
    f = open(os.path.join(request.folder,'static','form_json', form_json))
    form_json = json.load(f)
    
    # define the header block
    header_rows =   [('Student',  '{student_first_name} {student_last_name}'),
                     ('CID', '{student_cid}'),
                     ('Course Presentation', '{course_presentation}'),
                     ('Academic Year', '{academic_year}'),
                     ('Marker', '{marker.first_name} {marker.last_name}'),
                     ('Marker Role', '{marker_role}'),
                     ('Status', '{status}')]
     
    header_pack = [DIV(LABEL(l, _class='col-sm-3'), DIV(v.format(**record), _class='col-sm-9'), _class='row')
                       for l, v in header_rows]
    
    header_pack.append(DIV(LABEL('Marking critera', _class='col-sm-3'), 
                           DIV(A(style_dict['criteria'], 
                                 _href=URL('static','marking_criteria/' + style_dict['criteria']), 
                                 _target='blank'),
                               _class='col-sm-9'), _class='row'))
    
    header_pack.append(H4('Instructions'))
    header_pack.append(XML(form_json['instructions']))
    
    # - Extract the set of fields from the components section of the questions array
    #   This allows a question to have multiple bits (e.g. rubric + optional comments)
    fields=[]
    for q in form_json['questions']:
        for c in q['components']:
            if c['type'] == 'rubric':
                fields.append(Field(c['variable'], 
                              type='string', 
                              requires=IS_NULL_OR(IS_IN_SET(c['options'])),
                              widget=div_radio_widget))
            elif c['type'] == 'comment':
                # protect carriage returns in the display of the text but stop anybody using 
                # any other tags
                fields.append(Field(c['variable'], 
                              type='text', 
                              represent=lambda text: "" if text is None else XML(text.replace('\n', '<br />'),
                              sanitize=True, 
                              permitted_tags=['br/'])))
            elif c['type'] == 'select':
                fields.append(Field(c['variable'], 
                              type='string', 
                              requires=IS_NULL_OR(IS_IN_SET(c['options']))))
            else:
                # Other types that don't insert a form control- currently only 'query'
                pass
    
    # - define the form for IO using the fields object, making it editable but with no save.
    form = SQLFORM.factory(*fields,
                           showid=False)
    
    # modify any widget settings for active forms
    for q in form_json['questions']:
        for c in q['components']:
            if 'nrow' in list(c.keys()):
                form.custom.widget[c['variable']]['_rows'] = c['nrow']
            if 'placeholder' in list(c.keys()):
                form.custom.widget[c['variable']].update(_placeholder=c['placeholder'])
            if 'value' in list(c.keys()):
                form.custom.widget[c['variable']].components = [c['value']]
    
    # compile the laid out form in a list
    html = [DIV(H4('Example form'),
                    P('This page shows an ', B('exact'), ' copy of the form that a '
                      'marker will complete for this component of a Masters thesis '
                      'examination. ', _class='mb-0'),
                    _class="alert alert-success", _role="alert"),
            H2(form_json['title'])]
    [html.append(h) for h in header_pack]
    html.append(form.custom.begin)
    
    # add the questions in the order they appear in the JSON array
    for q in form_json['questions']:
        html.append(DIV(H4(q['title']), _style='background-color:lightgrey;padding:1px'))
        
        if q.get('info') is not None:
            html.append(DIV(XML(q.get('info'))))
        else:
            html.append(DIV(_style='min-height:10px'))
        
        for c in q['components']:
            
            # Insert either the form variable and stored data or the output of a 
            # query component.
            if c['type'] == 'query':
                # This is a tricky line. globals() contains globals functions, so needs
                # the appropriate query function to be imported. All such functions
                # get the assignment record as an input. You could use eval() here but
                # that has security risks - hard to see them applying here, but hey.
                query_data = globals()[c['query']](record)
                html.append(DIV(DIV(B(c['label']), _class='col-sm-2'),
                                DIV(query_data, _class='col-sm-10'),
                                _class='row'))
            else:
                html.append(DIV(DIV(B(c['label']), _class='col-sm-2'),
                                DIV(form.custom.widget[c['variable']], _class='col-sm-10'),
                                _class='row'))
            
            if c.get('info') is not None:
                html.append(DIV(XML(c.get('info'))))
            else:
                html.append(DIV(_style='min-height:10px'))
            
        html.append(DIV(_style='min-height:10px'))
    
        
    # finalise the form and send the whole thing back
    html.append(BR())
    # html.append(form.custom.submit)
    html.append(form.custom.end)
    
    # Set the form title
    response.title = f"{record.student_last_name}: {record.marker_role}"
    
    return dict(html=CAT(*html))


def download_pdf():

    """
    General function that checks the access token and pulls in
    html from functions and spits back a PDF
    """

    # first check request variables
    # - access control needs a marking_assignment record id number
    #   and either a matching staff_access_token to obtain the confidential 
    #   report or a public_access_token to obtain a public one

    security = request.vars

    # is the record id valid
    if security['record'] is None:
        session.flash = 'No project marking record id provided'
        redirect(URL('index'))
    else:
        # allow old reports to be retrieved
        db.assignments._common_filter = None
        record = db.assignments(int(security['record']))
    
        if record is None:
            session.flash = 'Unknown project marking record id provided'
            redirect(URL('index'))
        
        if not record.status in ['Submitted', 'Released']:
            session.flash = 'This report has not yet been submitted or released'
            redirect(URL('index'))
    
    # what access tokens have been provided?
    if security['staff_access_token'] is None and security['public_access_token'] is None:
        
        session.flash = 'No access token provided for PDF download'
        redirect(URL('index'))
        
    elif security['staff_access_token'] is not None:
        
        if record.staff_access_token != security['staff_access_token']:
            session.flash = 'Staff access token invalid for PDF download'
            redirect(URL('index'))
        else:
            confidential = True
        
    elif security['public_access_token'] is not None:
            
        if record.public_access_token != security['public_access_token']:
            session.flash = 'Public access token invalid for PDF download'
            redirect(URL('index'))
        elif record.status != 'Released':
            session.flash = ("Report not yet released. Also, we'd just love to know how you " + 
                             "got your hands on a valid public access token for an unreleased report.")
            redirect(URL('index'))
        else:
            confidential = False
    
    # - load the correct form definition 
    style_dict = form_data_dict[(record.course_presentation, record.marker_role)] 
    form_json = style_dict['form']
    f = open(os.path.join(request.folder,'static','form_json', form_json))
    form_json = json.load(f)
    
    # create the form - this is a separate function so that the file creation 
    # can be used by other functions (like downloading a zipfile of selected pdf)
    pdf, filename = create_pdf(record, form_json, confidential=confidential)
    
    # return a pdf version of the record
    response.headers['Content-Type'] = 'application/pdf'
    attachment = 'attachment;filename={}'.format(filename)
    response.headers['Content-Disposition'] = attachment
    
    raise HTTP(200, pdf,
               **{'Content-Type':'application/pdf',
                  'Content-Disposition':attachment + ';'})

## -----------------------------------------------------------------------------
## Project proposal handlers.
## One view option that students can see, with a custom view function
## One submission handler for use by staff
## -----------------------------------------------------------------------------

def project_proposals():
    
    """
    Controller to serve up the contents of the proposals database as a nice
    searchable grid.
    """
    
    # Hide the internal ID numbers
    db.project_proposals.id.readable=False
    
    links = [dict(header = '', 
                  body = lambda row: A(SPAN('',_class="fa fa-info-circle", 
                                            _style='font-size: 1.3em;',
                                            _title='See details'),
                                       _class="button btn btn-default", 
                                       _href=URL("marking_reports","proposal_details", 
                                                 args=[row.id], user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;'))]
    
    # show the standard grid display
    # - restrict list display to a few key fields
    # - sub in a custom view function for the normal details link
    # - just give the CSV export link, which is moved from the bottom to
    #   the search bar using in javascript in the view.
    grid  = SQLFORM.grid(db.project_proposals,
                         fields = [db.project_proposals.project_filled,
                                   db.project_proposals.contact_name,
                                   db.project_proposals.project_base,
                                   db.project_proposals.project_title,
                                   db.project_proposals.date_created],
                         headers = {'project_proposals.project_filled':"Available?"},
                         links = links,
                         details = False,
                         maxtextlength=250,
                         create=False, # using a custom create form
                         csv=False,
                         exportclasses = dict(csv=False, json=False, html=False,
                                              tsv=False, xml=False, 
                                              tsv_with_hidden_cols=False),
                         formargs={'showid':False},
                         orderby= ~db.project_proposals.date_created)
    
    # edit the grid object
    # - extract the download button and retitle it
    # - insert it in the search menu
    download = A('Download all', _class="btn btn-secondary btn-sm",
                  _href=URL('project_proposals', 
                            vars={'_export_type': 'csv_with_hidden_cols'}))
    
    if grid.element('.web2py_console form') is not None:
        grid.element('.web2py_console form').append(download)

    if auth.has_membership('project_proposer'):
        download = A('New proposal', _class="btn btn-success btn-sm",
                      _href=URL('submit_proposal'))
        
        if grid.element('.web2py_console form') is not None:
            grid.element('.web2py_console form').append(download)
        
    
    return(dict(grid=grid))


def proposal_details():
    
    """
    Controller to provide a nicely styled custom view of project details
    """
    
    # retrieve the news post id from the page arguments passed by the button
    # and then get the row and send it to the view
    proposal_id = request.args(0)
    proposal = db.project_proposals(proposal_id)
    
    if proposal is None:
        session.flash = CENTER(B('Invalid project proposal number.'), _style='color: red')
        redirect(URL('marking_reports','project_proposals'))
    
    # optional fields
    if proposal.imperial_email:
        internal = DIV(DIV(B('Imperial contact email'), _class="col-sm-3"),
                        DIV(A(proposal.imperial_email, _href='mailto:{}'.format(proposal.imperial_email)),
                            _class="col-sm-9"),
                        _class='row', _style='min-height:30px')
    else:
        internal = DIV()
    
    # package up the proposal in a neat set of foldable containers
    propview =  DIV(H3('Project proposal details'),
                    P('Please look carefully through the proposal details below. If you are interested '
                      'in the project then contact the supervisor, explaining why you are interested and '
                      'any background which makes you a good fit for the project.'), 
                    P('If this is an external project, the lead supervisor may have suggested someone at '
                      'Imperial College or the NHM who could act as an internal supervisor and you should '
                      'also contact them. If the project is external and no internal has been proposed '
                      'then you ', B('must'), ' find an internal supervisor before starting the project.'),
                    P('Please pay close attention to any extra notes on requirements (such as being able to '
                      'drive or to speak particular languages) or the application process. There may be '
                      'specific limitations on the project availability: if there are then they will be '
                      'clearly shown further down the page.'),
                    DIV(DIV(B("Project title"), _class="col-sm-3"),
                        DIV(proposal.project_title, _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    DIV(DIV(B("Contact name"), _class="col-sm-3"),
                        DIV(proposal.contact_name, _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    DIV(DIV(B("Contact email"), _class="col-sm-3"),
                        DIV(A(proposal.contact_email, _href='mailto:{}'.format(proposal.contact_email)),
                            _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    DIV(DIV(B("Project based at"), _class="col-sm-3"),
                        DIV(proposal.project_base, _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    internal,
                    DIV(DIV(B("Project description"), _class="col-sm-3"),
                        DIV(XML(proposal.project_description.replace('\n', '<br />')), _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                   )
    
    # some more optional components
    if proposal.requirements:
        propview += DIV(DIV(B("Additional requirements"), _class="col-sm-3"),
                        DIV(proposal.requirements, _class="col-sm-9"),
                        _class='row', _style='min-height:30px')

    if proposal.support:
        propview += DIV(DIV(B("Available support"), _class="col-sm-3"),
                        DIV(proposal.support, _class="col-sm-9"),
                        _class='row', _style='min-height:30px')
    
    if proposal.eligibility:
        propview += DIV(DIV(B("Selection and eligibility"), _class="col-sm-3"),
                        DIV(proposal.eligibility, _class="col-sm-9"),
                        _class='row', _style='min-height:30px')
    
    # add the date created
    propview += DIV(DIV(B("Date uploaded"), _class="col-sm-3"),
                    DIV(proposal.date_created.isoformat(), _class="col-sm-9"),
                    _class='row', _style='min-height:30px')

    # if there are any limitations, add a section
    if proposal.project_length or proposal.available_project_dates or proposal.course_restrictions:
        limits = DIV(H3('Project proposal limitations', _style='background:lightgrey;min-height:30px'),
                     P('The project proposer has indicated that there are some limitations to '
                       'the availability of this project. It may only be available at certain '
                       'times of year or suit a specific project length. It may also need '
                       'skills taught to students on a particular course or courses.'),
                     P('Research project proposals are usually part of an active research programme. '
                       'If supervisors have stated limitations to a proposal, then they are unlikely '
                       'to have any flexibility. If you are very interested in the topic but have '
                       'problems with the stated limitations, the supervisor ',B('may'), ' still be '
                       'happy to talk to you about other options around the proposal, but you should '
                       'not expect that any alternative arrangements can be made.'))
        
        if proposal.project_length:
            limits += DIV(DIV(B("Project length limitations"), _class="col-sm-3"),
                          DIV(', '.join(proposal.project_length), _class="col-sm-9"),
                          _class='row', _style='min-height:30px')

        if proposal.available_project_dates:
            limits += DIV(DIV(B("Available date limitations"), _class="col-sm-3"),
                          DIV(', '.join(proposal.available_project_dates), _class="col-sm-9"),
                          _class='row', _style='min-height:30px')

        if proposal.course_restrictions:
            limits += DIV(DIV(B("Suitable for"), _class="col-sm-3"),
                          DIV(', '.join(proposal.course_restrictions), _class="col-sm-9"),
                          _class='row', _style='min-height:30px')

        propview += limits
    
    return dict(proposal = propview)


@auth.requires_membership('project_proposer')
def submit_proposal():
    
    form  = SQLFORM(db.project_proposals)
    
    # process the form
    if form.process(onvalidation=validate_proposal).accepted:
        
        response.flash = CENTER(B('Project proposal submitted.'), _style='color: green')
        
        # email the submitter
        row = db.project_proposals[form.vars.id]
        email_dict = {'name': row.contact_name,
                      'title': row.project_title,
                      'fill_link': URL('project_filled', 
                                       vars={'id': row.id, 'token': row.project_filled_token},
                                       scheme=True, host=True)}
        
        mailer = Mail()
        success = mailer.sendmail(subject='Project proposal submission',
                                  to=row.contact_email,
                                  email_template='proposal_submitted.html',
                                  email_template_dict=email_dict)
        del mailer
        
    elif form.errors:
        
        response.flash = CENTER(B('Problems with the form, check below.'), _style='color: red')
        
    else:
        pass
    
    # customise the form to improve the layout
    form.element('textarea[name=requirements]')['_rows']= 3
    form.element('textarea[name=support]')['_rows']= 3
    form.element('textarea[name=eligibility]')['_rows']= 3

    # Create the project base selector. We're hijacking the standard widget to provide an
    # optional "Other" text entry field, when "Other" is selected from a drop down
    base_script = SCRIPT("""function checkvalue(val)
                            {
                                if(val==="Other")
                                   document.getElementById('project_proposals_project_base_other').style.display='block';
                                else
                                   document.getElementById('project_proposals_project_base_other').style.display='none';
                            }""")
    
    base_select = SELECT(*[OPTION(x, _value=x) for x in bases],
                         _class="generic-widget form-control",
                         _id="project_proposals_project_base",
                         _name="project_base",
                         _onchange = 'checkvalue(this.value)')
    
    base_other = INPUT(_class="form-control string",
                       _id="project_proposals_project_base_other",
                       _name="project_base_other",
                       _type="text",
                       _value="",
                       _placeholder="Institution name",
                       _style="display:none")
    
    form =  DIV(form.custom.begin,
                H3('Project proposal details', _style='background:lightgrey;min-height:30px'),
                DIV(DIV(H4("Contact name"), P("This should be name of main person to contact about the project"),
                        form.custom.widget.contact_name, _class="col-sm-6"),
                    DIV(H4("Contact email"), P("The email address main project contact"),
                        form.custom.widget.contact_email, _class="col-sm-6"),
                    _class='row'),
                DIV(DIV(H4("Project based at"), P('Please select the organisation where the student will be '
                        'based for the majority of the project (excluding fieldwork).'),
                        base_script, base_select, base_other, _class="col-sm-6"),
                    DIV(H4("Imperial email"), P("For external projects, if possible "
                        'please provide the email of an Imperial or NHM member of staff '
                        "who could act as an internal supervisor."),
                        form.custom.widget.imperial_email, _class="col-sm-6"),
                    _class='row'),
                DIV(DIV(H4("Project title"), P('Please provide a title. Students will initially see a list '
                        'of supervisors, project location and titles, so make it catchy!'),
                        form.custom.widget.project_title, _class="col-sm-12"),
                    _class='row'),
                DIV(DIV(H4("Project description"), P('Provide a brief description of the main project aims, '
                          'possibly including any key references'),
                        form.custom.widget.project_description, _class="col-sm-12"),
                    _class='row'),
                DIV(DIV(H4("Project type"), P('Please indicate the broad research skills '
                           'involved in this project - you can select multiple options.'),
                        form.custom.widget.project_type, _class="col-sm-12"),
                    _class='row'),
                H3('Additional information', _style='background:lightgrey;min-height:30px'),
                DIV(DIV(H4("Additional skills or experience required"), P('Most analytical skills and '
                         'methods should be taught during the project but vital skills or experience '
                         '(languages, driving, etc) should be given here'),
                        form.custom.widget.requirements, _class="col-sm-12"),
                    _class='row'),
                DIV(DIV(H4("Support offered"), P('This is for non-academic project support - logistics or '
                                                 'bursaries, for example'),
                        form.custom.widget.support, _class="col-sm-12"),
                    _class='row'),
                DIV(DIV(H4("Eligibility notes"), P('If the project has a deadline or a '
                        'particular selection criterion or process, please provide brief details offered'),
                        form.custom.widget.eligibility, _class="col-sm-12"),
                    _class='row'),
                H3('Proposal limitations', _style='background:lightgrey;min-height:30px'),
                P('Students from the courses above will be able to browse all of the projects listed in '
                  'this database. Students appreciate the breadth of choice to allow them to follow their '
                  'own interests. However, we recognise that some projects may be limited in when they '
                  'can occur and how long they will take. Some projects may require a skillset that makes '
                  'them well suited only to students from particular courses.'),
                P('Use the check boxes below to indicate any limitations for this proposal. ', B('Note that ',
                  'you only need to select options for categories that you want to limit. ', _style='color:darkred'),
                  'If all of the options in one of these categories are fine for the project then '
                  'save your clicking finger and leave all the boxes unchecked!'),
                DIV(DIV(H4("Project length"), P('Indicate if the proposal is only suited to particular '
                                                 'lengths of student projects'),
                        form.custom.widget.project_length, _class="col-sm-12"),
                    _class='row'),
                DIV(DIV(H4("Available project dates"), P('Indicate if the proposal is only available at '
                                                         'particular times of the year'),
                        form.custom.widget.available_project_dates, _class="col-sm-12"),
                    _class='row'),
                DIV(DIV(H4("Course restrictions"), P('Indicate if the proposal is only suited to students '
                                                     'with the background of particular courses'),
                        form.custom.widget.course_restrictions, _class="col-sm-12"),
                    _class='row'),
                DIV(_class='row', _style='min-height:10px'),
                form.custom.submit, form.custom.end)

    return(dict(form = form))


def validate_proposal(form):
    
    # Before processing the form object (which only considers fields in the table), sub the other text from 
    # the request.vars. into the form.vars. slot.
    if request.vars.project_base == 'Other':
        form.vars.project_base = request.vars.project_base_other
        #else:
        #    form.errors.project_base('For other project bases, please provide an institution name')
    
    form.vars.date_created = datetime.date.today()


def project_filled():
    
    """
    Provides supervisors with a link to change a project from unfilled to filled and back. 
    This basically only updates the display and all filled projects remain visible
    """
    
    project_id = request.vars['id']
    project_token = request.vars['token']
    
    msg = 'Invalid project id and or access token'
    
    # check both are provided
    if project_id and project_token:
        row = db.project_proposals[int(project_id)]
        
        # valid project ID?
        if row:
            # if the security token matches the one stored for 
            # this project, set project_filled = True
            if row.project_filled_token == project_token and not row.project_filled:
                row.update_record(project_filled= True)
                msg = 'Project successfully marked as unavailable'
            elif row.project_filled_token == project_token and row.project_filled:
                row.update_record(project_filled= False)
                msg = 'Project successfully marked as available'

        # currently does nothing about bad matches or inputs.
    
    return dict(msg=msg)


@auth.requires_login()
def reset_project_proposal_uuid():
    
    """
    Bit of a hack really. Exposes a controller to populate the UUID field
    of the project proposals. Could be extended to reset any of the UUID 
    fields?
    """
    
    rows = db(db.project_proposals.id > 0).select()
    
    for r in rows:
        r.update_record(project_filled_token = str(uuid.uuid4()))
    
