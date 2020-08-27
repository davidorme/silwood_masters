# Generate the marking criteria lists from the role dictionary 
criteria = [(T('- ' + role), False, URL('static','marking_criteria/' + details['criteria']), [])
            for role, details in role_dict.items()]

marking_reports_menu = [
    (T('Project Proposals'), False, URL('marking_reports','project_proposals'), []),
    (T('Reports and Criteria'), False, None, [
        (T('Reports'), False, configuration.get('report_drive.link'), []),
        (DIV('Marking criteria', _style='padding:4px 24px;color:grey'), False, False, []),
        *criteria
        ]),
    (T('Help'), False, None, [
        (T('Overview'), False,  URL('marking_reports', 'help'), [])])
    ]

response.menu.extend(marking_reports_menu)


