import datetime
from dateutil import parser
from itertools import groupby


# The web2py HTML helpers are provided by gluon. This also provides the 'current' object, which
# provides the web2py 'request' API (note the single letter difference from the requests package!).
# The 'current' object is also extended by models/db.py to include the current 'db' DAL object
# so it can accessed by this module

from gluon import current

def get_year_start_datetime():
    
    db = current.db
    start_of_year = db(db.college_dates.name == 'First Monday of Autumn Term').select().first()
    start_of_year = datetime.datetime.combine(start_of_year.event_startdate, datetime.time.min)
    return start_of_year


def convert_date_to_weekdaytime(value):
    """Takes a datetime string coming in from client POST data and converts
    it into the academic week, day and time.
    """
    
    if not isinstance(value, str):
        return 0, 'value not a string'
    
    try:
        # values come in from JAVA with Z UTC indicator, so use a parser that 
        # handles this and then strip the tzinfo for comparison to internal dates
        value = parser.isoparse(value)
        value = value.replace(tzinfo=None)
    except ValueError as e:
        return 0, str(e)
    
    start_of_year = get_year_start_datetime()
    diff = value - start_of_year
    
    weeks = (diff.days // 7) + 1 # Week 1 is week 1 not week 0
    days = diff.days % 7
    
    return 1, weeks, days, value.time()


def update_module_record_with_dates(module):
    """Calculates the start and end date of a module from the row 
    and inserts it into the record object in place."""
    
    db = current.db
    start_of_year = db(db.college_dates.name == 'First Monday of Autumn Term').select().first()
    start_of_year = start_of_year.event_startdate
    
    if module.module_week is None:
        module.module_week = 1
    
    if module.module_ndays is None:
        module.module_ndays = 5
    
    module.start = start_of_year + datetime.timedelta(weeks=module.module_week - 1)
    module.end = module.start + datetime.timedelta(days=module.module_ndays)


def update_event_record_with_dates(event, module_startdate, 
                                   duration=1, event_day=0, start_time=datetime.time(9,0)):
    """Calculates the start and end date of an event from the event row 
    and module start date and inserts them into the record object in place."""

    duration = duration if event.duration is None else event.duration
    event_day = event_day if event.event_day is None else event.event_day
    start_time = start_time if event.start_time is None else event.start_time
    
    event.start = datetime.datetime.combine(module_startdate + 
                                            datetime.timedelta(days=event_day),
                                            start_time)
    event.end = event.start + datetime.timedelta(hours=duration)


def module_markdown(module_id, title=False):
    """Gets a markdown version of the module information and events
    """
    
    db = current.db
    module = db(db.modules.id == module_id).select()
    module = list(module.render())[0]
    update_module_record_with_dates(module)
    
    if title:
        content = f'# {module.title}\n'
    else:
        content =""
    
    content += f'**Convenor**: {module.convenor_id}  \n'
    content += f'**Dates**: {module.start} to {module.end}  \n'
    content += f'**Courses**: {module.courses}\n\n'
    
    sections = [('description', '### Description'), 
                ('aims', '### Aims'),
                ('reading', '### Reading'),
                ('other_notes', '### Additional information')]
    
    # Load and format events
    for fld, title in sections:
        if module[fld] is not None and module[fld] != "":
            content += f'{title}\n\n{module[fld]}\n\n'
    
    events = db(db.module_events.module_id == module_id
                ).select(orderby=[db.module_events.event_day,
                                  db.module_events.start_time])
    events = list(events.render())
    [update_event_record_with_dates(ev, module.start) for ev in events]
    
    events_by_day = groupby(events, lambda x: x.event_day)
    
    content += '### Events:\n\n'
    
    for key, gp in events_by_day:
        gp = list(gp)
        
        content += f'**{gp[0].start.strftime("%A %B %d")}**  \n'
        
        for ev in gp:
            content += f'{ev.start.strftime("%H:%M")} - {ev.end.strftime("%H:%M")}'
            content += f' **{ev.title}** ({ev.teacher_id}, {ev.location_id})  \n'
            content += f'{ev.description}  \n'
        
    return content
