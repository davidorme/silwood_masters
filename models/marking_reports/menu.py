marking_reports_menu = [
    (T('Project Proposals'), False, URL('marking_reports','project_proposals'), []),
    (T('Dissertation Reports'), False, None, [
        (T('2019-20'), False, 'https://drive.google.com/drive/folders/12vkP0t2D8WXr9tsiOxH5DL-jX6khIypY', []),
        ]),
    (T('Marking Criteria'), False, None, [
            (T('Marker'), False, URL('static','marking_criteria/Project_Marking_Criteria.pdf'), []),
            (T('Supervisor'), False, URL('static','marking_criteria/Supervisor_Marking_Criteria.pdf'), [])
        ])
    ]

if auth.is_logged_in():
    marking_reports_menu.append((T('Admin tools'), False, None, [
                                  (T('Create Marking Assignment'), False, 
                                   URL('marking_reports', 'new_assignment'), []),
                                  (T('Load Marking Assignments'), False, 
                                   URL('marking_reports', 'load_assignments'), []),
                                  (T('View Marking Assignments'), False, 
                                   URL('marking_reports', 'assignments'), []),
                                  (T('View Project Markers'), False, 
                                   URL('marking_reports', 'markers'), []),
                                  (T('View Email Log'), False, 
                                   URL('marking_reports', 'email_log'), []),
                                  (T('Database (requires site password)'), False, 
                                   URL(app, 'appadmin', 'index'))
                                  ]))

response.menu.extend(marking_reports_menu)