import datetime
from dateutil import parser
from itertools import groupby

# The web2py HTML helpers are provided by gluon. This also provides the 'current' object, which
# provides the web2py 'request' API (note the single letter difference from the requests package!).
# The 'current' object is also extended by models/db.py to include the current 'db' DAL object
# so it can accessed by this module

from gluon import current

def get_year_start_date():
    
    db = current.db
    start_of_year = db(db.college_dates.name == 'First Monday of Autumn Term').select().first()
    
    if start_of_year is not None:
        return start_of_year.event_startdate
    else:
        return None



def convert_date_to_weekdaytime(value, start_of_year=None):
    """Takes a string representation of a date or datetime objects and converts
    it into the academic week, day and time. If the value is a date, the time will
    be 00:00.
    """

    if isinstance(value, datetime.date):
        value = datetime.datetime.combine(value, datetime.time.min)
    elif isinstance(value, datetime.datetime):
        pass
    elif not isinstance(value, str):
        return 0, 'value not a string'
    else:
        try:
            # values come in from JAVA with Z UTC indicator, so use a parser that 
            # handles this and then strip the tzinfo for comparison to internal dates
            value = parser.isoparse(value)
            value = value.replace(tzinfo=None)
        except ValueError as e:
            return 0, str(e)
    
    if start_of_year is None:
        start_of_year = current.FIRST_DAY
    
    diff = value - datetime.datetime.combine(start_of_year, datetime.time.min)
    
    weeks = (diff.days // 7) + 1 # Week 1 is week 1 not week 0
    days = diff.days % 7
    
    return 1, weeks, days, value.time()


def update_module_record_with_dates(module, for_fullcalendar=False):
    """Calculates the start and end date of a module from the module events 
    and inserts it into the record object in place. If there are no events 
    yet then the placeholder week and duration are used."""
    
    events = module.events.select()
    [update_event_record_with_dates(ev) for ev in events]
    
    if len(events):
        module.start = min([ev.start for ev in events]).date()
        module.end = max([ev.end for ev in events]).date()
        # fullcalendar end is exclusive, so need to add one if these dates
        # are being used to populate events in fullcalendar
        if for_fullcalendar:
            module.end =  module.end + datetime.timedelta(days=1)
    else:
        try:
            # academic placeholder weeks are base-1 not base-0
            module.start = current.FIRST_DAY + datetime.timedelta(weeks=module.placeholder_week - 1)
            # placeholders cover monday to friday and fullcalendar end dates are exclusive,
            # so don't need to account for the extra day at the start
            placeholder_length = (module.placeholder_n_weeks * 5 + 
                                  (module.placeholder_n_weeks - 1) * 2)
            module.end = module.start + datetime.timedelta(days=placeholder_length)
        except TypeError:
            module.start = current.FIRST_DAY
            module.end = current.FIRST_DAY


def update_event_record_with_dates(event, week=1, duration=1, event_day=0, 
                                   start_time=datetime.time(9,0)):
    """Calculates the start and end date of an event from the event row 
    and module start date and inserts them into the record object in place."""
    
    #TODO are these virtual fields?
    
    week = week if event.academic_week is None else event.academic_week
    duration = duration if event.duration is None else event.duration
    event_day = event_day if event.day_of_week is None else event.day_of_week
    start_time = start_time if event.start_time is None else event.start_time
    
    event_date = current.FIRST_DAY + datetime.timedelta(weeks=week - 1,
                                                        days=event_day)
    
    event.start = datetime.datetime.combine(event_date, start_time)
    event.end = event.start + datetime.timedelta(hours=duration)


def module_markdown(module_id, title=False, show_events=True):
    """Gets a markdown version of the module information and events
    """
    
    db = current.db
    
    # update the format of teaching_staff rows
    db.teaching_staff._format = lambda row: f" {row.first_name} {row.last_name}" 
    
    module = db(db.modules.id == module_id).select()
    module = list(module.render())[0]
    update_module_record_with_dates(module)
    
    if title:
        content = f'### {module.title}\n'
    else:
        content =""
    
    content += f'**Convenors**: {module.convenors}  \n'
    
    if not module.is_series:
        data = convert_date_to_weekdaytime(module.start)
        content += f'**Week**: {data[1]}  \n'
    
    content += f'**Dates**: {module.start} to {module.end}  \n'
    content += f'**Courses**: {module.courses}\n\n'
    
    sections = [('description', '#### Description'), 
                ('aims', '#### Aims'),
                ('reading', '#### Reading'),
                ('delivery', '#### Module delivery'),
                ('other_notes', '#### Additional information')]
    
    # Load and format events
    for fld, title in sections:
        if module[fld] is not None and module[fld] != "":
            content += f'{title}\n\n{module[fld]}\n\n'
    
    if show_events:
        
        events = db(db.events.module_id == module_id
                    ).select(orderby=[db.events.academic_week,
                                      db.events.day_of_week,
                                      db.events.start_time])
        events = list(events.render())
        [update_event_record_with_dates(ev) for ev in events]
    
        events_by_day = groupby(events, lambda x: x.start.date())
    
        content += '#### Events:\n\n'
    
        # It would be neater to do this using tables but pandoc tables are seriously
        # limited at present - the core functions are now there but the reader and 
        # writers are not yet updated. Definition lists provide a reasonable solution:
        # <dd> tags can be styled with an indent in html and the docx output has a 
        # 'definition' style that can also have an indent applied. 
    
        for key, gp in events_by_day:
            gp = list(gp)
        
            content += f'**{gp[0].start.strftime("%A %B %d")}**  \n\n'
        
            for ev in gp:
                content += f'{ev.start.strftime("%H:%M")} - {ev.end.strftime("%H:%M")} {ev.title}  \n'
                content += f':   *Staff*: {ev.teacher_id}  \n'
                content += f'    *Locations*: {ev.location_id}  \n'
                if ev.courses is not None:
                    content += f'    *Courses*: {ev.courses}  \n'
                if ev.description is not None:
                    content += f'    *Description*: {ev.description}  \n\n'
    
    content += '\n\n\n\n'
    
    return content
