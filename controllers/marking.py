import datetime
import io
import os
import csv
import itertools
import random
import copy
import uuid
from itertools import groupby, chain
import simplejson as json
from marking_functions import (create_pdf, release, distribute, zip_pdfs, download_grades, 
                                       query_report_marker_grades, get_form_header, 
                                       assignment_to_sqlform, style_sqlform, FoldingTOC)

from staff_auth import staff_authorised
import sharepoint
import markdown # gluon provides MARKDOWN but lacks extensions.
from mailer import Mail
from gluon.storage import Storage
from pydal.helpers.methods import smart_query

def help():
    
    filepath = os.path.join(request.folder, 'static', 'docs', 'marking_reports_help.md')
    
    with open(filepath, encoding="utf-8-sig") as help_file:
        
        # OK - this is a hack. Simply reading and displaying static content from MD is
        # straightforward but now there is a dynamic element from the config. The right
        # way to do this would be to write a markdown generic.view handler
        
        help_doc = help_file.read()
        help_doc = XML(markdown.markdown(help_doc))
    
    return dict(help_doc=help_doc)


# ---- action to server uploaded static content (required) ---
@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)
    


## --------------------------------------------------------------------------------
#  Project marking table managment
## --------------------------------------------------------------------------------


@auth.requires_membership('admin')
def marking_roles():
    
    # don't allow deleting as the referencing to project marks will 
    # drop referenced rows from marking tables
    form = SQLFORM.grid(db.marking_roles,
                        fields=[db.marking_roles.name, 
                                db.marking_roles.marking_criteria,
                                db.marking_roles.form_file],
                        csv=False,
                        deletable=False)
    
    return dict(form=form)


@auth.requires_membership('admin')
def submitted_files():
    
    # don't allow deleting, editing or detailas as this is populated automatically
    # from the file structure
    form = SQLFORM.grid(db.marking_files,
                        fields=[db.marking_files.student_cid,
                                db.marking_files.academic_year,
                                db.marking_files.course_presentation_id,
                                db.marking_files.marker_role_id,
                                db.marking_files.filename],
                        maxtextlength=100,
                        csv=False,
                        details=False,
                        editable=False,
                        deletable=False)
    
    return dict(form=form)


## --------------------------------------------------------------------------------
## ADMIN FUNCTIONS
## --------------------------------------------------------------------------------


@auth.requires_membership('admin')
def scan_files():
    """Exposes the scan function."""
    
    # TODO - turn this into something that doesn't just hang around and ? uses
    # AJAX to populate the scan. Also - maybe only scan updated files.
    return sharepoint.scan_files()


## --------------------------------------------------------------------------------
## MARKING ASSIGNMENTS
## - ADMIN FUNCTIONS
## --------------------------------------------------------------------------------

@auth.requires_membership('admin')
def new_assignment():
    
    db.assignments.status.readable = False
    db.assignments.assignment_data.readable = False
    db.assignments.assignment_data.writable = False
    
    db.assignments.student.requires = IS_IN_DB(db, 'students.id', 
                                              '%(student_last_name)s, %(student_first_name)s (%(course)s)')
    
    db.assignments.marker.requires = IS_IN_DB(db, 'markers.id', 
                                              '%(last_name)s, %(first_name)s (%(email)s)')
    
    form = SQLFORM(db.assignments,
                   fields=['student', 
                           'marker',
                           'course_presentation_id',
                           'marker_role_id',
                           'academic_year',
                           'due_date'])
    
    if form.process().accepted:
        response.flash = 'Assignment created'
        redirect(URL('assignments'))
    
    return dict(form=form)


