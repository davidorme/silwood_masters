
# The wiki functions are exposed in the marking_reports controller, which 
# should be set as the default in routes.py. This keeps the wiki link 
# short (since you can't easily set routes to have a default function 
# for a standalone wiki controller). But it does mean I've done this to
# hide the marking reports menu when browsing or managing the wiki

if request.function in ['wiki', 'manage_wikicontent', 'manage_wikimedia']:
    
    if auth.has_membership('wiki_editor'):
        wikimenu = [
            (T('Wiki content'), False, None, [
                (T('Pages'), False, URL('marking_reports','manage_wikicontent'), []),
                (T('Media'), False, URL('marking_reports','manage_wikimedia'), []),
                (T('Editing the wiki'), False, URL('marking_reports','wiki', 
                 args=['editing-this-wiki']), []),
            ])
            ]
        
        response.menu.extend(wikimenu)

else:
    
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


