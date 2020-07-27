# -*- coding: utf-8 -*-
from timetable_functions import (module_markdown, update_module_record_with_dates,
                                 update_event_record_with_dates, convert_date_to_weekdaytime)
import io
import gluon
import datetime
from dateutil import parser
import pypandoc
import markdown # gluon provides MARKDOWN but lacks extensions.

def index():

    return dict()

## TABLE VIEW CONTROLLERS 
## - These can all be viewed by anyone but you have to log in to edit
##   and many are locked down to admin staff only

def teaching_staff_table():
    """Presents a view of teaching staff. Users can add and edit, admin delete
    """
    
    form = SQLFORM.grid(db.teaching_staff,
                        deletable=auth.has_membership('admin'), 
                        csv=is_admin)
    
    return dict(form=form)


def locations_table():
    """Presents a view of teaching staff. Only admins can edit, delete or add
    """
    
    db.locations.id.readable = False
    
    is_admin = auth.has_membership('admin')
    
    form = SQLFORM.grid(db.locations,
                        editable=is_admin,
                        deletable=is_admin,
                        create=is_admin, 
                        csv=is_admin)
    
    return dict(form=form)


def courses_table():
    """Presents a view of courses. Only admins can edit, delete or add
    """
    
    db.courses.id.readable = False
    
    is_admin = auth.has_membership('admin')
    
    form = SQLFORM.grid(db.courses,
                        ignore_common_filters=is_admin,
                        editable=is_admin,
                        deletable=is_admin,
                        create=is_admin, 
                        csv=is_admin)
    
    return dict(form=form)


def college_dates_table():
    """Presents a view of college dates. Only admins can edit, delete or add.
    """
    
    db.college_dates.id.readable = False
    
    is_admin = auth.has_membership('admin')
    
    form = SQLFORM.grid(db.college_dates,
                        editable=is_admin,
                        deletable=is_admin,
                        create=is_admin, 
                        csv=is_admin)
    
    return dict(form=form)


def recurring_events_table():
    """Presents a view of recurring events. Only admins can edit, delete or add.
    """
    
    db.college_dates.id.readable = False
    
    is_admin = auth.has_membership('admin')
    
    form = SQLFORM.grid(db.recurring_events,
                        editable=is_admin,
                        deletable=is_admin,
                        create=is_admin, 
                        csv=is_admin)
    
    return dict(form=form)


def events_table():
    """Presents a view of module events. These should always be edited via events()
    """
    
    db.events.id.readable = False
    is_admin = auth.has_membership('admin')
    
    form = SQLFORM.grid(db.events,
                        fields=[db.events.module_id,
                                db.events.title,
                                db.events.teacher_id],
                        editable=is_admin,
                        deletable=False,
                        create=False,
                        ignore_common_filters=is_admin,
                        csv=is_admin)
    
    return dict(form=form)


def modules_table():
    """Presents a view of modules. These should be edited via module_information()
    but admins can create, delete and edit them here. 
    TODO - enable fullcalendar interface to changing time for admins
    """
    
    db.modules.id.readable = False
    
    is_admin = auth.has_membership('admin')
    
    form = SQLFORM.grid(db.modules,
                        fields=[db.modules.title,
                                db.modules.convenor_id,
                                db.modules.courses],
                        editable=is_admin,
                        deletable=is_admin,
                        create=is_admin,
                        ignore_common_filters=is_admin,
                        csv=is_admin)
    
    return dict(form=form)

## MODULE INFORMATION CONTROLLERS
## - information shows a form for the module level data
## - events provides a week calendar for event editing
## - view renders the existing information as html
## - docx downloads the existing information as docx

def _module_page_header(module_id, current):
    """A helper function to generate the common header for module controllers.
    It also embeds some module data in the html for client side use by the 
    events calendar
    """
    
    # Set of links to create - keep the current link as plain text
    links = [{'title': 'Info', 'url': URL('module_information', args=[module_id])},
             {'title': 'Events', 'url': URL('module_events', args=[module_id])},
             {'title': 'HTML', 'url': URL('module_view', args=[module_id])},
             {'title': 'Word', 'url': URL('module_doc', args=[module_id, 'docx'])},
             {'title': 'LaTeX', 'url': URL('module_doc', args=[module_id, 'latex'])}]
    links = [SPAN(lnk['title'], _style="margin:5px")
                if lnk['title'] == current 
                else SPAN(A(lnk['title'], _href=lnk['url']), _style="margin:5px")
                for lnk in links]
    
    module_record = db.modules[module_id]
    update_module_record_with_dates(module_record)
    module_header = DIV(DIV(H2(module_record.title),
                            _class='col-8'),
                        DIV(B(CAT(links[0], ' + ', links[1], ' = ', links[2] ,
                                  XML('&or;'), links[3], XML('&or;'), links[4], 
                                  _class='pull-right')),
                            _class='col-4'),
                        _class='row', _id='module_data', 
                        _module_id = module_id, _module_start = module_record.start) + HR()
    
    return module_header