@auth.requires_membership('admin')
def assignments():
    """
    Exposes a grid table of assignments along with functions to run on queried sets
    rows. An older version used selectable to allow admins to select rows, but that doesn't
    play well with large numbers of records and pagination, so this uses  the grid search
    to get subsets and then feeds the search keywords in to run the actions.
    """
    
    # look for the 'all' variable to allow the system to show older records.
    if 'all' in request.vars.keys():
        db.assignments._common_filter = None
        
    # Represent status as icon
    db.assignments.status.represent = lambda id, row: status_dict[row.assignments.status]
    
    # Conceal the id in the form but retain in selected fields for links.
    # db.assignments.id.writable = False
    db.assignments.id.readable = False
    
    # Link to a non-default report page and edit page. Note that this is an admin
    # only page and the write_report() controller allows logged in admin access
    # so no need to pass any security credentials beyond being logged in
    links = [dict(header = 'Report',
                  body = lambda row: A('View',_class='button btn btn-secondary',
                                       _href=URL("marking", "write_report",
                                                 vars={'record': row.assignments.id}))),
             dict(header = 'Assignment',
                  body = lambda row: A('Edit',_class='button btn btn-secondary',
                                       _href=URL("marking", "edit_assignment", 
                                                 args=row.assignments.id)))]
    
    # create the SQLFORM grid to show the existing assignments
    # and set up actions to be applied to selected rows - these
    # are powered by action functions defined below
    
    fields = [db.student_presentations.student,
              db.student_presentations.course_presentation,
              db.student_presentations.academic_year,
              db.assignments.id,
              db.assignments.marker,
              db.assignments.marker_role_id,
              db.assignments.due_date,
              db.assignments.status]
    
    grid = SQLFORM.grid(db(db.assignments.student_presentation == db.student_presentations.id),
                        fields = fields,
                        maxtextlength=100,
                        csv=False,
                        deletable=False,
                        create=False,
                        details=False,
                        editable=False,
                        links=links,
                        headers= {'students.student_last_name': 'Student'},
                        paginate = 50)
    
    # Create a form of buttons to handle the actions
    button_actions = (("send", "Send to markers", distribute, {}),
                      ("release", "Release to students", release, {}),
                      ("cpdf", "Download Confidential PDFs", zip_pdfs, {'confidential': True}),
                      ("pdf", "Download Public PDFs", zip_pdfs, {}),
                      ("grades", "Download Grades", download_grades, {}))
    
    buttons = [INPUT(_type='submit', _name=nm, _value=vl, 
                     _class='btn btn-secondary',
                     _style='margin: 0px 5px',
                     _callback=URL()
                     )
               for nm, vl, _, _ in button_actions]
    
    actions = FORM(*buttons)
    
    if actions.process().accepted:
        
        # Find the action from the post vars
        _, _, action_func, action_args = [b for b in button_actions if b[0] in request.post_vars][0]
        
        # Pass the keywords currently in use by the SQLFORM.grid 
        # back into the db to get the rows they select and hence the list of ids
        if request.get_vars.keywords is None:
            qry = db.assignments
        else:
            qry = smart_query(fields, request.get_vars.keywords)
        
        records = db(qry).select(db.assignments.id)
        records = [r.id for r in records]
        
        # Feed those into the action function
        action_func(ids=records, **action_args)
        
    # old records, turning off the common filter
    old_count = None  # TODO - fix db(db.assignments.academic_year < datetime.datetime.now().year,
                      # ignore_common_filters=True).count()
    
    return dict(form=grid, actions=actions, old_count=old_count)


@auth.requires_membership('admin')
def marker_progress():

    # look for the 'all' variable to allow the system to show older records.
    if 'all' in request.vars.keys():
        db.assignments._common_filter = None
    
    db.markers._format = "%(last_name)s, %(first_name)s"
    
    status_count = db(db.assignments).select(
                        db.assignments.marker, 
                        db.assignments.marker_role_id, 
                        db.assignments.marker_role_id.count().with_alias('n'),
                        db.assignments.status,
                        groupby=[db.assignments.marker, 
                                 db.assignments.status,
                                 db.assignments.marker_role_id])
    
    # Render names and sort by marker
    status_count = list(status_count.render())
    status_count.sort(key=lambda x: x.assignments.marker)

    # Get a template count (not completed, completed) by marker role
    count_template = db(db.marking_roles).select(db.marking_roles.name)
    count_template = {r.name: [0,0] for r in count_template}

    # Build the table
    hdr = TR(*[TH(''), *[TH(x, _colspan=2, _width='20%') for x in count_template.keys()]])
    subhdr = TR([TH('')] + [TH(SPAN('',_class="fa fa-times-circle",
                                  _style="color:red;font-size: 1.3em;")), 
    
                            TH(SPAN('',_class="fa fa-check-circle",
                                  _style="color:green;font-size: 1.3em;"))] *  len(count_template.keys()))
    table = [hdr, subhdr]
    
    # Loop over the marker data
    for marker, data in groupby(status_count, lambda x: x.assignments.marker):
    
        # Fill in a copy of the count template to fix order and gaps
        marker_counts = copy.deepcopy(count_template)
    
        for this_count in data:
            details = this_count.assignments
            # Use a logical index to put completed/released in 1 and everything else in 0
            marker_counts[details.marker_role_id][details.status in ['Completed', 'Released']] += this_count.n
        
        # Style the row 
        row = [[TD(B(v[0]), _style='background-color:salmon') if v[0] else TD(v[0], _style='color:black'), 
                TD(v[1], _style='color:black')] 
               for v in marker_counts.values()]
        row = list(chain(*row))
        
        table.append([TD(marker)] + row)
    
    # Return the formatted table
    return dict(table=TABLE(table, _border=1))


