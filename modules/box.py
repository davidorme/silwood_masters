#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''
Box interface module. 

Used to generate the cached client and to provide functions to scan the
Box root folder for files and update the database
'''

import json
import os
import datetime
import re
from boxsdk import JWTAuth, Client
from boxsdk.exception import BoxAPIException
# current exposes the database abstraction layer as current.db
from gluon import current


def authorize_jwt_client_json():
    """
    Function to obtain an authorised Box API Client using JWT
    """
    
    config = os.path.join(current.request.folder, 'private',
                          current.configuration.get('box.app_config'))
    
    jwt_auth = JWTAuth.from_settings_file(config)
    jwt_auth.authenticate_instance()

    return Client(jwt_auth)


def downscope_to_root_download():
    """
    Function to provide a downscoped access token from the server JWT client
    that can be provided to users.
    :param client: A JWT Client instance
    :return: A Box SDK TokenResponse object
    """
    
    client = current.box_client
    dl_token = client.downscope_token(scopes=['item_download'], item=client.folder(0))

    return dl_token


def scan_box():
    
    """
    Searches through the folder structure files for all the files and updates
    """
    
    client = current.box_client
    db = current.db

    # Call the search endpoint limiting to files within the current folder.
    # Note that the path collection is always relative to the root folder
    # (client.folder('0')) regardless of any ancestors provided.
    search_folder = current.configuration.get('box.search_folder')
    file_search = client.search().query(query='*.pdf',
                                        ancestor_folders=[client.folder(search_folder).get()],
                                        file_extensions=['pdf'],
                                        # created_at_range=(scan_from_str, None),
                                        type='file',
                                        fields=['name', 'id', 'path_collection', 
                                                'size', 'modified_at'],
                                        limit=200)
    
    # REGEX to extract CID from end of file name _########.pdf
    cid_regex = re.compile("(?<=_)[0-9]+(?=.pdf$)")
    
    # Now iterate over the file search generator
    file_data = []
    
    for this_file in file_search:
        
        # The files are expected to be structured by Search Folder > Year > Presentation, but 
        # because the path is always relative to the account root, need to trim down to the 
        # final 3 directories of the path name
        
        path = [entry.name for entry in this_file.path_collection['entries']]
        path = path[-3:]
        
        # Get the student CID
        cid = cid_regex.search(this_file.name)
        if cid is not None:
            cid = int(cid.group())
        
        file_data.append(dict(box_id = this_file.id,
                              filename = this_file.name,
                              filesize = this_file.size,
                              cid = cid,
                              presentation = path[0],
                              academic_year = path[1],
                              marker_role = path[2]))
    
    # Now do checking on the results:
    report = f'Found {len(file_data)} files\n'
    
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
    for this_file in file_data:
        
        this_file['presentation_id'] = presentation_lookup.get(this_file['presentation'])
        this_file['marker_role_id'] = role_lookup.get(this_file['marker_role'])
        this_file['student'] = student_lookup.get(this_file['cid'])
        
        this_path = "{presentation}/{academic_year}/{marker_role}/{filename}".format(**this_file)
        
        if this_file['presentation_id'] is None:
            report += f"Unknown presentation: {this_path}\n" 

        if this_file['marker_role_id'] is None:
            report += f"Unknown marker role: {this_path}\n" 

        if this_file['student'] is None:
            report += f"Unknown CID: {this_path}\n" 

        # Update or insert on what is found. The box id should be persistent, so moving files
        # around should just update the records rather than creating new ones.
        db.marking_files_box.update_or_insert(db.marking_files_box.box_id == this_file['box_id'],
                                              **this_file)
    
    db.commit()

    return dict(report=report)


def download_url(box_id):
    """
    Simple helper to pair the static download page with the current download access token value

    :param box_id:
    :return:
    """

    url = 'https://dl.boxcloud.com/api/2.0/files/{}/content?access_token={}'.format(box_id, current.dl_token.access_token)

    return url