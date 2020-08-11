timetabler_menu = [
    (T('Views'), False, None, [
        (T('Module Grid'), False, URL('timetabler', 'module_grid'), []),
        (T('Course List'), False, URL('timetabler', 'courses'), []),
        (T('Room Grid'), False, URL('timetabler', 'room_grid'), [])
    ]),
    (T('Tables'), False, None, [
        (T('College Dates'), False, URL('timetabler', 'college_dates_table'), []),
        (T('Recurring Events'), False, URL('timetabler', 'recurring_events_table'), []),
        (T('Locations'), False, URL('timetabler', 'locations_table'), []),
        (T('Courses'), False, URL('timetabler', 'courses_table'), []),
        (T('Teaching Staff'), False, URL('timetabler', 'teaching_staff_table'), []),
        (T('Modules'), False, URL('timetabler', 'modules_table'), []),
        (T('Events'), False, URL('timetabler', 'events_table'), [])
    ]),
    (T('Help'), False, URL('timetabler', 'help'), [])]

response.menu.extend(timetabler_menu)
