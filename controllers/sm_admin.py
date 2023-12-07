from mailer import Mail

# ---- Action for login/register/etc (required for auth) -----
def user():
    """
    exposes:
    http://..../[app]/default/user/login
    http://..../[app]/default/user/logout
    http://..../[app]/default/user/register
    http://..../[app]/default/user/profile
    http://..../[app]/default/user/retrieve_password
    http://..../[app]/default/user/change_password
    http://..../[app]/default/user/bulk_register
    use @auth.requires_login()
        @auth.requires_membership('group name')
        @auth.requires_permission('read','table name',record_id)
    to decorate functions that need access control
    also notice there is http://..../[app]/appadmin/manage/auth to allow administrator to manage users
    """
    return dict(form=auth())

# ---- action to server uploaded static content (required) ---
@cache.action()
def download():
    """
    allows downloading of uploaded files
    http://..../[app]/default/download/[filename]
    """
    return response.download(request, db)
    

## --------------------------------------------------------------------------------
## EMAIL LOG
## --------------------------------------------------------------------------------

@auth.requires_membership('admin')
def show_users():
    
    # Users and group membership
    icons = {False: SPAN(_class='fa fa-times-circle',
                        _style='color:gray;font-size: 1.3em;',
                        _title='Not granted'),
             True: SPAN(_class='fa fa-check-circle', 
                         _style='color:green;font-size: 1.3em;',
                         _title='Granted')}
    
    def _user_roles(row):
        
        db.auth_group._format = '%(role)s'
        roles = db(db.auth_membership.user_id == row.id).select(db.auth_membership.group_id)
        roles = [r['group_id'] for r in roles.render()]
        
        return ", ".join(roles)
    
    links = [dict(header = 'New', 
                  body = lambda row: icons[row.registration_key == 'pending']),
             dict(header = 'Roles', 
                  body = lambda row: _user_roles(row)),
             dict(header = 'Info', 
                  body = lambda row: A(SPAN(_class='fa fa-info-circle', 
                                            _style='color:#007BFF;font-size: 1.3em;',
                                            _title='Info'),
                                       _href=URL('sm_admin', 'user_details', args=row.id)))]
    
    form = SQLFORM.grid(db.auth_user,
                        csv=False,
                        create=False,
                        editable=False,
                        deletable=False,
                        details=False,
                        links=links,
                        orderby=db.auth_user.registration_key != 'pending')
    
    roles = db(db.auth_group).select(db.auth_group.role, db.auth_group.description).as_list()
    roles = [list(r.values()) for r in roles]
    role_table = TABLE(roles, _class='table table-sm table-striped')
    
    return dict(role_table=role_table, form=form)


@auth.requires_membership('admin')
def user_details():
    
    if not request.args:
        redirect(URL('sm_admin','show_users.html'))
    else:
        record = db.auth_user[int(request.args[0])]
    
    # This duplicates the user editable parts of auth_user 
    fields = [Field('first_name', 'string'),
              Field('last_name', 'string'),
              Field('email', 'string')]
    
    # Add group membership fields
    groups = db(db.auth_group).select()
    
    for grp in groups:
        fields.append([Field(grp.role, 'boolean', default=False)])
        record[grp.role] = auth.has_membership(grp.id, record.id)

    # Add a delete option
    fields.append([Field('delete', 'boolean', default=False)])
    labels = {'delete': 'Check to delete'}
    record.delete = False
    
    # Add an approve new users mechanism
    if record.registration_key == 'pending':
        fields.append([Field('approved', 'boolean', default=False)])
        labels['approved'] = 'Approve new registration'
        record.approved = False
    
    form = SQLFORM.factory(*fields,
                           record=record,
                           labels=labels,
                           showid=False)
    
    if form.process().accepted:
        # Delete first
        if form.vars.delete:
            record.delete_record()
            redirect(URL('sm_admin','show_users'))
        
        # Group memberships
        for grp in groups:
            if record[grp.role] and not form.vars[grp.role]:
                # role removed
                role_record = db((db.auth_membership.user_id == record.id) &
                                 (db.auth_membership.group_id == grp.id)
                                 ).select().first()
                role_record.delete_record()
            elif not record[grp.role] and form.vars[grp.role]:
                # role added
                db.auth_membership.insert(user_id=record.id,
                                          group_id = grp.id)
        
        # Any updates to auth_user
        record.update_record(**form.vars)
        
        # New users
        if 'approved' in form.vars and form.vars.approved:
            record.update_record(registration_key="")
            mailer = Mail()
            success = mailer.sendmail(subject='Registration approved',
                                      to=record.email,
                                      text="Your registration on the Masters website has "
                                           "been approved.")
            del mailer
        
        redirect(URL('sm_admin','show_users'))
    
    # Role table
    roles = db(db.auth_group).select(db.auth_group.role, db.auth_group.description).as_list()
    roles = [list(r.values()) for r in roles]
    role_table = TABLE(roles, _class='table table-sm table-striped')
    
    return dict(role_table=role_table,form = form)


@auth.requires_membership('admin')
def email_log():
    
    # Just shows a searchable log of emails sent
    db.email_log.email_template_dict.readable=False
    db.email_log.email_cc.readable=False
    db.email_log.id.readable=False
    
    form = SQLFORM.grid(db.email_log, 
                        csv=False,
                        create=False,
                        editable=False,
                        deletable=False)
    
    return dict(form=form)

