import re
from office365.runtime.auth.user_credential import UserCredential
from office365.sharepoint.client_context import ClientContext
from gluon import current, BR, P, LI, UL, CAT

def get_sharepoint_folder_contents(ctx, dir):
    """
    Function to provide a dictionary of folders and files within a 
    sharepoint folder. 
    """
    
    
    # Get the sub-directories
    subdirs = dir.folders
    ctx.load(subdirs)
    ctx.execute_query()
    
    # Get the files
    files = dir.files
    ctx.load(files)
    ctx.execute_query()
    
    return dict(folders = [(sub.properties['ServerRelativeUrl'], sub) for sub in subdirs],
                files = [(f.properties['Name'], f) for f in files])


def scan_files():
    """Recursively scan files
    
    This function takes a configured document root directory on a sharepoint site 
    and scans it recursively for a complete listing of files. The retrieved properties
    include the relative URL, which can be used to link directly to the file. The download
    url, using the config settings and a Row `f` are:
    
        url =  f"{tenant_name}/:t:/r/{f.relative_url}" 
    
    Files can only be accessed via these URLs after a user has logged in to Sharepoint using
    college credentials and also has access rights to the file, so needs a Sharepoint folder
    with managed access for markers. That is relatively simple to do. There is also an API
    to provide shared links to anyone in the organisation. Users would still need to log in
    but the access management _within the organisation_ can be omitted. The API is needlessly
    obscure though, so not implemented, but the URLs look like.
    
        url = f"{tenant_name}/:t:/s/{site}/{cryptic_share_code}
    """
    
    
    # Get access to the db object
    db = current.db
    
    # Get the configured sharepoint tenant, site and relative url
    # and credentials for a college role user that has been given access 
    # to that relative URL.

    conf = current.configuration

    tenant_name = conf.get('sharepoint.tenant_name')
    site = conf.get('sharepoint.site')
    root_dir_relative_url = conf.get('sharepoint.root_dir_relative_url')
    
    user_credentials = UserCredential(conf.get('email.imap_user'), 
                                      conf.get('email.password'))
    
    # Connect to sharepoint
    ctx = ClientContext(f"{tenant_name}/sites/{site}").with_credentials(user_credentials)
    
    # Get the root directory
    root = ctx.web.get_folder_by_server_relative_url(root_dir_relative_url)
    
    # Scan the directory for files, until this list is emptied.
    dir_filo = [('root', root)]
    
    # Now iterate over the directory contents collecting dictionaries of file data
    file_data = []
    
    # REGEX to extract CID from end of file name _########.pdf
    cid_regex = re.compile("(?<=_)[0-9]+(?=.pdf$)")
        
    while dir_filo:
        
        # Get the first entry from the FILO for directories and scan it
        this_dir = dir_filo.pop(0)
        contents = get_sharepoint_folder_contents(ctx, this_dir[1])
        
        # Contents is a dictionary of folders and files, so add the folders
        # onto the front of the directory FILO (depth first search)
        dir_filo = contents['folders'] + dir_filo
        
        # If there are any files, they are 2-tuples of (name, office365.sharepoint.files.file.File)
        # which can be used to retrieve key information
        for each_file in contents['files']:
            
            file_props = each_file[1].properties
            
            # Can't see how to filter to only PDFs using the sharepoint API, so 
            # do it here.
            if not file_props['Name'].endswith('.pdf'):
                continue
            
            # Get the student CID
            cid = cid_regex.search(file_props['Name'])
            if cid is not None:
                cid = int(cid.group())
            
            # The files are expected to be structured within root_dir_relative_url as:
            #   Presentation/Year/Role/File.pdf
            # because the file url is always relative to the account root, need to trim down to the 
            # final 3 directories of the path name
            
            path = file_props['ServerRelativeUrl'].split('/')
            
            file_data.append(dict(unique_id = file_props['UniqueId'],
                                  filename = file_props['Name'],
                                  filesize = file_props['Length'],
                                  cid = cid,
                                  presentation = path[-4],
                                  academic_year = path[-3],
                                  marker_role = path[-2],
                                  relative_url = file_props['ServerRelativeUrl']))
    
    # Now do checking on the results:
    # Load presentations, marker roles and student ids, substituting underscores for spaces
    presentations = db(db.presentations).select(db.presentations.name, 
                                                db.presentations.id).as_list()
    presentation_lookup = {dt['name'].replace(' ', '_'): dt['id'] 
                           for dt in presentations}

    roles = db(db.marking_roles).select(db.marking_roles.name, 
                                        db.marking_roles.id).as_list()
    role_lookup = {dt['name'].replace(' ', '_'): dt['id'] for dt in roles}
    
    students = db(db.students).select(db.students.id, db.students.student_cid).as_list()
    student_lookup = {dt['student_cid']: dt['id'] for dt in students}

    # Insert what is available
    problems = []
    
    for this_file in file_data:
        
        this_path = "{presentation}/{academic_year}/{marker_role}/{filename}".format(**this_file)
        
        # Lookup ID numbers of presentation, role and student in 
        this_file['course_presentation_id'] = presentation_lookup.get(this_file['presentation'])
        this_file['marker_role_id'] = role_lookup.get(this_file['marker_role'])
        this_file['student_cid'] = student_lookup.get(this_file['cid'])
        
        # Try and get the year as an integer
        try:
            this_file['academic_year'] = int(this_file['academic_year'])
        except ValueError:
            this_file['academic_year'] = None
        
        # Report errors
        these_problems = []
               
        if (this_file['course_presentation_id'] is None):
            these_problems.append("Unknown presentation")

        if this_file['academic_year'] is None:
            these_problems.append("Unknown year")
            
        if this_file['marker_role_id'] is None:
            these_problems.append("Unknown marker role")

        if this_file['student_cid'] is None:
            these_problems.append("Unknown CID")
        
        if these_problems:
            problems.append(LI(f"{this_path}", BR(), ','.join(these_problems)))
        

        # Update or insert on what is found. The box id should be persistent, so moving files
        # around should just update the records rather than creating new ones.
        db.marking_files.update_or_insert(db.marking_files.unique_id == this_file['unique_id'],
                                          **this_file)
    
    # Reporting
    report = P(f'Found {len(file_data)} files')
    
    if problems:
        report += CAT(P(f'Issues found with {len(problems)} files: '), UL(*problems))
    
    db.commit()

    return dict(report=report)


def download_url(record):
    """
    Simple helper to get the sharepoint address, which will require user login.

    :param records:
    :return:
    """
    
    conf = current.configuration
    tenant_name = conf.get('sharepoint.tenant_name')
    url = f"{tenant_name}/:t:/r/{record.relative_url}" 

    return url