@auth.requires_membership('admin')
def edit_assignment():
    """Edit assignment details
    
    This controller allows an administrator to edit the details of
    an assignment - the marker/role/etc. The contents of 
    db.assignments.assignment_data should be edited via view_assignment.
    
    """
    db.assignments.assignment_data.readable = False
    db.assignments.assignment_data.writable = False
    
    db.assignments.marker.requires = IS_IN_DB(db, 'markers.id', 
                                              '%(last_name)s, %(first_name)s (%(email)s)')
    
    # allow access to previous records.
    db.assignments._common_filter = None
    record = db.assignments[request.args[0]]
    
    db.assignments.marker.requires = IS_IN_DB(db, 'markers.id', '%(last_name)s, %(first_name)s (%(email)s)')
    
    if record.status in ['Created', 'Not started']:
        delete_ok = True
    else:
        delete_ok = False
    
    # # This code used to lock completed reports from editing. But that prevents
    # # accidental submissions from being reopened. Even when released, editing
    # # might be needed to correct issues.
    
    # if record.status in ['Submitted', 'Released']:
    #     readonly = True
    # else:
    #     readonly = False
    
    # Allow admins to change the status
    db.assignments.status.writable = True
    readonly = False
    
    form = SQLFORM(db.assignments,
                   deletable=delete_ok,
                   record=record,
                   readonly=readonly)
    
    if form.process(onvalidation=submit_validation).accepted:
        redirect(URL('assignments'))
    
    return dict(form = form)


