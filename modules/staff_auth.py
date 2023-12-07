import datetime
from gluon import current, HTTP, CAT, A, URL


def staff_authorised(callee):
    
    """
    This decorator performs a simple check to see if this session has provided
    a valid magic_link token to access staff functionality.
    """
    
    def wrapper():
        
        if (current.session.magic_auth is None) and not current.auth.has_membership('admin'):
            raise HTTP(403, CAT("403 Forbidden: Please use the ", 
                                A("staff login", _href=URL('staff', 'staff_login')),
                                " to access this page"))
        else:
            return callee()
    
    return wrapper


def staff_authorised_new(callee):
    
    """
    This decorator validates a staff magic link token against the database and
    sets the authorised staff details in the session as an access control mechanism
    before proceeding to the calling page
    
    This version is neat - it allows a page to be called and authorised directly, _but_
    that happens after some of the response build, so the staff menu still appears with
    just the staff login link. Using the authorise() controller with a _next argument 
    ensures that the page loads properly and the wrapper just enforces access.
    """
    
    def wrapper():
        
        if (current.session.magic_auth is None) and not current.auth.has_membership('admin'):
            
            # Look for magic link token
            magic_link = current.request.vars['token']
            
            if magic_link is None:
                raise HTTP(403, "Not already authorised and no access token provided")
            
            # Look for the provided token in the magic_links table
            db = current.db
            magic_link = db((db.magic_links.token == magic_link) &
                            (db.magic_links.staff_id == db.teaching_staff.id)).select().first()
    
            if magic_link is None:
                raise HTTP(403, "Unknown access token")
    
            # Check for expiry
            if magic_link.magic_links.expires < datetime.datetime.now():
        
                raise HTTP(403, P("This access link has expired. Please ", 
                                  A("request a new one", 
                                    _src=URL('staff' 'staff_login', 
                                             vars={'email': magic_link.teaching_staff.email},
                                             scheme=True, host=True))))
    
            # Store the marker details in the session to demonstrate that the link exists 
            # and has not expired. This can then be checked by functions that require authorised
            # access. 
            current.session.magic_auth = magic_link.teaching_staff
        
        # Now we are here, all errors have been redirected to 403    
        return callee()
    
    return wrapper
