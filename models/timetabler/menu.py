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
                                  (T('Freezer'), False, 
                                      URL('timetabler', 'freezer'), []),
                                  (DIV(_class='dropdown-divider'), False, False, []),
                                  (SPAN(T('View Users'), badge), False, 
                                      URL('admin', 'show_users'), []),
                                  (T('View Email Log'), False, 
                                      URL('admin', 'email_log'), []),
                                  (T('Database (requires site password)'), False, 
                                      URL(request.application, 'appadmin', 'index'), [])
                                  ]))