@auth.requires_membership('admin')
def load_assignments():
    
    # Get lookups for course presentations and roles
    known_presentations = db(db.presentations).select(db.presentations.id,
                                                      db.presentations.name)
    known_presentations = {rw.name: rw.id for rw in known_presentations}
    
    known_roles = db(db.marking_roles).select(db.marking_roles.id,
                                              db.marking_roles.name)
    known_roles = {rw.name: rw.id for rw in known_roles}
    
    # Expose the upload form
    form = FORM(DIV(DIV('Upload File:', _class='col-sm-2'),
                    DIV(INPUT(_type='file', _name='myfile', id='myfile', 
                              requires=IS_NOT_EMPTY()), _class='col-sm-6'), 
                    DIV(INPUT(_type='submit',_value='Upload', _style='padding:5px 15px',
                              _class='btn btn-primary')
                        ,_class='col-sm-2'),
                    _class='row'))
    
    def _format_error(lst):
        """['', 'afdskh'] --> '"","afdskh"'
        """
        
        lst = [f'"{vl}"' for vl in lst]
        return ','.join(lst)
        
    if form.accepts(request.vars):
        
        # get the data from the request, converting from uploaded bytes into StringIO
        data = io.StringIO(request.vars.myfile.value.decode('UTF-8-SIG'))
        data = csv.DictReader(data)
        
        # create an html upload report as the function runs
        html = ''
        
        # check the headers
        headers = data.fieldnames
        required = ['student_cid', 'student_first_name', 'student_last_name', 'student_email',
                    'course', 'course_presentation', 'academic_year', 'marker_email', 'due_date',
                    'marker_last_name', 'marker_first_name', 'marker_role']
        
        missing_headers = set(required).difference(headers)
        
        if len(missing_headers) > 0:
            
            html = CAT(html,
                       H2('Missing fields in file'),
                       P('These fields are missing from the upload file: ', ', '.join(missing_headers)))
            
            # Nothing is likely to work from this point, so bail early
            return dict(form=form, html=html, known_roles=list(known_roles.keys()), 
                        known_presentations=list(known_presentations.keys()))
        
        # extract the contents into a big list of dictionaries to work with
        # rather than having an iterator that runs through once
        data = [row for row in data]
        
        # Look for blank rows (all empty strings)
        blank = [''.join(row.values()) == '' for row in data]
        
        if sum(blank):
            
            html = CAT(html,
                       H4('Blank lines'),
                       P(f'The input file contains {sum(blank)} blank rows.'))
            
            data = [row for row, bl in zip(data, blank) if not bl]
        
        # - repackage the data into fields to do checks
        fields = {key:[item[key] for item in data] for key in headers}
        
        # - roles are recognized?
        unknown_roles = set(fields['marker_role']).difference(known_roles.keys())
        
        if len(unknown_roles) > 0:
            html = CAT(html,
                       H4('Unknown marking roles'),
                       P('These roles are found in the file but are not recognized: '),
                       P(_format_error(unknown_roles)),
                       P('Valid values are: ', ', '.join(known_roles.keys())))
        
        # - course presentations are recognized?
        unknown_presentations = set(fields['course_presentation']).difference(known_presentations)
        
        if len(unknown_presentations) > 0:
            html = CAT(html,
                       H4('Unknown course presentations'),
                       P('These course presentations are found in the file but are not recognized:'),
                       P(_format_error(unknown_presentations)),
                       P('Valid values are: ', ', '.join(known_presentations.keys())))
        
        # bad student emails
        bad_emails = [IS_EMAIL()(x) for x in fields['student_email']]
        bad_emails = [x[0] for x in bad_emails if x[1] is not None]
        if len(bad_emails) > 0:
            html = CAT(html,
                       H4('Invalid student emails'),
                       P('The following are not well formatted emails: '), 
                       P(_format_error(set(bad_emails))))
            
        # bad marker emails
        bad_emails = [IS_EMAIL()(x) for x in fields['marker_email']]
        bad_emails = [x[0] for x in bad_emails if x[1] is not None]
        if len(bad_emails) > 0:
            html = CAT(html,
                       H4('Invalid marker emails'),
                       P('The following are not well formatted emails: '),
                       P(_format_error(set(bad_emails))))
        
        # due dates not formatted correctly
        bad_dates = [IS_DATE()(x) for x in fields['due_date']]
        bad_dates = [x[0] for x in bad_dates if x[1] is not None]
        if len(bad_dates) > 0:
            html = CAT(html,
                       H4('Invalid due dates'),
                       P('The following are not well formatted dates: '),
                       P(_format_error(set(bad_dates))))
        
        # non numeric years
        years = set(fields['academic_year'])
        bad_years = [ x for x in years if not x.isdigit() ]
        if len(bad_years) > 0:
            html = CAT(html,
                       H4('Invalid year'),
                       P('The following are not valid years: '),
                       P(_format_error(set(bad_years))))
        
        # non numeric CID
        cids = set(fields['student_cid'])
        bad_cids = [ x for x in cids if not x.isdigit() ]
        if len(bad_cids) > 0:
            html = CAT(html,
                       H4('Invalid student CID numbers'),
                       P('The following are not valid CIDs: '),
                       P(_format_error(set(bad_cids))))
        
        # empty names or just whitespace
        names = set(fields['student_first_name'] + fields['student_last_name']+
                    fields['marker_first_name'] + fields['marker_last_name'])
        bad_names = [ x for x in names if x.isspace() or x == '' ]
        
        if len(bad_names) > 0:
            html = CAT(html,
                       H4('Invalid student or marker names'),
                       P('The student and marker names data contains empty strings or '
                         'text just consisting of spaces'))
        
        # NOW validate students and staff against the tables
        
        # extract unique student data as tuples 
        students= set([(x['student_cid'],
                        x['student_first_name'],
                        x['student_last_name'],
                        x['student_email'],
                        x['course']) for x in data])
        
        student_id_map = {}
        bad_student_records = []
        
        for this_student in students:
            
            if this_student[0].isdigit():
                
                # bad CIDs have already been trapped above
                this_cid = int(this_student[0])
                
                student_record = db(db.students.student_cid == this_cid).select().first()
                
                if student_record is not None:
                    if ((student_record.student_first_name != this_student[1]) &
                        (student_record.student_last_name != this_student[2]) &
                        (student_record.student_email != this_student[3]) &
                        (student_record.course != this_student[4])):
                            bad_student_records.append(this_student)
                    else:
                        student_id_map[this_cid] = student_record.id
                else:
                    student_id_map[this_cid] = db.students.insert(student_cid = this_cid,
                                                                  student_first_name = this_student[1],
                                                                  student_last_name = this_student[2],
                                                                  student_email = this_student[3],
                                                                  course = this_student[4])
        
        if len(bad_student_records) > 0:
            html = CAT(html,
                       H4('Inconsistent student records'),
                       P('The students include existing CID numbers with incongruent names and  '
                         'courses: '), 
                       P(_format_error([f"{st[0]} ({st[1]} {st[3]}, {st[3]})"
                                        for st in bad_student_records])))
        
        # Staff
        # extract unique staff entries
        staff = set([(x['marker_first_name'],
                      x['marker_last_name'],
                      x['marker_email']) for x in data])
        
        staff_email_map = {}
        bad_staff_records = []
        
        for this_staff in staff:
            
            staff_record = db(db.markers.email.lower() == this_staff[2].lower()).select().first()
            
            if staff_record is not None:
                if ((staff_record.first_name != this_staff[0]) &
                    (staff_record.last_name != this_staff[1])):
                        bad_staff_records.append(this_staff)
                else:
                    staff_email_map[this_staff[2]] = staff_record.id
            else:
                
                new_id = db.markers.insert(first_name = this_staff[0],
                                           last_name = this_staff[1],
                                           email=this_staff[2])
                staff_email_map[this_staff[2]] = new_id
        
        if len(bad_staff_records) > 0:
            html = CAT(html,
                       H4('Inconsistent marker records'),
                       P('The marker data includes incongruent marker data:'), 
                       P(_format_error([f"{st[0]} {st[1]}, ({st[2]})" 
                                        for st in bad_staff_records])))
        
        # Any problems detected
        if html != '':
            html = CAT(H2('Errors found in the uploaded file', _style='color:darkred'),
                       P('Please edit the file to fix these problems and then repeat the upload'),
                       html)
            
            # revert any database transactions
            db.rollback()
        else:
            
            for assgn in data:
                
                
                db.assignments.insert(student = student_id_map[int(assgn['student_cid'])],
                                      academic_year = int(assgn['academic_year']),
                                      course_presentation_id = known_presentations[assgn['course_presentation']],
                                      marker = staff_email_map[assgn['marker_email']],
                                      marker_role_id = known_roles[assgn['marker_role']],
                                      due_date = assgn['due_date'])
            
            # load the assignments
            html = CAT(H2(str(len(data)) + ' assignments successfully uploaded'))
            
        
    else:
        
        html=''
    
    return dict(form=form, html=html, known_roles=list(known_roles.keys()), 
                known_presentations=list(known_presentations.keys()))



