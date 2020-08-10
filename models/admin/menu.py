
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
                                  (CAT(T('View Users'), badge), False, 
                                      URL('admin', 'show_users'), []),
                                  (T('View Email Log'), False, 
                                      URL('admin', 'email_log'), []),
                                  (T('Database (requires site password)'), False, 
                                      URL(request.application, 'appadmin', 'index'), [])
                                  ]))

