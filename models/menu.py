# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations


response.menu = [
    (T('Home'), False, URL('default', 'index'), []),
    (T('Module Grid'), False, URL('default', 'module_grid'), []),
    (T('Room Grid'), False, URL('default', 'room_grid'), []),
    (T('Tables'), False, None, [
        (T('College Dates'), False, URL('default', 'college_dates'), []),
        (T('Locations'), False, URL('default', 'locations'), []),
        (T('Courses'), False, URL('default', 'courses'), []),
        (T('Teaching Staff'), False, URL('default', 'teaching_staff'), []),
        (T('Modules'), False, URL('default', 'modules'), []),
        (T('Events'), False, URL('default', 'events'), [])
    ]),
]

if auth.has_membership('admin'):
    response.menu.append((T('User requests'), False, URL('default', 'user_requests'), []))
