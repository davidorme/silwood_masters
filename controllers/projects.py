from staff_auth import staff_authorised
from gluon.sqlhtml import ExportClass
from io import StringIO

## -----------------------------------------------------------------------------
## Project proposal handlers.
## One view option that students can see, with a custom view function
## One submission handler for use by staff
## -----------------------------------------------------------------------------

def project_overview():
    
    return dict()

def project_proposals():
    
    """
    Controller to serve up the contents of the proposals database as a nice
    searchable grid.
    """
    
    # Hide the internal ID numbers and project student (used in links)
    db.projects.id.readable=False
    db.projects.project_student.readable = False
    
    # DEV - Add a secret switch to show older projects
    date_created = request.vars.get('date_created')
    
    if date_created is None:
        date_created = FIRST_DAY - datetime.timedelta(days=60)    
    
    # Show available status as an icon
    filled_icons = {True: SPAN(_class='fa fa-users',
                               _style='color:green;font-size: 1.3em;',
                               _title='Available'),
                    False: SPAN(_class='fa fa-user', 
                                _style='color:red;font-size: 1.3em;',
                                _title='Filled')}
    
    links = [dict(header = 'Info', 
                  body = lambda row: A(SPAN('',_class="fa fa-info-circle", 
                                            _style='font-size: 1.3em;',
                                            _title='See details'),
                                       _class="button btn btn-default", 
                                       _href=URL("projects","view_project", 
                                                 vars={'id': row.id}, user_signature=True),
                                       _style='padding: 3px 5px 3px 5px;')),
            dict(header = 'Open', 
                 body = lambda row: filled_icons[row.project_student is None])]
    
    # show the standard grid display
    # - restrict list display to a few key fields
    # - sub in a custom view function for the normal details link
    # - just give the CSV export link, which is moved from the bottom to
    #   the search bar using in javascript in the view.
    grid  = SQLFORM.grid((db.projects.date_created > date_created),
                         fields = [db.projects.project_student,
                                   db.projects.lead_supervisor,
                                   db.projects.project_base,
                                   db.projects.project_title,
                                   db.projects.date_created
                                   ],
                         headers = {'projects.project_student': "Available"},
                         links = links,
                         details = False,
                         maxtextlength=250,
                         create=False, # using a custom create form
                         csv=True,
                         searchable=True,
                         # exportclasses =  dict(
                         #   csv_with_hidden_cols=(ExporterCSV_hidden, 'CSV (hidden cols)', T(...))),
                         exportclasses = dict(json=False, html=False,
                                              tsv=False, xml=False,
                                              tsv_with_hidden_cols=False,
                                              csv_with_hidden_cols=False),
                         formargs={'showid':False},
                         #orderby= ~db.projects.date_created
                         )
    
    # Huh exportclasses:  CSV uses represent, CSV hidden doesn't. Need a bespoke exporter to
    # show a subset in the grid and export a bigger group with represent.
    
    # edit the grid object
    # - extract the download button and retitle it
    # - insert it in the search menu
    # TODO - restructure this option
    
    # download = A('Download all', _class="btn btn-secondary btn-sm",
    #               _href=URL('project_proposals',
    #                         vars={'_export_type': 'csv'}))
    #
    # if grid.element('.web2py_console form') is not None:
    #     grid.element('.web2py_console form').append(download)
    
    return(dict(grid=grid))


