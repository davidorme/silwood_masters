import openpyxl
import csv
import simplejson
import datetime
import argparse

"""
Compiles project data from the Project Data Excel sheet into 
the upload format for the marking system


"""

def projects_to_assignments(datafile, outfile, due_date, 
                            years = None, presentations=None, role_map=None):
    
    """Project Data to assignment tool
    
    This script provides a tool to export data from the Project Data Excel workbook
    into the upload format used for the marking system. The tool takes the path to that
    workbook as an input and saves assignments to a named output file.
    
    The tool provides options to subset the data down to particular years and course
    presentations. It also provides a way to customise the mapping from project roles
    (e.g. Supervisor or Marker) to assignment roles: a supervisor might just have to 
    complete a supervisor report, but a marker might have to mark a thesis and a
    presentation and complete a viva. This data is provided as a JSON string mapping
    columns in the Excel sheet to an array of assignment roles. For example, to only
    generate thesis marking assignments:
    
    > role_map='{"marker_1": ["Marker"], "marker_2": ["Marker"]}'
    
    """
    
    try:
        due_date_formatted = datetime.date.fromisoformat(due_date)
    except ValueError:
        raise RuntimeError(f'due_date ({due_date}) not an ISO formatted date (2020-01-01)')
    
    wb = openpyxl.load_workbook(datafile, data_only=True)
    
    # Load staff details using values, which iterates over rows and build
    # a dictionary keyed on display name to match to staff in the project data 

    staff_sheet = wb['Staff']
    staff_values = staff_sheet.values
    staff_colnames = next(staff_values)
    staff_dict = {}

    for this_staff in staff_values:
    
        this_staff = dict(zip(staff_colnames, this_staff))
        staff_dict[this_staff['display']] = this_staff

    # Load project using values again into a dictionary

    project_sheet = wb['Projects']

    project_values = project_sheet.values
    project_colnames = next(project_values)
    projects = []

    for this_project in project_values:

        this_project = dict(zip(project_colnames, this_project))
    
        if ((years is None or this_project['academic_year'] in years) and 
            (presentations is None or this_project['course_presentation'] in presentations)):
        
            projects.append(this_project)

    # Compile a set of assignments
    if role_map is None:
        role_map = '''{"supervisor_1": ["Supervisor"],
                       "supervisor_2": ["Supervisor"],
                       "supervisor_3": ["Supervisor"],
                       "marker_1": ["Marker", "Presentation", "Viva"],
                       "marker_2": ["Marker", "Presentation"]}'''
    
    role_map = simplejson.loads(role_map)
    
    assignments = []

    for this_proj in projects:
    
        for this_role, these_assignments in role_map.items():
        
            role_staff = this_proj[this_role]
        
            if role_staff is None or role_staff == '':
                continue
        
            role_staff = staff_dict[role_staff]
        
            for this_assign in these_assignments:
            
                assignments.append(
                    {'student_cid': this_proj['student_cid'],
                     'course': this_proj['course'],
                     'course_presentation': this_proj['course_presentation'],
                     'academic_year': this_proj['academic_year'],
                     'student_first_name': this_proj['student_first_name'], 
                     'student_last_name': this_proj['student_last_name'], 
                     'student_email': this_proj['student_email'],
                     'marker_first_name': role_staff['first_name'], 
                     'marker_last_name': role_staff['last_name'], 
                     'marker_email': role_staff['email'], 
                     'marker_role': this_assign, 
                     'due_date': due_date,
                     'project_role': this_role})

    output_columns = ['student_cid', 'course', 'course_presentation', 'academic_year',
                      'student_first_name', 'student_last_name', 'student_email',
                      'marker_first_name', 'marker_last_name', 'marker_email', 'marker_role', 
                      'due_date', 'project_role']


    with open(outfile, 'w', newline='') as csvfile:
    
        output = csv.DictWriter(csvfile, output_columns)
        output.writeheader()
    
        for each_assignment in assignments:
            output.writerow(each_assignment)


if __name__ == '__main__':
    
    # initiate the parser
    parser = argparse.ArgumentParser(description = projects_to_assignments.__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    
    parser.add_argument('datafile', help = 'Path to Excel Projects Data file')
    
    
    parser.add_argument('--outfile', '-o',
                        type = str, 
                        help = 'Output file for assignments')
    
    parser.add_argument('--due_date', '-d',
                        type = str, 
                        help = 'Due date for extracted assignments')

    parser.add_argument('--years', '-y', nargs = '+', 
                        type = int, 
                        help = 'Year(s) to extract')
    
    parser.add_argument('--presentations', '-p', nargs = '+', 
                        type = str, 
                        help = 'Course presentation(s) to extract')

    parser.add_argument('--role_map', '-r',
                        type = str, 
                        help = 'JSON data defining the roles for each marker')

    args = parser.parse_args()
    
    projects_to_assignments(datafile=args.datafile, outfile=args.outfile, due_date=args.due_date,
                            years=args.years, presentations=args.presentations,
                            role_map=args.role_map)