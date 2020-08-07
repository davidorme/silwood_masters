# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# This minimal constant menu is extended in the controller model folders
# so that it changes by the controller context

response.menu = [
    (T('Home'), False, URL('default', 'index'), []),
    (T('Marking'), False, URL('marking', 'index'), []),
    (T('Timetabler'), False, URL('timetabler', 'index'), [])]
