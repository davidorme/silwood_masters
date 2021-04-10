
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
    
    # Generate the menu
    marking_reports_menu = [
        (T('Project Proposals'), False, URL('marking_reports','project_proposals'), []),
        (T('Criteria and Forms'), False, URL('marking_reports','criteria_and_forms'), []),
        (T('Help'), False, None, [
            (T('Overview'), False,  URL('marking_reports', 'help'), []), 
            (T('Video tutorial'), False, URL('static', 'video/marking_howto.mp4'), [])
        ])]
    
    # If a user has two factor authenticated their marking assignment,
    # provide a menu link
    if session.tf_validated:
        my_assign = (T('My Assignments'), False, 
                      URL('marking_reports','my_assignments', 
                          vars=dict(marker=session.marker,
                                    marker_access_token=session.marker_access_token)), [])
        marking_reports_menu.append(my_assign)
    
    response.menu.extend(marking_reports_menu)