def module_information():
    """Controller to return a SQLFORM for module level information"""
    module_id = request.args[0]
    
    
    form = SQLFORM(db.modules, 
                   fields = ['title',
                             'convenor_id',
                             'courses',
                             'description',
                             'aims',
                             'reading',
                             'other_notes'],
                   showid=False,
                   record=module_id, 
                   readonly=not auth.is_logged_in())
    
    return dict(form=form, module_data=_module_page_header(module_id, 'Info'))


def module_events():
    """Controller to deliver a module level calendar and handle event creation and update.
    Editing is only possible for logged in users, but anyone can view and click through."""
    
    if len(request.args) == 1:
        module_id = request.args[0]
        event_id = None
    else:
        module_id = request.args[0]
        event_id = request.args[1]
    
    if auth.is_logged_in():
        db.events._common_filter = None
    
    module_record = db.modules[module_id]
    update_module_record_with_dates(module_record)
    
    # USE SQLFORM to create the event form when an event id is passed in the arguments
    # otherwise create some instructions. The day, time and duration fields are not 
    # included. This information is stored in hidden fields in the form and updated 
    # by using fullcalendar - the resulting information is copied back into the form
    # internally below
    
    if event_id is not None:
        record = db(db.events.id == event_id).select().first()
        form=SQLFORM(db.events,
                     deletable=auth.is_logged_in(),
                     record = record,
                     fields = ['title', 'description', 'teacher_id', 
                               'location_id', 'courses', 'conceal'],
                     hidden = dict(academic_week=record.academic_week,
                                   event_day=record.day_of_week,
                                   duration=record.duration,
                                   start_time=record.start_time),
                     #formstyle='bootstrap3_stacked',
                     showid=False,
                     readonly=not auth.is_logged_in())
    elif auth.is_logged_in():
        form= DIV(H4('Options'),
                  UL(LI('Click on an existing event to unlock it for editing. '
                        'You can drag and resize the event to reschedule it and '
                        'edit the event details in the form that will appear. '
                        'Remember to press the Submit button after making changes!',
                        #_style='padding:2px'
                        ),
                     LI('Drag and drop the event below to create a new event:',
                        CENTER(DIV(DIV(DIV(CENTER('New event!'),
                                    _class='fc-event-main', 
                                    **{'data-event': '{ "title": "newevent", "duration": "01:00" }'}),
                                _class='fc-event fc-h-event fc-daygrid-event fc-daygrid-block-event',
                                _style='padding:10px;width:150px'),
                            _id='external-events')),
                        _style='padding:2px'),
                     LI('You can use ', 
                        A('Markdown', _href='https://guides.github.com/features/mastering-markdown/'),
                        ' to easily add formatting to your content.',
                        _style='padding:2px'),
                     LI('Follow these links to add new ', 
                        A('teaching staff', _href=URL('teaching_staff')),
                        ' or ',
                        A('locations', _href=URL('locations')),
                        ' if needed.',
                        _style='padding:2px'),
                     LI('Events can be deleted or concealed - a concealed event will stay '
                        'in the database and can be seen by registered users and unconcealed, '
                        'but a deleted event is gone')),
                  _class='jumbotron')
    else:
        form= DIV(H4('Options'),
                  UL(LI('Log in to edit events.'),
                     LI('Click on an event to see event details.')),
                  _class='jumbotron')
        
    
    # Process the form if that is what comes back, first adding the hidden fields back in
    if isinstance(form, gluon.sqlhtml.SQLFORM):
        form.vars.start_time = request.vars.start_time
        form.vars.event_day = request.vars.event_day
        form.vars.duration = request.vars.duration
    
    if isinstance(form, gluon.sqlhtml.SQLFORM) and form.process().accepted:
        redirect(URL(args=[module_id]))
    
    return dict(module_data=_module_page_header(module_id, 'Events'),
                event_data=DIV(_id='event_data', _event_id=event_id),
                form=form)


