import secrets
from staff_auth import staff_authorised

## --------------------------------------------------------------------------------
## SECURITY AND STAFF AUTHENTICATION
## - The staff ae _deliberately_ not all signed up in db.auth_user. We want a curated
##   list of staff that do project supervision and marking and we also want to separate
##   staff in marking roles from the same staff with higher privileges for admin 
##   or timetabling.
## - We also want a low-friction passwordless approach for adding markers - not have
##   to rely on people signing up before we can assign project marking etc. 
## - The security system has evolved. Initially there was a single static access token,
##   which is not ideal. It then used a static token with an emailed 2FA code to confirm,
##   but that is clumsy and caused some (not much) friction. It now uses a single access
##   token but which expires - you can only get in for 60 minutes after the request.
## - All of the security relies on the user email being secure, but so does _anything_
##   that doesn't rely on having a second device and we're not in a position to do that.
## --------------------------------------------------------------------------------


@staff_authorised
def home():
    
    return dict(header=H2(f"Welcome {session.magic_auth.first_name} {session.magic_auth.last_name}"))


def checkout():
    
    session.magic_auth = None
    redirect(URL('staff', 'staff_login'))


def staff_login():
    
    """
    A controller to use get_staff_link from the website rather than having to have an email
    with it in
    """
    
    requester_email = request.vars.get('email')
    
    form = SQLFORM.factory(Field('email_address', requires=IS_EMAIL(), 
                                 default=requester_email))
        
    if form.process(onvalidation=staff_login_validate).accepted:
        
        sent = _send_staff_link(form.record)
        
        if sent:
            message = 'An access link has been emailed to this address'
        else:
            message = ('There has been a problem sending this email. Please contact us'
                       'using the email link above.')
        
        form.element('span').components.append(DIV(message,
                                                   _style="padding: 5px; color: darkgreen"))
    
    return dict(form=form)


def staff_login_validate(form):
    """
    Checks whether the token can be created
    """
    
    requester_record = db(db.teaching_staff.email == form.vars.email_address).select().first()
        
    if requester_record is None:
        # Unknowns
        form.errors.email_address = 'Unknown email - no teaching staff registered with this address'
        
    elif not requester_record.can_supervise:
        # Non approved
        form.errors.email_address = 'This account is not currently approved for project supervision.'
    
    else:
        # Also, we throttle requests to only have one live link at a time
        live_links = db((db.magic_links.staff_id == requester_record.id) &
                        (db.magic_links.expires > datetime.datetime.now)).count()

        if live_links > 0:
            form.errors.email_address = ('An unexpired link has already been issued for this email. '
                                         'Please check your email.')
    
    # Attach the row for the post approval action
    form.record = requester_record


def _send_staff_link(requester_row):
    """
    This controller creates magic links for email accounts that exist in the staff table.
    """
    
    
    # Now we are in a position to create and send a new link
    new_uuid = secrets.token_urlsafe(nbytes=32)
    
    home_link = URL('staff', 'authorise', vars={'token': new_uuid}, 
                    scheme=True, host=True)
    myprj_link = URL('staff', 'authorise', vars={'token': new_uuid,
                                                 '_next': 'projects/my_projects'}, 
                     scheme=True, host=True)
    mymrk_link = URL('staff', 'authorise', vars={'token': new_uuid,
                                                 '_next': 'marking/my_marking'}, 
                     scheme=True, host=True)
    
    email_dict = dict(home_link = home_link,
                      myprj_link=myprj_link,
                      mymrk_link=mymrk_link,
                      first_name = requester_row.first_name)

    mailer = Mail()
    success = mailer.sendmail(subject='Silwood Masters access link',
                              to=requester_row.email,
                              email_template='magic_links.html',
                              email_template_dict=email_dict)
    
    if not success:
        return False
    else:
        db.magic_links.insert(staff_id = requester_row.id,
                              token = new_uuid)
        return True


def authorise():
    """
    This access controller validates a staff magic link token against the database and
    then provides links on to project, marking and profile details. It sets the
    authorised staff details in the session as an access control mechanism.
    """
    
    # Look for magic link token
    magic_link = request.vars['token']
    
    if magic_link is None:
        raise HTTP(403, 'notoken')
    
    # Look for the provided token in the magic_links table
    magic_link = db((db.magic_links.token == magic_link) &
                    (db.magic_links.staff_id == db.teaching_staff.id)).select().first()
    
    if magic_link is None:
        raise HTTP(403, 'no link')
    
    # Check for expiry
    if magic_link.magic_links.expires < datetime.datetime.now():
        
        raise HTTP(403, P("This access link has expired. Please ", 
                          A("request a new one", 
                            _src=URL('staff_login', 
                                     vars={'email': magic_link.teaching_staff.email},
                                     scheme=True, host=True))))
    
    # Store the marker details in the session to demonstrate that the link exists 
    # and has not expired. This can then be checked by functions that require authorised
    # access. 
    session.magic_auth = magic_link.teaching_staff
    
    # Does the request say where to go next (projects etc)?
    _next = request.vars.get('_next')
    
    if _next is not None:
        _next = _next.split('/')
        redirect(URL(*_next))
    else:
         redirect(URL('staff', 'home'))
    
