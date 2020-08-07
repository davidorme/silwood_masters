marking_reports_menu = [
    (T('Project Proposals'), False, URL('marking_reports','project_proposals'), []),
    (T('Reports and Criteria'), False, None, [
        (T('Reports'), False, 'https://drive.google.com/drive/folders/12vkP0t2D8WXr9tsiOxH5DL-jX6khIypY', []),
        (T('Marking Criteria'), False, 'javascript:;', []),
        (T('- Markers'), False, URL('static','marking_criteria/Project_Marking_Criteria.pdf'), []),
        (T('- Supervisors'), False, URL('static','marking_criteria/Supervisor_Marking_Criteria.pdf'), [])
        ])
    ]

response.menu.extend(marking_reports_menu)

if auth.has_membership('admin'):
    response.menu.append((T('Admin tools'), False, None, [
                                  (T('Create Marking Assignment'), False, 
                                      URL('marking_reports', 'new_assignment'), []),
                                  (T('Load Marking Assignments'), False, 
                                      URL('marking_reports', 'load_assignments'), []),
                                  (T('View Marking Assignments'), False, 
                                      URL('marking_reports', 'assignments'), []),
                                  (T('View Project Markers'), False, 
                                      URL('marking_reports', 'markers'), []),
                                  (T('User requests'), False, 
                                      URL('default', 'user_requests'), []),
                                  (T('View Email Log'), False, 
                                      URL('marking_reports', 'email_log'), []),
                                  (T('Database (requires site password)'), False, 
                                      URL(request.application, 'appadmin', 'index'), [])
                                  ]))