def module_view():
    """A controller to combine module and event email and then display, converting
    markdown to HTML along the way. Anyone can view.
    """
    
    module_id = request.args[0] 
    
    content= module_markdown(module_id)
    
    return dict(content = XML(markdown.markdown(content, extensions=['def_list'])), 
                module_data=_module_page_header(module_id, 'HTML'))


def module_doc():
    """A controller to push out a document version of the view, using pandoc to convert 
    markdown into docx or latex. Anyone can access.
    """
    
    module_id = request.args[0] 
    output_format = request.args[1] 
    
    content= module_markdown(module_id, title=True)
    
    if output_format == 'docx':
        # With docx, the output _has_ to be written to a file, not just handled internally
        # as a string. Also, oddly, streaming the response from an open file directly 
        # reuslt in weird stalling behaviour and failure, but loading it to bytes and 
        # streaming the content of that works flawlessly. <shrug>
        
        filename = f'Module_{module_id}_{datetime.date.today()}.docx'
        url = os.path.join('static', 'module_docx',  filename)
        filepath = os.path.join(request.folder, url)
        template = os.path.join(request.folder, 'static', 'module_docx',  'docx_template.docx')
        pypandoc.convert_text(content, 'docx', format='md',  outputfile=filepath,
                              extra_args=[f"--reference-doc={template}"])
    
        with open(filepath, 'rb') as fin:
            data = io.BytesIO(fin.read())
        ctype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    elif output_format == 'latex':
        # With latex, can just directly pass the string
        filename = f'Module_{module_id}_{datetime.date.today()}.tex'
        data = pypandoc.convert_text(content, 'latex', format='md')
        ctype = 'application/x-tex'
    
    disposition = f'attachment; filename={filename}'
    raise HTTP(200, data,
               **{'Content-Type': ctype,
               'Content-Disposition': disposition})

