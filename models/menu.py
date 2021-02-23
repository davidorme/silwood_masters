# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# This minimal constant menu is extended in the controller model folders
# so that it changes by the controller context

response.logo = IMG(_src=URL('static','images/imperial_white.png'), _height='70px')
response.title = request.application.replace('_',' ').title()
response.subtitle = ''

response.menu = [
    (T('Marking'), False, URL('marking_reports', 'index'), []),
    (T('Timetabler'), False, URL('timetabler', 'index'), []),
    (T('Info'), False, URL('marking_reports', 'wiki'), [])]


if auth.has_membership('admin'):
    
    n_new = db(db.auth_user.registration_key == 'pending').count()
    if n_new == 0:
        badge = SPAN('0 new', 
                     _class="badge badge-pill badge-secondary",
                     _style='margin:0px 5px')
    else:
        badge = SPAN(str(n_new) + ' new', 
                     _class="badge badge-pill badge-danger",
                     _style='margin:0px 5px')
    
    response.menu.append((T('Admin tools'), False, None, [
                            (T('Create Marking Assignment'), False, 
                                URL('marking_reports', 'new_assignment'), []),
                            (T('Load Marking Assignments'), False, 
                                URL('marking_reports', 'load_assignments'), []),
                            (T('View Marking Assignments'), False, 
                                URL('marking_reports', 'assignments'), []),
                            (T('View Project Markers'), False, 
                                URL('marking_reports', 'markers'), []),
                            (T('View Marking Presentations'), False, 
                                URL('marking_reports', 'presentations'), []),
                            (T('View Marking Roles'), False, 
                                URL('marking_reports', 'marking_roles'), []),
                            (T('View Students'), False, 
                                URL('marking_reports', 'students'), []),
                            (T('View Submitted Files'), False, 
                                URL('marking_reports', 'submitted_files'), []),
                            (T('Scan Files'), False, 
                                URL('marking_reports', 'scan_files'), []),
                            (DIV(_class='dropdown-divider'), False, False, []),
                            (T('Timetable freezer'), False, 
                                URL('timetabler', 'freezer'), []),
                            (DIV(_class='dropdown-divider'), False, False, []),
                            (CAT(T('View Users'), badge), False, 
                                URL('sm_admin', 'show_users'), []),
                            (T('View Email Log'), False, 
                                URL('sm_admin', 'email_log'), []),
                            (T('Database (requires site password)'), False, 
                                URL(request.application, 'appadmin', 'index'), [])
                            ]))


response.menu.append((DIV(_style='border-left: 3px solid #FFFFFF80; height: 40px;margin:0px 10px'),
                      False, False, []))

