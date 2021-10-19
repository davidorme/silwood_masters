# -*- coding: utf-8 -*-
# this file is released under public domain and you can use without limitations

# This minimal constant menu is extended in the controller model folders
# so that it changes by the controller context

response.logo = IMG(_src=URL('static','images/imperial_white.png'), _height='70px')
response.title = request.application.replace('_',' ').title()
response.subtitle = ''


timetabler_dropdown = [
                        (T('Overview'), False, URL('timetabler', 'overview'), []),
                        (T('Module Grid'), False, URL('timetabler', 'module_grid'), []),
                        (T('Course List'), False, URL('timetabler', 'courses'), []),
                        (T('Room Grid'), False, URL('timetabler', 'room_grid'), []),
                        (T('Video tutorial'), False, URL('static', 'video/timetabler_howto.mp4'), [])
                      ]

if auth.has_membership('timetabler') or auth.has_membership('admin'):
    
    timetabler_dropdown.extend(
        [(DIV(_class='dropdown-divider'), False, False, []),
         (DIV('Tables and Tools', _class='dropdown-item', 
         _style='color:grey;font-variant:small-caps'), False, False, []),
         (T('College Dates'), False, URL('timetabler', 'college_dates_table'), []),
         (T('Recurring Events'), False, URL('timetabler', 'recurring_events_table'), []),
         (T('Locations'), False, URL('timetabler', 'locations_table'), []),
         (T('Courses'), False, URL('timetabler', 'courses_table'), []),
         (T('Teaching Staff'), False, URL('manage', 'teaching_staff'), []),
         (T('Modules'), False, URL('timetabler', 'modules_table'), []),
         (T('Events'), False, URL('timetabler', 'events_table'), []),
         (T('Download timetable archive'), False, URL('timetabler', 'archive_timetable'), [])])


if auth.has_membership('wiki editor') or auth.has_membership('admin'):
    wiki_dropdown = (T('Wiki'), False, None, [
                         (T('Pages'), False, URL('wiki','manage_wikicontent'), []),
                         (T('Media'), False, URL('wiki','manage_wikimedia'), []),
                     (  T('Editing the wiki'), False, URL('wiki','wiki', 
                                                          args=['editing-this-wiki']), [])])
else:
     wiki_dropdown =  (T('Wiki'), False, URL('wiki','wiki'), [])




marking_dropdown = [(T('Overview'), False,  URL('marking', 'help'), []), 
                    (T('Criteria and Forms'), False, URL('marking','criteria_and_forms'), []),
                    (T('Video tutorial'), False, URL('static', 'video/marking_howto.mp4'), [])]



if auth.has_membership('admin'):
    marking_dropdown.extend([
        (DIV(_class='dropdown-divider'), False, False, []),
        (DIV('Admin Tools', _class='dropdown-item', 
             _style='color:grey;font-variant:small-caps'), False, False, []),
        (T('Marking Roles'), False, 
            URL('marking', 'marking_roles'), []),
        (T('Create Marking Assignment'), False, 
            URL('marking', 'new_assignment'), []),
        (T('Load Marking Assignments'), False, 
            URL('marking', 'load_assignments'), []),
        (T('View Marking Assignments'), False, 
            URL('marking', 'assignments'), []),
        (T('View Marker Progress'), False, 
            URL('marking', 'marker_progress'), []),
        (T('View Submitted Files'), False, 
            URL('marking', 'submitted_files'), []),
        (T('Scan Files'), False, 
            URL('marking', 'scan_files'), [])])


projects_dropdown = [(T('Overview'), False, URL('projects', 'project_overview'), []),
                     (T('External projects'), False, URL('projects', 'external_projects'), []),
                     (T('Proposals'), False, URL('projects', 'index'), []),
                     (T('Allocations'), False,  URL('projects', 'project_allocations'), [])]


if auth.has_membership('admin'):
    projects_dropdown.extend([
        (DIV(_class='dropdown-divider'), False, False, []),
        (DIV('Admin Tools', _class='dropdown-item', 
             _style='color:grey;font-variant:small-caps'), False, False, []),
        (T('Project Admin'), False, 
            URL('projects', 'project_admin'), [])])


response.menu = [
    (T('Projects'), False, None, projects_dropdown),
    (T('Marking'), False, None, marking_dropdown),
    (T('Timetabler'), False, None, timetabler_dropdown),
    wiki_dropdown
    ]


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

    response.menu.append((T('Manage'), False, None, [
                            (T('Teaching Staff'), False, 
                                URL('manage', 'teaching_staff'), []),
                            (T('Courses'), False, 
                                URL('manage', 'courses'), []),
                            (T('Coursework Presentations'), False, 
                                URL('manage', 'presentations'), []),
                            (T('Students'), False, 
                                URL('manage', 'students'), []),
                            (T('Student Coursework'), False, 
                                URL('manage', 'student_presentations'), []),
                            (T('Upload Students'), False, 
                                URL('manage', 'load_students'), []),
                            (DIV(_class='dropdown-divider'), False, False, []),
                            (CAT(T('View Users'), badge), False, 
                                URL('sm_admin', 'show_users'), []),
                            (T('View Email Log'), False, 
                                URL('sm_admin', 'email_log'), []),
                            (T('Database (requires site password)'), False, 
                                URL(request.application, 'appadmin', 'index'), [])
                            ]))

if session.magic_auth is not None:
    
    response.menu.append((T('Staff'), False, URL('staff', 'home'), [
                         (DIV(f'Welcome {session.magic_auth.first_name}',
                              _class='dropdown-item', 
                              _style='color:grey;font-variant:small-caps'), False, False, []),
                          (T('Home'), False, 
                              URL('staff', 'home'), []),
                          (T('My marking'), False, 
                              URL('marking', 'my_marking'), []),
                          (T('My projects'), False, 
                              URL('projects', 'my_projects'), []),
                          (T('Create project'), False, 
                              URL('projects', 'project_details'), []),
                          (T('Checkout'), False, 
                              URL('staff', 'checkout'), [])
                         ]))

else:
    
    response.menu.append((T('Staff '), False, URL('staff', 'home'), [
                          (T('Staff Login'), False, 
                              URL('staff', 'staff_login'), []),
                         ]))
    
    