def course_doc():
    """A controller to push out a DOCX version of a course, using pandoc to convert 
    markdown into the docx. Anyone can access.
    """
    
    course_id = request.args[0] 
    output_format = request.args[1]
    
    content = ""
    
    course = db.courses[course_id]
    modules = db(db.modules.courses.contains(course_id)
                 ).select(db.modules.id,
                          db.modules.title,
                          db.modules.convenor_id)
    
    # Convert ids to representation
    modules = list(modules.render())
    
    # Add dates and sort in time order
    _ = [update_module_record_with_dates(row) for row in modules]
    modules.sort(key=lambda row: row.start)
    
    # Process into a definition list (tables and pandoc again)
    content += '## Weekly module summary\n\n\n'
    for mod in modules:
        week = ((mod.start - FIRST_DAY).days // 7) + 1
        content += f'Week {week} - {mod.title}\n'
        content += f':   Convenor: {mod.convenor_id}  \n'
        content += f'    Dates: {mod.start} - {mod.end}\n\n'

    content += '## Module details\n\n'
    
    for mod in modules:
        content += module_markdown(mod.id, title=True)
    
    if output_format == 'docx':
        # With docx, the output _has_ to be written to a file, not just handled internally
        # as a string. Also, oddly, streaming the response from an open file directly 
        # reuslt in weird stalling behaviour and failure, but loading it to bytes and 
        # streaming the content of that works flawlessly. <shrug>
        
        filename = f'{course.abbrname}_{datetime.date.today()}.docx'
        url = os.path.join('static', 'module_docx',  filename)
        filepath = os.path.join(request.folder, url)
        template = os.path.join(request.folder, 'static', 'module_docx',  'docx_template.docx')
        pypandoc.convert_text(content, 'docx', format='md',  outputfile=filepath,
                              extra_args=[f"--reference-doc={template}"])
    
    
        with open(filepath, 'rb') as fin:
            data = io.BytesIO(fin.read())
        ctype = 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
    
    elif output_format == 'latex':
        # With latex, can just directly pass the string
        filename = f'{course.abbrname}_{datetime.date.today()}.tex'
        data = pypandoc.convert_text(content, 'latex', format='md')
        ctype = 'application/x-tex'
        
    disposition = f'attachment; filename={filename}'
    raise HTTP(200, data,
               **{'Content-Type': ctype,
               'Content-Disposition': disposition})

## Other views

def module_grid():
    """A controller to view the sequence of modules by course. Anyone can access.
    TODO - add admin level edit to move modules on calendar.
    """
    
    # Use a div to pass the year academic start data to the client for use by fullcalendar
    year_data = DIV(_id='year_data', _day_one=FIRST_DAY)
    
    return dict(year_data=year_data)


def room_grid():
    """A controller to view the weekly use of rooms by module. Anyone can access.
    """
    # Use a div to pass the year academic start data to the client for use by fullcalendar
    year_data = DIV(_id='year_data', _day_one=FIRST_DAY)
    
    return dict(year_data=year_data)


def courses():
    """A controller to view the modules in a course
    """
    
    # if the URL has no arguments, present a list of courses with URLs
    if len(request.args) == 0:
        
        courses = db(db.courses).select()
        courses = list(courses.render())
        
        table_rows = []
        for crs in courses:
            row = TR(TD(B(crs.fullname), DIV(_style='flex:1'), 
                        A('View', _href=URL('courses', args=crs.id)),
                     _style='display:flex'))
            table_rows.append(row)
            row = TR(TD(DIV(_style='flex:1'), crs.convenor,
                     _style='display:flex'))
            table_rows.append(row)
            
            table = TABLE(table_rows, _class='table-striped')
        
        return dict(table=table, header=H2('Course list'))
    
    # Otherwise get the requested course module list
    course_id = int(request.args[0])
    
    course = db.courses[course_id]
    modules = db(db.modules.courses.contains(course_id)
                 ).select(db.modules.id, 
                          db.modules.title,
                          db.modules.convenor_id)
    
    header = CAT(H2(course.fullname),
                 P(B('Course Convenor: '), course.convenor),
                 P(B('Course Co-convenor: '), course.coconvenor),
                 P(B('Download course timetable: '), 
                     SPAN(A('Word', _href=URL('course_doc', args=[course.id, 'docx'])),
                          _style="margin:5px"),
                     XML('&or;'),
                     SPAN(A('LaTeX', _href=URL('course_doc', args=[course.id, 'latex'])),
                          _style="margin:5px"),
                     ))
    
    # Convert ids to representation
    modules = list(modules.render())
    
    # Add dates and sort in time order
    _ = [update_module_record_with_dates(row) for row in modules]
    modules.sort(key=lambda row: row.start)
    
    # Process into a table - would be nice to still use fullCalendar but
    # it doesn't provide a week slot only day and time
    table_rows = []
    for mod in modules:
        week = ((mod.start - FIRST_DAY).days // 7) + 1
        row = TR(TD(f'Week {week}', _style='width:20%'),
                 TD(B(mod.title), DIV(_style='flex:1'), 
                    A('View', _href=URL('module_view', args=mod.id)),
                 _style='display:flex'))
        table_rows.append(row)
        row = TR(TD(),
                 TD(mod.start, DIV(_style='flex:1'), mod.convenor_id,
                 _style='display:flex'))
        table_rows.append(row)
    
    table = TABLE(table_rows, _class='table-striped')
    
    
    return dict(header=header, table=CAT(H3('Module list'), table))

## Admin

@auth.requires_membership('admin')
def user_requests():
    
    # By default, the registration key is not visible or editable
    db.auth_user.registration_key.readable=True
    db.auth_user.registration_key.writable=True
    
    form = SQLFORM.grid(db(db.auth_user.registration_key == 'pending'))
    
    return dict(form = form)


@auth.requires_membership('admin')
def freezer():
    
    # By default, the registration key is not visible or editable
    rec = db(db.freezer).select().first()
    form = SQLFORM(db.freezer,
                   record=rec.id)
    
    if form.process().accepted:
        redirect(URL('index'))
    
    return dict(form = form)


##
## Data services
##
## fullcalendar automatically sends start and end to do lazy loading of events, 
## but that is currently not implemented in any of these services.


def call():
    session.forget()
    return service()

@service.json
def get_college_dates(start=None, end=None):
    """Service to provide college dates as events, merging college dates and 
    recurring events into a single feed
    """
    
    college_dates = db(db.college_dates).select()
    
    json = []
    
    for record in college_dates:
        if record.event_startdate is not None:
            
            entry = dict(id=record.id,
                         title=record.name)
            if record.event_enddate is not None:
                entry['start'] = record.event_startdate
                entry['end'] = record.event_enddate
                entry['allDay'] = True
            elif record.event_duration is not None:
                start_time = datetime.time(9,0) if record.event_starttime is None else record.event_starttime
                entry['start'] = datetime.datetime.combine(record.event_startdate, start_time)
                entry['end'] = entry['start'] + datetime.timedelta(hours=record.event_duration)
                entry['allDay'] = False
            
            json.append(entry)
    
    recurring = db(db.recurring_events).select()
    
    for record in recurring:
        entry = dict({'daysOfWeek':[record.day_of_week],
                      'title':record.title,
                      'id':record.id, 
                      'startRecur': record.recur_startdate,
                      'endRecur': record.recur_enddate})
        if record.all_day:
            entry['allDay'] = True
        else:
            entry['startTime'] = record.start_time
            entry['endTime'] = record.end_time
        
        json.append(entry)
    
    return json


@service.json
def get_events(module_id, start=None, end=None, event_id=None):
    """Service to provide the events within a module with locations as resources"""
    
    # Use the events set from the module to get the module details
    # and the events. Logged in users get to see concealed events
    if auth.is_logged_in():
        db.events._common_filter = None
    
    module = db.modules[module_id]
    events = module.events.select()
    
    events_json = []
    
    for ev in events:
        update_event_record_with_dates(ev)
        ev_dict = dict(id=ev.id,
                       title=ev.title,
                       start=ev.start,
                       end=ev.end,
                       color='cornflowerblue',
                       editable=False,
                       resourceIds=ev.location_id,
                       extendedProps=dict(description=ev.description,
                                          teacher_id=ev.teacher_id),
                       url=URL('module_events',args=[module_id, ev.id]))
        
        if event_id != 'null':
            event_id = int(event_id)
            
            if ev.conceal == True:
                ev_dict['color'] = 'grey'
            
            if ev.id == event_id:
                ev_dict['color'] = 'salmon'
            
            if ev.id == event_id and auth.is_logged_in():
                ev_dict['editable'] = True
        
        events_json.append(ev_dict)
        
    return events_json


@auth.requires_login()
@service.json
def post_new_event(module_id, datetime, duration):
    """Used to create a new event when fullcalendar fires eventReceive"""
    
    success, *data = convert_date_to_weekdaytime(datetime)
    
    if not success:
        return None
    
    recid = db.events.insert(title='New event',
                             academic_week=data[0],
                             day_of_week=data[1],
                             start_time=data[2],
                             duration=duration,
                             module_id=module_id)
    
    record = db.events[recid]

    return record.id


@service.json
def get_events_by_week(start=None, end=None):
    """Service to provide a week of events with locations as resources"""
    
    # Get modules that intersect the start date
    start = parser.isoparse(start).date()
    modules = db(db.modules).select()
    [update_module_record_with_dates(mod) for mod in modules]
    
    these_modules = [mod for mod in modules if (mod.start <= start) and (mod.end > start)]
    
    if not these_modules:
        return []
    
    module_start_date = these_modules[0].start
    events = db(db.events.module_id.belongs([mod.id for mod in modules])).select()
    
    events_json = []
    
    for ev in events:
        update_event_record_with_dates(ev, module_start_date)
        
        ev = dict(id=ev.id,
                  title=ev.title,
                  start=ev.start,
                  end=ev.end,
                  resourceIds=ev.location_id,
                  extendedProps=dict(description=ev.description,
                                     teacher_id=ev.teacher_id),
                  url=URL('events',args=[ev.module_id, ev.id]))
        
        ev['color'] = 'grey'
        
        events_json.append(ev)
        
    return events_json


@service.json
def get_locations():
    """Service to provide locations as fullcalendar resource data"""
    
    locs = db(db.locations).select(db.locations.id, db.locations.title, db.locations.is_external)
    
    return locs


@service.json
def get_courses():
    """Service to provide courses as fullcalendar resource data"""
    
    courses = db(db.courses).select(db.courses.id, db.courses.abbrname)
    
    for crs in courses:
        crs.title = crs.abbrname
        crs.pop('abbrname')
    
    return courses


@service.json
def get_modules(start=None, end=None, course_id=None):
    """Service to provides module level events for the module grid. At the moment
    the course_id option isn't used -  full calendar can't do a week level slot,
    and a day by day list is ugly."""
    
    if course_id is None:
        query = db.modules
    else:
        query = db.modules.courses.contains(course_id)
    
    modules = db(query).select(db.modules.id, 
                               db.modules.title,
                               db.modules.courses)
    
    # This is a bit clumsy - need to add start, end and url
    # and convert courses entry to resourceIDs
    _ = [update_module_record_with_dates(m) for m in modules]
    for mod in modules:
        mod.url = URL('module_view', args=mod.id)
        mod.resourceIds = mod.courses
        mod.pop('courses')
    
    return modules


# ---- Action for login/register/etc (required for auth) -----
def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())

# ---- action to server uploaded static content (required) ---
@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)
