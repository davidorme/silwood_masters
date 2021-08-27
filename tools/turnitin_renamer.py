import os
import sys
import shutil
import re
import zipfile
import argparse
import pandas

def turnitin_renamer(file_dir, cid_table, course_presentation, zipto=None):
    
    """Renames TurnItIn downloads to the standard convention.
    
    Files submitted through TurnItIn download with mangled file names, and may
    have been badly names to begin with ('project.pdf' etc.). This tool uses the
    Excel file that can be downloaded from TurnItIn to map student details to TurnItIn ID
    to rename submitted files to the project marking convention of:
    
    Surname_with_spaces_as_underscores_Course_CID.pdf
    
    However, the TurnItIn xls file only reports user login, _not_ CID, so a separate table
    of student login and CID is needed to merge this back in. This can be obtained from
    the DSS: 
        https://www.imperial.ac.uk/dss
    
    Currently this code assumes the row headers and encoding (Latin-1) of data downloaded
    from the DSS system. Be wary of students with different starting years - delayed or
    
    The code then optionally compresses the original files to get them out of the way.
    
    Args:
        file_dir: The directory to search for PDFs and accompanying Excel file
        cid_table: The path to the DSS file of login and CID details
        course_presentation: A string giving the course presentation (e.g. CMEE_MSc)
        zipto: A filename to use for the zip file within filedir, or None to leave
           the original files in filedir as well as the renamed files.
    """
    
    file_list = os.listdir(file_dir)
    file_ext = [os.path.splitext(f) for f in file_list]

    # Get excel file and pdf files
    excel_file = [f for f, ext in zip(file_list, file_ext) if ext[1] in [".xls", ".xlsx"]]
    pdf_files = [f for f, ext in zip(file_list, file_ext) if ext[1] == '.pdf']

    if len(excel_file) != 1:
        raise RuntimeError('Multiple excel files found')
    
    # Assuming a single sheet with headers in first row. Why this isn't
    # written by TII as CSV, I do not know...
    data = pandas.read_excel(os.path.join(file_dir, excel_file[0]), header=1)
    
    # Match TII paper IDs at start of pdf files names to rows
    paper_id_re = re.compile('^[0-9]+')
    pdf_paper_ids = [paper_id_re.match(f).group() for f in pdf_files]
    
    # Check matches found
    if any([pid is None for pid in pdf_paper_ids]):
        raise RuntimeError('PDF files with no initial paper ID found')
    
    pdf_paper_ids = [int(pid) for pid in pdf_paper_ids]
    
    if set(pdf_paper_ids) != set(data['Paper ID']):
        raise RuntimeError('PIDs do not match between files and Excel data')
    
    # Map files to rows
    file_df = pandas.DataFrame({'Paper ID': pdf_paper_ids, 'filename': pdf_files})
    data = data.merge(file_df, on='Paper ID')
    
    # Map logins to CIDs
    with open(cid_table, encoding='latin_1') as cid_map:
        cid_data = pandas.read_csv(cid_map)
    
    data = data.merge(cid_data, left_on='User ID', right_on='Login ID', how='left')
    
    if any(data['CID'].isna()):
        raise RuntimeError('CIDs not found for all logins')
    
    # Now all should be set to rename the files
    data['new_file_name'] = [f"{rw['Last Name'].replace(' ', '_').title()}_"
                             f"{course_presentation}_{rw['CID']}.pdf"
                             for idx, rw in data.iterrows()]
    
    for idx, row in  data.iterrows():
        
        sys.stdout.write(f"Moving {row['filename']} to {row['new_file_name']}\n")
        shutil.copy(os.path.join(file_dir, row['filename']), 
                    os.path.join(file_dir, row['new_file_name']))
    
    if zipto is not None:
        # TIDY up old files into a zip.
        zipf = zipfile.ZipFile(os.path.join(file_dir, zipto), 'w', zipfile.ZIP_DEFLATED)
    
        for oldf in file_list:
            zipf.write(os.path.join(file_dir, oldf))
        zipf.close()
    
        for oldf in file_list:
            os.remove(os.path.join(file_dir, oldf))



if __name__ == '__main__':
    
    # initiate the parser
    parser = argparse.ArgumentParser(description = turnitin_renamer.__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument('file_dir', help = 'The directory to search for PDFs and accompanying Excel file')
    
    parser.add_argument('cid_table', 
                        type = str, 
                        help = 'The path to the DSS file of login and CID details')
    
    parser.add_argument('course_presentation', 
                        type = str, 
                        help = 'A string giving the course presentation (e.g. CMEE_MSc)')

    parser.add_argument('--zipto', default=None,
                        type = str, 
                        help = 'Optionally, a zip filename to archive the original files')
    
    args = parser.parse_args()
    
    turnitin_renamer(file_dir=args.file_dir, 
                     cid_table=args.cid_table, 
                     course_presentation=args.course_presentation,
                     zipto=args.zipto)