def view_project():
    
    """
    Controller to provide a nicely styled custom view of project details
    """
    
    # retrieve the news post id from the page arguments passed by the button
    # and then get the row and send it to the view
    project_id = request.vars.get('id')
    
    if project_id is None:
        session.flash = CENTER(B('No project number provided.'), _style='color: red')
        redirect(URL('projects','project_proposals'))
    
    project = db.projects(int(project_id))
    
    if project is None:
        session.flash = CENTER(B('Invalid project number.'), _style='color: red')
        redirect(URL('projects','project_proposals'))
    
    # Filled?
    
    if project.project_student is None:
        
        filled = DIV()
    
    else:
        
        filled = DIV(DIV(B("Project filled: "), "This project has been allocated to "
                         f"{project.project_student.student.student_first_name} "
                         f"{project.project_student.student.student_last_name} ("
                         f"{project.project_student.course_presentation.name}, "
                         f"{project.project_student.academic_year}). Supervisors "
                          "are sometimes able to offer other similar projects, so "
                          "it may be worth getting in touch but you should not expect "
                          "that a similar project will be available.",
                         _class='card-body', _style='padding:10px'),
                     _class='card', _style='margin-bottom:20px')
    
    
    # Supervisor details
    if project.lead_supervisor.is_internal:
        internal = DIV()
        
    else:
        
        if project.internal_supervisor is not None:
            int_text = ('The lead supervisor for this project is not based at Imperial College '
                        'London or the Natural History Museum and requires an internal '
                        'supervisor. They have suggested the staff member above and you should '
                        'contact both about this project')
            
            internal = DIV(DIV(B('Internal Supervisor'), _class="col-sm-3"),
                               DIV(project.internal_supervisor.first_name, " ",
                                   project.internal_supervisor.last_name, " (",
                                   A(project.internal_supervisor.email, 
                                     _href=f"mailto:{project.internal_supervisor.email}"), ')',
                                   P(int_text),
                                   _class="col-sm-9"),
                                _class='row', _style='min-height:30px')
        else:
            internal = DIV(DIV(B('Internal Supervisor'), _class="col-sm-3"),
                               DIV("The lead supervisor for this project is not based at "
                                   "Imperial College London or the Natural History Museum "
                                   "and requires an internal supervisor. With the lead "
                                   "supervisor you will need to identify an internal before "
                                   "this project can be accepted.",
                                   _class="col-sm-9"),
                                _class='row', _style='min-height:30px')
    
    if project.other_supervisors is not None:
        
        other_supervisors = [f"{s.first_name} {s.last_name} ({s.email})" 
                             for s in project.other_supervisors]
        other_supervisors = DIV(DIV(B('Other supervisors'), _class="col-sm-3"),
                               DIV(', '.join(other_supervisors),
                                   _class="col-sm-9"),
                                _class='row', _style='min-height:30px')
    else:
        
        other_supervisors = DIV()
        
    
    # package up the proposal in a neat set of foldable containers
    propview =  DIV(H3('Project proposal details'),
                    P('Please look carefully through the proposal details below. If you are interested '
                      'in the project then contact the supervisor, explaining why you are interested and '
                      'any background which makes you a good fit for the project. '
                      'Please pay close attention to any extra notes on requirements (such as being able to '
                      'drive or to speak particular languages) or the application process.'),
                    filled, 
                    DIV(DIV(B("Project title"), _class="col-sm-3"),
                        DIV(project.project_title, _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    DIV(DIV(B("Lead Supervisor"), _class="col-sm-3"),
                        DIV(project.lead_supervisor.first_name, " ",
                            project.lead_supervisor.last_name, " (",
                            A(project.lead_supervisor.email, 
                              _href=f"mailto:{project.lead_supervisor.email}"), ')',
                            _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    internal,
                    other_supervisors,
                    DIV(DIV(B("Project description"), _class="col-sm-3"),
                        DIV(XML(project.project_description.replace('\n', '<br />')), _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    DIV(DIV(B("Project based at"), _class="col-sm-3"),
                        DIV(project.project_base, _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),
                    DIV(DIV(B("Project type"), _class="col-sm-3"),
                        DIV(project.project_type, _class="col-sm-9"),
                        _class='row', _style='min-height:30px'),

                   )
    
    # some more optional components
    if project.requirements:
        propview += DIV(DIV(B("Additional requirements"), _class="col-sm-3"),
                        DIV(project.requirements, _class="col-sm-9"),
                        _class='row', _style='min-height:30px')

    if project.support:
        propview += DIV(DIV(B("Available support"), _class="col-sm-3"),
                        DIV(project.support, _class="col-sm-9"),
                        _class='row', _style='min-height:30px')
    
    if project.eligibility:
        propview += DIV(DIV(B("Selection and eligibility"), _class="col-sm-3"),
                        DIV(project.eligibility, _class="col-sm-9"),
                        _class='row', _style='min-height:30px')
    
    # add the date created
    propview += DIV(DIV(B("Date uploaded"), _class="col-sm-3"),
                    DIV(project.date_created.isoformat(), _class="col-sm-9"),
                    _class='row', _style='min-height:30px')

    # if there are any limitations, add a section
    if project.project_length or project.available_project_dates or project.course_restrictions:
        
        limits = [DIV('The lead supervisor has set some limitations on what courses this proposal '
                      'is suitable for. If you are very interested in the topic but have '
                      'problems with the stated limitations, the supervisor ',B('may'), ' still be '
                      'happy to consider other students, but you should not assume that the '
                      'proposal can be adapted.',
                       _class='list-group-item')]
        
        if project.project_length:
            limits += [LI(DIV(DIV(B("Project length limitations"), _class="col-sm-3"),
                              DIV(', '.join(project.project_length), _class="col-sm-9"),
                              _class='row'),
                         _class='list-group-item')]

        if project.available_project_dates:
            limits += [LI(DIV(DIV(B("Available date limitations"), _class="col-sm-3"),
                              DIV(', '.join(project.available_project_dates), _class="col-sm-9"),
                              _class='row'),
                         _class='list-group-item')]

        if project.course_restrictions:
            limits += [LI(DIV(DIV(B("Suitable for"), _class="col-sm-3"),
                              DIV(', '.join(project.course_restrictions), _class="col-sm-9"),
                              _class='row'),
                         _class='list-group-item')]
        
        limits = UL(*limits, _class="list-group list-group-flush")

        limits = DIV(DIV('Project proposal limitations',
                         _class='card-header bg-danger text-white'),
                         limits,
                       _class='card')

        propview += limits
    
    return dict(proposal = propview)


@staff_authorised
def project_details():
    """
    This form allows an authorised staff member to submit a project proposal to the database or 
    edit an existing proposal. The authorised staff member is  automatically the lead supervisor. 
    For external supervisors (defined in the teaching_staff table), there is the opportunity to
    add an internal supervisor. This should not be mandatory until a project is filled.
    
    For logged in Admin users, the lead supervisor field is not locked, to allow projects to
    be added with any marker as lead.
    """
    
    # Get the authenticated staff details (None if admin logged in)
    staff = session.magic_auth
    
    # If this form is called with the variable record, then load the existing details
    # for that record into the form
    record = request.vars.get('record')
        
    db.projects.date_created.writable = False
    
    # If there is a record in the request then reload those details
    if record is not None:
        record = db.projects[record]
    
        if record is None:
            raise HTTP(404, 'Unknown project record id')
        
        buttons = ['Update']
        
        # # TODO - ability to hide unfilled projects?
        # if record.withdrawn:
        #     buttons.append('Repost')
        # else:
        #     buttons.append('Withdraw')
        
    else:
        buttons = ['Create']
        
        # Hide fields
        db.projects.date_created.readable = False
        
    # Tailor which fields are fixed or showm
    # - Authenticated staff:
    #   - can only make projects with themselves as lead
    #   - internals do not get presented with the internal dropdown
    #   - cannot deselect project students
    
    # Format the student selection dropdown labels
    # NOTE: https://stackoverflow.com/questions/53100625/
    
    def repr_string(row):
         return (f"{row.student.student_last_name}, " 
                 f"{row.student.student_first_name} ("
                 f"{row.course_presentation.name})")
    
    if not auth.has_membership('admin'):
        
        if record is not None and record.lead_supervisor != staff.id:
            raise HTTP(404, 'No access permitted to projects lead by other staff.')
        
        db.projects.lead_supervisor.default = staff.id
        db.projects.lead_supervisor.writable = False
        
        if staff.is_internal:
            db.projects.internal_supervisor.writable = False
            db.projects.internal_supervisor.readable = False
        elif record.internal_supervisor is None:
            # Cannot select a student until an internal is agreed
            db.projects.project_student.writable = False
            db.projects.project_student.represent = lambda row: 'Students cannot be accepted for external projects until an internal supervisor has been agreed'
    
    if record is None or record.project_student is  None:
        
        # find a list of current students that have not already been assigned a project
        qry = db((db.student_presentations.academic_year == FIRST_DAY.year) & 
                 (db.projects.project_student == None))
        left = db.projects.on(db.student_presentations.id == db.projects.project_student)
    
    
        ps_reqr = IS_NULL_OR(IS_IN_DB(qry,
                                      'student_presentations.id', 
                                      lambda  row: repr_string(row),
                                      left=left,
                                      zero='Select a student to assign this project',
                                      sort=True))
    
        db.projects.project_student.requires = ps_reqr
        
    elif auth.has_membership('admin'):
        
        # Admin can remove student.
        ps_reqr = IS_NULL_OR(IS_IN_DB(db(db.student_presentations.id == record.project_student),
                                      'student_presentations.id', 
                                      lambda  row: repr_string(row),
                                      zero='Remove this assigned student',
                                      #default=record.project_student,
                                      sort=True))
    
        db.projects.project_student.requires = ps_reqr
        
    else:
        
        # Lock down set project students
        db.projects.project_student.writable = False
        db.projects.project_student.represent = lambda row: repr_string(row)

    
    buttons = [TAG.button(val, _value=True,_type="submit", _name=val, _class="btn btn-primary")
               for val in buttons]
    
    # Get the SQLFORM for the projects table
    form  = SQLFORM(db.projects,
                    record = record,
                    showid = False,
                    buttons = buttons
                    )
    
    # process the form
    if form.process(onvalidation=validate_project).accepted:
        
        response.flash = "Project created"

    elif form.errors:
        
        response.flash = "Problems"
        
    # Project base selector. The idea here is to provide some common names using a drop down
    # but allowing an Other choice that then expands a free text input

    base_select = form.element('select[name=project_base]') 
    base_select.attributes['_onchange'] = 'check_pbase(this.value)'
    base_select.attributes['_onload'] = 'load_pbase()'
    base_select.parent.insert(0, SCRIPT("""
    function check_pbase(val){
        if(val==="Other")
           document.getElementById('project_proposals_project_base_other'
                                   ).style.display='block';
        else
           document.getElementById('project_proposals_project_base_other'
                                   ).style.display='none';};
    """))
    base_select.append(INPUT(_class="form-control string",
                       _id="project_proposals_project_base_other",
                       _name="project_base_other",
                       _type="text",
                       _value="",
                       _placeholder="Institution name",
                       _style="display:none"))
    
    form.element('textarea[name=requirements]')['_rows']= 3
    form.element('textarea[name=support]')['_rows']= 3
    form.element('textarea[name=eligibility]')['_rows']= 3
    
    # Dictionary of help comments for rows (Note that there is a labels option in
    # SQLFORM but only a spectacularly ugly table3cols implementation.)
    var_help = {'project_student': 
                   'This is normally left blank when creating a project and then completed when '
                   'you have agreed to take on a particular student, but you can create and fill '
                   'the project in one go.',
                'lead_supervisor': 
                   'This is the person that will be responsible for the day to day supervision '
                   'of the project and who will complete the supervisor assessment',
                'internal_supervisor': 
                    'For external projects, a member of staff at Imperial College London or '
                    'the NHM must agree to act as an internal supervisor before the project '
                    'can start. This can be left empty but a student cannot be accepted until '
                    'an internal has been agreed.',
                'other_supervisors': 
                    P('This can be used to select multiple other people who will be involved in '
                    'project supervision. If you need additional staff to be added to the '
                    'list, please ', A('email us', _href='mailto:silwood.masters@imperial.ac.uk')),
                'project_base':
                    'Please select the organisation where the student will be based for the '
                    ' majority of the project (excluding fieldwork).',
                'project_title':
                    'Please provide a title. Students will initially see a list of supervisors, '
                    'project locations and titles, so make it catchy!',
                'project_description': 
                    'Provide a brief description of the main project aims, possibly including'
                    ' any key references',
                'project_type': 'Please indicate the broad research skills involved in this '
                    'project - you can select multiple options.',
                'requirements': 'Additional skills or experience required: most analytical '
                    'skills and methods should be taught during the project but vital skills '
                    'or experience (languages, driving, etc) should be given here',
                'support': 'Details of any non-academic project support - logistics or '
                    'bursaries, for example',
                'eligibility': 'If the project has a deadline or a particular selection criterion '
                    ' or process, please provide brief details.',
                'project_length':
                    'Indicate if the proposal is only suited to particular lengths of '
                    'student projects',
                'available_project_dates':
                    'Indicate if the proposal is only available at particular times of the year',
                'course_restrictions':
                    'Indicate if the proposal is only suited to students with the background '
                    'of particular courses'}
    
    
    # Add help in the form of collapsing info rows below each field
    for idx, form_row in enumerate(form.elements('div.form-group,row')):
        
        row_label = form_row.components[0]
        
        #First element in each row is a label, except for the submit button
        if not isinstance(row_label, str) and row_label.tag == 'label':
            
            row_var = row_label['_for'].replace('projects_','')
            info_collapse_id = row_label.attributes['_for'] + '_info'
            
            # - add an info icon that triggers a collapsing row
            row_label.insert(1, DIV(SPAN(_class='fa fa-info-circle',
                                         _style='color:cornflowerblue;font-size: 1.3em;',
                                         _title='Unknown',
                                         **{'_data-toggle': "collapse",
                                            '_data-target': "#" + info_collapse_id}),
                                    _class='pull-right'))
            
            # - intersperse the collapsing rows into the form components
            help_div = DIV(DIV(DIV(_class='col-sm-3'),
                               DIV(DIV(var_help.get(row_var), 
                                       _class='card',
                                       _style='padding: 0px 5px; margin-bottom:16px; color:red'),
                                   _class='col-sm-9'),
                               _class='form_group row'),
                           _class='collapse',
                           _id=info_collapse_id)
            
            form.components[0].insert(idx * 2 + 1, help_div)
    
    return(dict(form = form))

def validate_project(form):
    
    # Before processing the form object (which only considers fields in the table), 
    # sub the other text from the request.vars into the form.vars slot.
    
    if request.vars.project_base == 'Other':
        print('I am here')
        if request.vars.project_base_other == '':
            form.errors.project_base ='For other project bases, please provide an institution name'
        else:
            form.vars.project_base = request.vars.project_base_other
    
    # Date created is only set when the project is first created or separately updated.
    if form.vars.date_created is None:
        form.vars.date_created = datetime.date.today()



def _none_to_dash(val, row, fmt, none_val="----"):
    """General purpose reformatter to take a row and return a formatted value
    unless the value is None, then return "----"
    """
    
    if val is None:
        return none_val
    else:
         return fmt.format(row=row)


@staff_authorised
def my_projects():
    
    # Hide ID and date_created but used to create a link.
    db.projects.id.readable = False
    db.projects.date_created.readable = False
    
    # Allow open old projects to be refreshed
    def _refresh(row):
        
        if ((row.student_presentations.student is None) and
            (row.projects.date_created < (FIRST_DAY - datetime.timedelta(days=60)))):
            
            return CENTER(A(SPAN('', _class="fa fa-repeat", 
                              _style='font-size: 1.3em;',
                              _title='Refresh'),
                    _class="button btn btn-default", 
                    _href=URL("projects","refresh_project", 
                              vars={'record':row.projects.id}),
                    _style='padding: 3px 5px 3px 5px;'))
        else:
            
            return CENTER(SPAN('', _class="fa fa-times", 
                              _style='font-size: 1.3em;color: grey',
                              _title='Cannot refresh'))
    
    # Clone any project
    def _clone(row):
                    
            return A(SPAN('', _class="fa fa-clone", 
                              _style='font-size: 1.3em;',
                              _title='Clone'),
                     _class="button btn btn-default", 
                     _href=URL("projects","clone_project", 
                               vars={'record':row.projects.id}),
                     _style='padding: 3px 5px 3px 5px;')
    
    # Show visibility
    def _visible(row):
        
        if row.projects.date_created > (FIRST_DAY - datetime.timedelta(days=60)):
            
            return CENTER(SPAN('', _class="fa fa-eye", 
                              _style='font-size: 1.3em;',
                              _title='Visible'))
        else:
            return CENTER(SPAN('', _class="fa fa-eye-slash", 
                              _style='font-size: 1.3em;color: grey',
                              _title='Hidden'))
    
    links = [dict(header = 'Visible', 
                  body = lambda row: _visible(row)),
             dict(header = 'Edit', 
                  body = lambda row: A(SPAN('',_class="fa fa-pencil", 
                                            _style='font-size: 1.3em;',
                                            _title='Edit project'),
                                       _class="button btn btn-default", 
                                       _href=URL("projects","project_details", 
                                                 vars={'record':row.projects.id}),
                                       _style='padding: 3px 5px 3px 5px;')),
             dict(header = 'Refresh', 
                  body = lambda row: _refresh(row)),
             dict(header = 'Clone', 
                  body = lambda row: _clone(row))]
    
    # Cosmetic changes to hide None for unallocated projects.
    std_fmt =  ("{row.student_presentations.student.student_first_name} "
                "{row.student_presentations.student.student_last_name}")
    yr_fmt = "{row.student_presentations.academic_year}"
    cp_fmt = "{row.student_presentations.course_presentation.name}"
    
    tbl = db.student_presentations
    tbl.student.represent = lambda val, row: _none_to_dash(val, row, std_fmt)
    tbl.academic_year.represent = lambda val, row: _none_to_dash(val, row, yr_fmt)
    tbl.course_presentation.represent = lambda val, row: _none_to_dash(val, row, cp_fmt)
    
    # Make the grid
    # - sorted to put open projects at the top and then most recent filled projects.
    form = SQLFORM.grid(db(db.projects.lead_supervisor == session.magic_auth.id) ,
                           fields=[db.projects.id,
                                   db.student_presentations.student,
                                   db.student_presentations.academic_year,
                                   db.student_presentations.course_presentation,
                                   db.projects.project_title,
                                   db.projects.date_created],
                           left = db.student_presentations.on(db.student_presentations.id 
                                                              == db.projects.project_student),
                           orderby= ('("student_presentations"."academic_year" IS NOT NULL) ASC, '
                                     'student_presentations.academic_year DESC'),
                           links=links,
                           details=False,
                           headers = {'projects.date_created': 'Visible?'},
                           create=False,
                           csv=False,
                           maxtextlengths={},
                           maxtextlength=250)
    
    return dict(form=form)



@staff_authorised
def clone_project():
    """
    This controller allows an authorised staff member to clone any a project proposal. 
    Filled projects are copied with the project student removed.
    """
    
    # Get the authenticated staff details (None if admin logged in)
    staff = session.magic_auth
    
    # If this form is called with the variable record, then load the existing details
    # for that record into the form
    record = request.vars.get('record')
    
    # If there is a record in the request then reload those details
    if record is not None:
        record = db.projects[record]
    
        if record is None:
            raise HTTP(404, 'Unknown project record id')
    else:
        raise HTTP(404, 'No project id provided')
    
    # - Authenticated staff can only readvertise their own projects
    if not auth.has_membership('admin') and record.lead_supervisor != staff.id:
            raise HTTP(404, 'You are not the project lead supervisor .')
    
    # Copy details and then insert as a new record with today's date. If the project is
    # open then project_student is already None, otherwise overwrite it
    record = record.as_dict()
    record.update(id=None, 
                  project_student=None,
                  date_created=datetime.date.today())
    clone_id = db.projects.insert(**record)
    
    redirect(URL('projects', 'project_details', vars={'record': clone_id}))


@staff_authorised
def refresh_project():
    """
    This controller allows an authorised staff member to update the creation date of an open
    project.
    """
    
    # Get the authenticated staff details (None if admin logged in)
    staff = session.magic_auth
    
    # If this form is called with the variable record, then load the existing details
    # for that record into the form
    record = request.vars.get('record')
    
    # If there is a record in the request then reload those details
    if record is not None:
        record = db.projects[record]
    
        if record is None:
            raise HTTP(404, 'Unknown project record id')
    else:
        raise HTTP(404, 'No project id provided')
    
    # - Authenticated staff can only readvertise their own projects
    if not auth.has_membership('admin') and record.lead_supervisor != staff.id:
        raise HTTP(403, 'You are not the project lead supervisor .')
    
    # Update the creation date
    if record.project_student is not None:
        raise HTTP(403, 'Cannot refresh a filled project.')
    
    
    record.update_record(date_created=datetime.date.today())
    
    redirect(URL('projects', 'project_details', vars={'record': record.id}))


class AllocationsCSV(ExportClass):
    """
    This is an allocations specific export class - bit of an overkill, but offers finer 
    control over the structure of the download file (represent, and changing column names)
    """
    
    label = 'CSV'
    file_ext = "csv"
    content_type = "text/csv"

    def __init__(self, rows):
        ExportClass.__init__(self, rows)

    def export(self):
        if self.rows:
            s = StringIO()
            
            # There is no way to rename the fields being written out, but _can_ write
            # them to the StringIO first and then leave off the colnames in the export
            colnames = ['student_cid', 'student_first_name', 'student_last_name',
                        'academic_year', 'course_presentation', 'project_title',
                        'supervisor_name', 'supervisor_roles']
            
            s.write(','.join(colnames) + '\n')
            
            self.rows.export_to_csv_file(s, represent=True, write_colnames = False)
            return s.getvalue()
        else:
            return None


def project_allocations():
    """
    Provides a controller to review the mapping of students to projects - showing all students
    including students with no assigned projects. The download format for this page is expected
    - with the addition of marker columns - as the input to load assignments.
    """
    
    # Get preset links to courses:
    
    coursepres = db(db.course_presentations.is_active == True).select()
    
    coursepres = [(rw.name, f'student_presentations.course_presentation="{rw.id}" and '
                            f'student_presentations.academic_year="{FIRST_DAY.year}"')
                  for rw in coursepres]
    
    coursepres = [A(vl[0], _href=URL('projects', 'project_allocations',
                                             vars={'keywords': vl[1]}))
                  for vl in coursepres]
    
    # https://stackoverflow.com/questions/5920643/
    presets  = [B(' | ')] * (len(coursepres) * 2 - 1)
    presets[0::2] = coursepres
    presets = CAT(presets)
    
    links = [dict(header = 'Details', 
                  body = lambda row: A(SPAN('',_class="fa fa-info-circle", 
                                            _style='font-size: 1.3em;',
                                            _title='Edit project'),
                                       _class="button btn btn-default", 
                                       _href=URL("projects","view_project", 
                                                 vars={'id':row.projects.id}),
                                       _style='padding: 3px 5px 3px 5px;')
                                       if row.projects.id is not None else 
                                       SPAN('',_class="fa fa-times-circle", 
                                              _style='font-size: 1.3em;color: grey',
                                              _title='Edit project'))]
    
    # Cosmetic changes to hide None for students with no projects
    # - This is a bit hacky - could join in teaching staff and shorten some of these,
    #   but then need to exclude noise from search again
    sup_fmt = "{row.projects.lead_supervisor.first_name} {row.projects.lead_supervisor.last_name}"
    sup_eml = "{row.projects.lead_supervisor.email}"
    prt_fmt = "{row.projects.project_title}"
    db.projects.lead_supervisor.represent = lambda val, row: _none_to_dash(val, row, sup_fmt)
    db.projects.project_title.represent = lambda val, row: _none_to_dash(val, row, prt_fmt)
    db.projects.id.represent = lambda val, row: _none_to_dash(val, row, sup_eml)
    
    # Hide excess fields from search
    db.students.id.readable = False
    db.students.student_email.readable = False
    db.students.course.readable = False
    db.students.academic_year.readable = False
    db.projects.internal_supervisor.readable = False
    db.projects.project_description.readable = False
    db.projects.project_base.readable = False
    db.projects.eligibility.readable = False
    db.projects.requirements.readable = False
    db.projects.date_created.readable = False
    db.projects.support.readable = False
    # db.projects.id.readable = False
    db.projects.project_student.readable = False
    db.student_presentations.id.readable = False
    db.student_presentations.student.readable = False
    
    # Left join - so that students with no project appear with null projects
    # - Setting csv=False suppresses download buttons, but the exportclasses machinery
    #   is still availabe using the URL vars _export_type and _export_filename
    # - Bit of a hack using represent to add in supervisor email without having join 
    #   teaching_staff in to the table - lazy really.
    form = SQLFORM.grid((db.students.id == db.student_presentations.student),
                        fields=[db.students.student_cid,
                                db.students.student_first_name,
                                db.students.student_last_name,
                                db.student_presentations.academic_year,
                                db.student_presentations.course_presentation,
                                db.projects.project_title,
                                db.projects.lead_supervisor,
                                db.projects.id,
                                ],
                        headers = {
                                'students.student_cid': 'CID',
                                'students.student_first_name': 'First Name',
                                'students.student_last_name': 'Last Name',
                                'student_presentations.academic_year': 'Year',
                                'student_presentations.course_presentation': 'Presentation',
                                'projects.lead_supervisor': 'Supervisor Name',
                                'projects.id': 'Supervisor',
                                'projects.project_title': 'Title'
                        },
                        field_id = db.projects.id,
                        left=db.projects.on(db.student_presentations.id == db.projects.project_student),
                        deletable=False,
                        editable=False,
                        details=False,
                        links=links,
                        csv=False,
                        exportclasses = dict(csv=(AllocationsCSV, 'CSV', T(...)),))
    
    # Insert a download button using the exportclasses machinery
    download = A('Download', _class="btn btn-secondary btn-sm",
                  _href=URL('project_allocations',
                            vars={'_export_type': 'csv',
                                  '_export_filename': f"project_allocations_{datetime.date.today().isoformat()}",
                                  'keywords': '' if request.vars.keywords is None else request.vars.keywords }))

    if form.element('.web2py_console form') is not None:
        form.element('.web2py_console form').append(download)
    
    return dict(form=form, presets=presets)


@auth.requires_membership('admin')
def project_admin():
    """
    This is essentially a clone of my projects but without reducing to only one supervisor.
    TODO - it may be possible to do this smarter with a single controller, but hey.
    """
    
    # Hide ID and date_created but used to create a link.
    db.projects.id.readable = False
    db.projects.date_created.readable = False
    
    # Allow open old projects to be refreshed
    def _refresh(row):
        
        if ((row.student_presentations.student is None) and
            (row.projects.date_created < (FIRST_DAY - datetime.timedelta(days=60)))):
            
            return CENTER(A(SPAN('', _class="fa fa-repeat", 
                              _style='font-size: 1.3em;',
                              _title='Refresh'),
                    _class="button btn btn-default", 
                    _href=URL("projects","refresh_project", 
                              vars={'record':row.projects.id}),
                    _style='padding: 3px 5px 3px 5px;'))
        else:
            
            return CENTER(SPAN('', _class="fa fa-times", 
                              _style='font-size: 1.3em;color: grey',
                              _title='Cannot refresh'))
    
    # Clone any project
    def _clone(row):
                    
            return A(SPAN('', _class="fa fa-clone", 
                              _style='font-size: 1.3em;',
                              _title='Clone'),
                     _class="button btn btn-default", 
                     _href=URL("projects","clone_project", 
                               vars={'record':row.projects.id}),
                     _style='padding: 3px 5px 3px 5px;')
    
    # Show visibility
    def _visible(row):
        
        if row.projects.date_created > (FIRST_DAY - datetime.timedelta(days=60)):
            
            return CENTER(SPAN('', _class="fa fa-eye", 
                              _style='font-size: 1.3em;',
                              _title='Visible'))
        else:
            return CENTER(SPAN('', _class="fa fa-eye-slash", 
                              _style='font-size: 1.3em;color: grey',
                              _title='Hidden'))
    
    links = [dict(header = 'Visible', 
                  body = lambda row: _visible(row)),
             dict(header = 'Edit', 
                  body = lambda row: A(SPAN('',_class="fa fa-pencil", 
                                            _style='font-size: 1.3em;',
                                            _title='Edit project'),
                                       _class="button btn btn-default", 
                                       _href=URL("projects","project_details", 
                                                 vars={'record':row.projects.id}),
                                       _style='padding: 3px 5px 3px 5px;')),
             dict(header = 'Refresh', 
                  body = lambda row: _refresh(row)),
             dict(header = 'Clone', 
                  body = lambda row: _clone(row))]
    
    # Cosmetic changes to hide None for unallocated projects.
    std_fmt =  ("{row.student_presentations.student.student_first_name} "
                "{row.student_presentations.student.student_last_name}")
    yr_fmt = "{row.student_presentations.academic_year}"
    cp_fmt = "{row.student_presentations.course_presentation.name}"
    
    tbl = db.student_presentations
    tbl.student.represent = lambda val, row: _none_to_dash(val, row, std_fmt)
    tbl.academic_year.represent = lambda val, row: _none_to_dash(val, row, yr_fmt)
    tbl.course_presentation.represent = lambda val, row: _none_to_dash(val, row, cp_fmt)
    
    # Make the grid
    # - sorted to put open projects at the top and then most recent filled projects.
    form = SQLFORM.grid(db.projects,
                           fields=[db.projects.id,
                                   db.student_presentations.student,
                                   db.student_presentations.academic_year,
                                   db.student_presentations.course_presentation,
                                   db.projects.project_title,
                                   db.projects.date_created],
                           left = db.student_presentations.on(db.student_presentations.id 
                                                              == db.projects.project_student),
                           orderby= ('("student_presentations"."academic_year" IS NOT NULL) ASC, '
                                     'student_presentations.academic_year DESC'),
                           links=links,
                           details=False,
                           deletable=False,
                           editable=False,
                           headers = {'projects.date_created': 'Visible?'},
                           create=False,
                           csv=False,
                           maxtextlengths={},
                           maxtextlength=250)
    
    return dict(form=form)