def who_are_my_markers():
    
    # This controller will never show previous years - so does not handle 
    # the ?all URL argument
    
    # Stop students knowing about or searching on the other fields
    db.assignments.id.readable = False
    db.assignments.academic_year.readable = False
    db.assignments.due_date.readable = False
    db.assignments.status.readable = False
    
    # create the SQLFORM grid to show the existing assignments
    grid = SQLFORM.grid(db.assignments.marker_role_id.belongs([1,3]),
                        fields = [db.assignments.student,
                                  db.assignments.course_presentation_id,
                                  db.assignments.marker,
                                  db.assignments.marker_role_id],
                        maxtextlength=100,
                        csv=False,
                        deletable=False,
                        create=False,
                        details=False,
                        editable=False,
                        headers= {'assignments.course_presentation_id': 'Course Presentation',
                                  'assignments.marker_role_id': 'Role'},
                        paginate = 50)
    
    return dict(form=grid)


@staff_authorised
def my_marking():
    
    """
    This controller allows a marker to access a table of assignments that have been
    assigned to them - like the admin assignments() controller - but with much reduced
    capabilities!
    """
    
    # Use 'all' variable in URL to toggle access to previous records
    if 'all' in request.vars:
        db.assignments._common_filter = None
        header = P("The table below shows all the assignments that have been assigned to you ",
                   B("across all years"),". To focus on your current marking assignments, click ",
                   A("here", _href=URL(vars={'all': ''})))
    else:
        header = P("The table below shows your ", B("current marking assignments"),
                   ". To also see records from previous years, click ",
                   A("here", _href=URL()))
    
    # Get the stored session details.
    marker = session.magic_auth
    
    # and edit representations
    db.assignments.status.represent = lambda id, row: status_dict[row.assignments.status]
    
    # link to a non-default new edit page
    links = [dict(header = 'Report', 
                  body = lambda row: A('View',
                                       _class='button btn btn-secondary',
                                       _href=URL("marking", "write_report", 
                                                 vars={'record': row.assignments.id}),
                                       _target='_blank'))]
    
    # create the SQLFORM grid to show the existing assignments
    # and set up actions to be applied to selected rows - these
    # are powered by action functions defined below
    grid = SQLFORM.grid((db.assignments.marker == marker.id) &
                        (db.assignments.student_presentation == db.student_presentations.id),
                        fields = [db.student_presentations.student,
                                  db.student_presentations.academic_year,
                                  db.student_presentations.course_presentation,
                                  db.assignments.marker_role_id,
                                  db.assignments.due_date,
                                  db.assignments.status
                              ],
                        maxtextlength=100,
                        csv=False,
                        deletable=False,
                        create=False,
                        details=False,
                        editable=False,
                        links=links,
                        headers= {'students.student_last_name': 'Student'},
                        paginate=False)
    
    return dict(name=marker.first_name + " " + marker.last_name, header=header, form=grid)


