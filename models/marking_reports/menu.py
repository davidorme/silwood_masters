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


