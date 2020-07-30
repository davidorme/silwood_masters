# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations


response.menu = [
    (T('Home'), False, URL('default', 'index'), []),
    (T('Views'), False, None, [
        (T('Module Grid'), False, URL('default', 'module_grid'), []),
        (T('Course List'), False, URL('default', 'courses'), []),
        (T('Room Grid'), False, URL('default', 'room_grid'), [])
    ]),
    (T('Tables'), False, None, [
        (T('College Dates'), False, URL('default', 'college_dates_table'), []),
        (T('Recurring Events'), False, URL('default', 'recurring_events_table'), []),
        (T('Locations'), False, URL('default', 'locations_table'), []),
        (T('Courses'), False, URL('default', 'courses_table'), []),
        (T('Teaching Staff'), False, URL('default', 'teaching_staff_table'), []),
        (T('Modules'), False, URL('default', 'modules_table'), []),
        (T('Events'), False, URL('default', 'events_table'), [])
    ]),
    (T('Help'), False, URL('default', 'help'), [])
]

if auth.has_membership('admin'):
    response.menu.append((T('Admin'), False, None, [
                            (T('User requests'), False, URL('default', 'user_requests'), []),
                            (T('Freezer'), False, URL('default', 'freezer'), [])]))