@staff_authorised
def my_students():
    
    """
    This controller allows a supervisor to access a table of students and hence
    a link to the overall reports on their performance
    """
    
    marker = session.magic_auth
    
    # and edit representations
    db.assignments.status.represent = lambda id, row: status_dict[row.status]
    
    # link to a non-default new edit page
    links = [dict(header = 'Report', 
                  body = lambda row: A('View',
                                       _class='button btn btn-secondary',
                                       _href=URL("marking", "presentation_overview", 
                                                 vars={'id': row.student,
                                                       'presentation': row.course_presentation_id,
                                                       'year': row.academic_year
                                                       }),
                                       _target='_blank'))]
    
    # This is automatically all years.
    db.assignments._common_filter = None
    
    # create the SQLFORM grid to show students the marker has supervised
    grid = SQLFORM.grid((db.assignments.marker == marker) & 
                        (db.assignments.marker_role_id == db.marking_roles.id) & 
                        (db.marking_roles.name == 'Supervisor'),
                        fields = [db.assignments.student,
                                  db.assignments.academic_year,
                                  db.assignments.course_presentation_id
                                  ],
                        maxtextlength=100,
                        csv=False,
                        deletable=False,
                        create=False,
                        details=False,
                        editable=False,
                        links=links,
                        headers= {'students.student_last_name': 'Student'},
                        paginate=False)
    
    return dict(name=marker.first_name + " " + marker.last_name, form=grid)

@staff_authorised
def presentation_overview():
    
    """
    This controller presents a summary of the marking on a particular course
    presentation, allowing admin and supervisors to view marking documents
    and performances
    """
    
    marker = session.magic_auth
    
    # and edit representations
    db.assignments.status.represent = lambda id, row: status_dict[row.status]
    
    # This is automatically all years.
    db.assignments._common_filter = None
    
    rows = db((db.assignments.student == request.vars['id']) & 
              (db.assignments.course_presentation_id == request.vars['presentation']) & 
              (db.assignments.academic_year == request.vars['year'])).select()

    if rows:
        
        content = [(TR(TH('Marking Role'), 
                       TH('Marker'),
                       TH('Status'),
                       TH('Grades'),
                       TH('Report')))]
        
        # Create a summary table
        for idx, this_row in enumerate(rows):
            
            # now render it to get representations of ids etc
            rend_row = rows.render(idx)
            
            if this_row.status in ['Submitted', 'Released']:
                
                # Extract the exported grades from the row 
                display_grades = this_row.marker_role_id.form_json['grade_export']
                display_vals = [this_row.assignment_data[x] for x in display_grades]
                
                grades = [P(f'{nm}: {gr}') for nm, gr in zip(display_grades, display_vals)]
                grades = DIV(*grades)
                
                # Create a link to the report
                link = A('Link', _href=URL('write_report', 
                                           vars={'record': this_row.id,
                                                 'supervisor_id': marker.id,
                                                 'staff_access_token': marker.marker_access_token}),
                                _target='_blank')
            else:
                grades = 'Not completed'
                link = "Not available"
            
            # Extend the content 
            content.append((TR(TD(rend_row.marker_role_id),
                               TD(rend_row.marker),
                               TD(rend_row.status),
                               TD(grades),
                               TD(link))))
        
        # Use the last row to get a header block
        header = TABLE(TR(TD('Student:'), TD(rend_row.student)),
                       TR(TD('Course Presentation:'), TD(rend_row.course_presentation_id)),
                       TR(TD('Academic Year:'), TD(rend_row.academic_year)),
                       _class='table table-striped')
                           
        # Render the content as a table
        content = TABLE(*content, _class='table')
    else:
        session.flash = 'Unknown presentation details'
        redirect(URL('index'))
    
    return dict(header=header, content=content)


