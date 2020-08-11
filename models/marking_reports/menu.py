marking_reports_menu = [
    (T('Project Proposals'), False, URL('marking_reports','project_proposals'), []),
    (T('Reports and Criteria'), False, None, [
        (T('Reports'), False, 'https://drive.google.com/drive/folders/12vkP0t2D8WXr9tsiOxH5DL-jX6khIypY', []),
        (DIV('Marking criteria', _style='padding:4px 24px;color:grey'), False, False, []),
        (T('- Markers'), False, URL('static','marking_criteria/Project_Marking_Criteria.pdf'), []),
        (T('- Supervisors'), False, URL('static','marking_criteria/Supervisor_Marking_Criteria.pdf'), [])
        ])
    ]

response.menu.extend(marking_reports_menu)

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
                                  (CAT(T('View Users'), badge), False, 
                                      URL('admin', 'show_users'), []),
                                  (T('View Email Log'), False, 
                                      URL('admin', 'email_log'), []),
                                  (T('Database (requires site password)'), False, 
                                      URL(request.application, 'appadmin', 'index'), [])
                                  ]))

