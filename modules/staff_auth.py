from gluon import current, HTTP

def staff_authorised(callee):
    """
    This decorator performs a simple check to see if this session has provided
    a valid magic_link token to access staff functionality.
    """
    
    def wrapper():
        
        
        if (current.session.magic_auth is None) and not current.auth.has_membership('admin'):
            raise HTTP(403, "403 Forbidden: Please look in your email for your "
                            "personal access link to staff marking and project details")
        else:
            return callee()
    
    return wrapper