@staff_authorised
def write_report():
    
    """
    This function generates a form dynamically from a JSON description
    and stores the data in a json field in the database. This approach
    avoids having to declare a bunch of different tables for different 
    forms and then handling the structure of each display. A user can 
    just provide a form definition and a marking criteria file and the
    forms are provided on the fly, with data stored in a single data 
    in the assignments table as a json object.
    
    The JSON form definitions are stored in the marking roles table
    which is referenced from assignments, so the form definition is
    accessible as assignment_record.marking_role_id.form_json
    """
    
    # is the record id valid
    if request.vars['record'] is None:
        session.flash = 'No assignment id provided'
        redirect(URL('index'))
    else:
        # allow old reports to be retrieved
        db.assignments._common_filter = None
        record = db.assignments[int(request.vars['record'])]
        
        if record is None:
            session.flash = 'Unknown assignment id provided'
            redirect(URL('index'))
    
    # Get the marker record
    marker = session.magic_auth
    
    # Access control - if the user is logged in as an admin, then
    # don't need to do any validation, otherwise use 2FA 
    show_due_date = False
    
    if auth.has_membership('admin'):
        
        admin_warn =  DIV(B('Reminder: '), "Logged in administrators have the ability to ",
                          "edit all reports in order to fix mistakes or unfortunate phrasing. ",
                          "Please do not do so lightly.", 
                          _class="alert alert-danger", _role="alert")
        readonly = False
    
    elif request.vars['supervisor_id'] is not None:
        
        admin_warn = ""
        
        # Provide supervisor access to completed reports
        supervisor = db.markers(int(security['supervisor_id']))
        
        if security['staff_access_token'] is None:
            session.flash = 'No staff access token provided'
            redirect(URL('index'))
        
        if supervisor.marker_access_token != security['staff_access_token']:
            session.flash = 'Staff access token invalid'
            redirect(URL('index'))\

        if record.status not in ['Submitted','Released']:
            session.flash = 'Marking not yet submitted'
            redirect(URL('index'))
        
        readonly = True
        
    else:
        
        admin_warn = ""
            
        if marker.id != record.marker:
            raise HTTP(403, '403 Forbidden: this marking is not assigned to you')
        
        if record.status in ['Submitted','Released']:
            readonly = True
        else:
            readonly = False
            show_due_date = True
    
    # define the header block - this is for display so needs the rendered data
    header = get_form_header(record, readonly, security=marker, show_due_date=show_due_date)
    
    # Get the form as html
    # - provide a save and a submit button
    buttons =  [TAG.BUTTON('Save', 
                           _type="submit", _class="button btn btn-danger",
                           _style='width:100px',
                           _name='save'),
                XML('&nbsp;')*5,
                TAG.BUTTON('Submit',
                           _type="submit", _class="button btn btn-danger",
                           _style='width:100px', 
                           _name='submit')]
    
    form = assignment_to_sqlform(record, readonly, buttons)
        
    # process the form to handle storing the data, via a validation function
    # that checks required fields are complete when users press submit. The validation
    # method retrieves form details from the session.
    session.form_json = record.marker_role_id.form_json
    
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
        
        # TODO - Would be neater to use ajax here rather than reloading the page
        # but parking that for another day.
        redirect(URL('write_report', vars={'record': record.id}))
    
    # Style SQLFORM
    html = style_sqlform(record, form, readonly)
    
    # Provide any available files
    expected_files = record.marker_role_id.form_json.get('submitted_files')
    if expected_files:
    
        # TODO FIX
        file_rows =  None
        # db((db.marking_files.student == record.student) &
        #                        (db.student_presentation == record.student_presentation) &
        #                        (db.marking_files.marker_role_id == record.marker_role_id)
        #               ).select()
    
        if file_rows:
            files = CAT(H4("Files"), P("The following submitted files are available. These files are "
                                       "now distributed using the College Sharepoint system so following "
                                       "these links may require you to log in using your college credentials."),
                        UL([A(f.filename, _href=sharepoint.download_url(f)) 
                            for f in file_rows]))
        else:
            files = CAT(H4("Files"), P("The expected submitted files associated with this report "
                                      f"({','.join(expected_files)}) have not yet been uploaded. "
                                       "We often send around marking assignments before students "
                                       "submit coursework, so they may be coming soon. If you have "
                                       "been told the files have been submitted and are still seeing "
                                       "this message, please contact the postgraduate administrator."))
    else:
        files = DIV()
    
    # Set the form title
    response.title = f"{record.student_presentation.student.student_last_name}: {record.marker_role_id.name}"
    
    # Save reminder
    if not readonly:
        save_and_submit = DIV(B('Reminder: '), "Do not forget to ", B('save'), " your progress and ",
                                B("submit"), " it when it is complete, using the buttons at the bottom "
                                "of this page. Do not navigate away from "
                                "this page without saving your changes! Once you have saved your "
                                "work, you can return to your My Assignments page ", 
                                A('here', _href=URL('my_assignments')),
                                 _class="alert alert-danger", _role="alert")
    else:
        save_and_submit = DIV()
    
    my_assignments = P(A('Back to my assignments', _href=URL('my_assignments')))
    
    return dict(header=CAT(admin_warn, *header), 
                save_and_submit=save_and_submit,
                form=CAT(*html), files=files)


def submit_validation(form):
    """
    Takes a submitted form and checks that all components tagged as
    required in the JSON description have been completed. Requires that
    the appropriate form JSON has been stored in the session object, since
    it seems to be impossible to pass extra arguments to onvalidation functions.
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







def criteria_and_forms():
    """Creates a publicly viewable table of marking roles with links to forms and criteria"""
    
    marking_roles = db(db.marking_roles).select()
    
    db.marking_roles.id.readable=False
    
    crit = db.marking_roles.marking_criteria
    crit.represent = lambda value, rw: A(value, _href=URL('static', 
                                                          os.path.join('marking_criteria', value)))

    name = db.marking_roles.name
    name.represent = lambda value, rw: A(value, 
                                         _href=URL('marking', 'show_form', args=rw.name))
    
    marking_roles = SQLFORM.grid(db.marking_roles,
                                 fields=[db.marking_roles.name, 
                                         db.marking_roles.marking_criteria],
                                 details=False,
                                 editable=False,
                                 create=False,
                                 deletable=False,
                                 csv=False,
                                 searchable=False,
                                 sortable=False)
    
    return dict(table=marking_roles)




def show_form():
    """This controller displays a form dynamically from a JSON description
    but as a simple static form with no submit method. This is a convenient
    way for students to be able to see the forms.
    """
    
    role = db(db.marking_roles.name == request.args[0]).select().first()
    
    # Redirect back to form list if the role is unknown
    if role is None:
        session.flash = 'Unknown marking role in show_form'
        redirect(URL('criteria_and_forms'))
    
    # The idea here is to pass something that looks exactly like a real
    # row to the form display methods used in write_report but using
    # some dummy values. That needs to behave exactly like a real record
    # in order to make use of the represent and referencing on a real 
    # Row. So this uses .insert() to create actual rows but then rolls
    # back those inserts before leaving the controller. 
    
    # TODO  - Fix this hack - it really doesn't seem optimal.
    
    db.assignments._common_filter = None
    marker = db.teaching_staff.insert(first_name='Sir Alfred', 
                               last_name='Marker', 
                               email='null@null')
    student = db.students.insert(student_first_name='Awesome', 
                                 student_last_name='Student', 
                                 student_email='null@null', 
                                 student_cid='00000000', 
                                 course=3)
    student_presentation = db.student_presentations.insert(student=student,
                                                           academic_year=2020,
                                                           course_presentation=31)
    record = db.assignments.insert(student_presentation=student_presentation,
                                   status='Not started', 
                                   marker=marker, 
                                   marker_role_id=role.id, 
                                   due_date='1970-01-01')
    
    # Get the new row
    rows = db(db.assignments.id == record).select()
    
    # Render the row to get the field representations and get the record itself
    
    record = rows[0]
    
    # define the header block
    header = get_form_header(record, readonly=False)
    
    # get the form object and style it
    form = assignment_to_sqlform(record, readonly=False)
    html = style_sqlform(record, form, readonly=False)
    
    # Set the form title
    response.title = f"{student.student_last_name}: {record.marker_role_id.name}"
    
    # Rollback the inserts
    db.rollback()
    
    return dict(header=CAT(*header), form=CAT(*html))


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
    if security['staff_access_token'] is None and security['student_access_token'] is None:
        
        session.flash = 'No access token provided for PDF download'
        redirect(URL('index'))
        
    elif security['staff_access_token'] is not None:
        
        marker = db.markers(record.marker)
        
        # Two factor authentication
        if not session.tf_validated:
            _next = URL(args=request.args, vars=request.vars)
            redirect(URL('authenticate', vars=dict(marker=marker.id, _next=_next)))
        
        if marker.marker_access_token != security['staff_access_token']:
            session.flash = 'Staff access token invalid for PDF download'
            redirect(URL('index'))
        else:
            confidential = True
        
    elif security['student_access_token'] is not None:
            
        if record.student.student_access_token != security['student_access_token']:
            session.flash = 'Student access token invalid for PDF download'
            redirect(URL('index'))
        elif record.status != 'Released':
            session.flash = ("Report not yet released. Also, we'd just love to know "
                             "how you got your hands on a valid student access token "
                             "for an unreleased report.")
            redirect(URL('index'))
        else:
            confidential = False
    
    # create the form - this is a separate function so that the file creation 
    # can be used by other functions (like downloading a zipfile of selected pdf)
    pdf, filename = create_pdf(record, confidential=confidential)
    
    # return a pdf version of the record
    response.headers['Content-Type'] = 'application/pdf'
    attachment = 'attachment;filename={}'.format(filename)
    response.headers['Content-Disposition'] = attachment
    
    raise HTTP(200, pdf,
               **{'Content-Type':'application/pdf',
                  'Content-Disposition':attachment + ';'})