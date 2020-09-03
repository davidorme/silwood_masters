import datetime
import os
import sys
import csv
import itertools
import zipfile
import io
import re
import openpyxl
import simplejson as json
from collections import Counter
import fpdf
import importlib
from tempfile import NamedTemporaryFile
from mailer import Mail

from gluon import current, SQLFORM, DIV, LABEL, CAT, B, P, A, URL, HTTP, BR, TABLE

"""
This module contains key functions for processing marking reports. They have been 
separated out into a module to reduce the amount of code in the controller, which
should speed up response times.
"""


## --------------------------------------------------------------------------------
## GLOBAL FUNCTIONS
## --------------------------------------------------------------------------------

def div_radio_widget(field, value, **attributes):
    # provides a horizontal radio button rubric
    table=SQLFORM.widgets.radio.widget(field, value, **attributes)
    
    return DIV(*[DIV(DIV(LABEL(td.components[1], _style='display:block;'),
                         td.element('input'), ),
                         _class='col-sm-2', _style='display:inline-block;text-align:center;')
                 for td in table.elements('td') 
                     if '_disabled' not in list(td.element('input').attributes.keys())],
               _class='row')

def div_checkbox_widget(field, value, **attributes):
    # provides a horizontal checkbox rubric for three fields
    # - needs to catch hidden field at end
    table = SQLFORM.widgets.checkboxes.widget(field, value, **attributes)

    return DIV(*[DIV(DIV(td.element('input'), '  ',
                         td.element('label')),
                         _class='col-sm-3', _style='display:inline-block;')
                 for td in table.elements('td') 
                     if '_disabled' not in list(td.element('input').attributes.keys())],
               _class='row')

def div_checkbox_widget_wide(field, value, **attributes):
    # provides a horizontal checkbox rubric for three fields
    # - needs to catch hidden field at end
    table = SQLFORM.widgets.checkboxes.widget(field, value, **attributes)

    return DIV(*[DIV(DIV(td.element('input'), '  ',
                         td.element('label')),
                         _class='col-sm-6', _style='display:inline-block;')
                 for td in table.elements('td') 
                     if '_disabled' not in list(td.element('input').attributes.keys())],
               _class='row')

## --------------------------------------------------------------------------------
## LOCAL FUNCTIONS USED BY THE ASSIGNMENT PAGE TO TAKE ACTIONS ON SETS OF RECORD IDS
## --------------------------------------------------------------------------------

def release(ids):
    
    """
    Local function to email reports to students. It will only email released reports.
    """
    
    db = current.db
    
    # Get only submitted
    n=0
    email = []
    for id in ids:
        record = db.assignments(id)
        if record.status in ['Submitted', 'Released']:
            record.update_record(status='Released')
            email.append(record)
            n += 1
    
    # now group by student
    email.sort(key=lambda rec: rec['student_email'])
    student_blocks = {k:list(recs) 
                      for k, recs 
                      in itertools.groupby(email, lambda x: x['student_email'])}

    # Create a mailer instance to send multiple emails using the same connection
    fails = 0
    mailer = Mail()
    mailer.login()
    
    for student, recs in student_blocks.items():
        
        # Create a set of links to the reports
        links = [CAT(P(B('Marking Role: '), 
                       r.marker_role,
                       B('; Marker: '), 
                       A(r.marker.first_name, ' ', r.marker.last_name, 
                         _href=URL('download_pdf', scheme=True, host=True,
                                   vars={'record':r.id, 
                                         'public_access_token': r.public_access_token}))))
                for r in recs]
        
        success = mailer.sendmail(subject='Your Project Marking Reports', 
                                  to=student, email_template='student_release.html',
                                  email_template_dict={'name':recs[0].student_first_name + ' ' + recs[0].student_last_name,
                                                 'links':CAT(links).xml()})
        
        if not success:
            fails += 1
    
    mailer.logout()
    del mailer
    
    # give some feedback
    msg = 'Emailed {} released records from {} selected rows to {} students'.format(
            n, len(ids), len(student_blocks)-fails)
    if fails > 0:
        msg = msg + "Warning: FAILED to send {} emails. Review email log.".format(fails)
    
    current.session.flash = msg


def distribute(ids):
    
    """
    This local function emails a set of records out to the relevant markers
    Note that this can be repeated to send reminders but won't email submitted
    or released reports, to avoid hassling markers!
    """
    
    db = current.db
    
    # first, subset down to records to email
    n = 0
    email = []
    for id in ids:
        record = db.assignments(id)
        
        if record.status == 'Created':
            record.update_record(status='Not started')
            email.append(record)
            n += 1
        elif record.status in ['Not started', 'Started']:
            email.append(record)
            n += 1
        else:
            # don't pester people who have completed records
            pass
    
    # now group by marker
    email.sort(key=lambda rec: rec['marker.email'])
    marker_blocks = {k:list(recs) for k, recs in itertools.groupby(email, lambda x: x['marker.email'])}
    
    # Create a mailer instance to send multiple emails using the same connection
    fails = 0
    mailer = Mail()
    mailer.login()

    for marker, recs in marker_blocks.items():
        
        # now create a set of links to individual student reports:
        recs = sorted(recs, key=lambda x: (x.course_presentation, x.marker_role))
        links = [CAT(P(B('Course: '), r.course_presentation,
                       B('; Marking Role: '), r.marker_role,
                       B('; Student: '), r.student_first_name, ' ', r.student_last_name,
                       B('; Due Date: '), r.due_date,
                       BR(),
                       A('Go to marking report for ', r.student_first_name, ' ', r.student_last_name, 
                         _href=URL('write_report', scheme=True, host=True,
                         vars={'record':r.id, 'staff_access_token': r.staff_access_token}))))
                 for r in recs]
        
        # Create a link to the marker my assignments page.
        my_assignments_url = A('View my assignments',
                               _href = URL('my_assignments', scheme=True, host=True,
                                           vars={'marker': recs[0].marker.id, 
                                                 'marker_access_token': recs[0].marker.marker_access_token}))
        
        success = mailer.sendmail(subject='Silwood Park Masters Project Marking', 
                                  to=marker, email_template='marker_distribute.html',
                                  email_template_dict={'name':recs[0].marker.first_name,
                                                       'links':CAT(links).xml(),
                                                       'my_assignments_url': my_assignments_url.xml()})
        
        if not success:
            fails += 1
    
    mailer.logout()
    del mailer
    
    # give some feedback
    msg = 'Emailed {} records from {} selected rows'.format(n -fails, len(ids))
    if fails > 0:
        msg = msg + "Warning: FAILED to send {} emails. Review email log.".format(fails)
    
    current.session.flash = msg


def zip_pdfs(ids, confidential=False):
    
    """
    Local function to create a zipfile of pdfs for selected records and
    return it to the user
    """
    
    db = current.db
    
    # create a zipfile of the selected pdfs and return it
    contents = io.BytesIO()
    zf = zipfile.ZipFile(contents, mode='w', compression=zipfile.ZIP_DEFLATED)
    
    # loop over the ids, creating the correct PDF and adding it.
    for id in ids:
        
        record = db.assignments(id)
        
        # can't create a PDF of incomplete assignments
        if record.status in ['Submitted','Released']:
            
            # - load the correct form definition 
            style_dict = current.globalenv['form_data_dict'][(record.course_presentation, record.marker_role)] 
            form_json = style_dict['form']
            f = open(os.path.join(current.request.folder,'static','form_json', form_json))
            form_json = json.load(f)
            
            # create the form - this is a separate function so that the file creation 
            # can be used by other functions (like downloading a zipfile of selected pdf)
            pdf, filename = create_pdf(record, form_json, confidential=confidential)
            
            zf.writestr(filename, pdf)
    
    # finalise and return the zip file
    zf.close()
    
    current.response.headers['Content-Type'] = 'application/pdf'
    attachment = 'attachment;filename=MarkingRecords.zip'
    current.response.headers['Content-Disposition'] = attachment
    
    raise HTTP(200, contents.getvalue(),
               **{'Content-Type':'application/pdf',
                  'Content-Disposition':attachment + ';'})


def download_grades(ids):
    
    """
    This local function takes a set of rows from the assignments grid
    and returns a collated excel file, one row per student, with the 
    names and grades in separate columns. 
    """
    db = current.db
    wb = openpyxl.Workbook()
    
    # spreadsheet styles
    left = openpyxl.styles.Alignment(horizontal='left')
    center = openpyxl.styles.Alignment(horizontal='center')
    weekend = openpyxl.styles.PatternFill(fill_type='solid', start_color='CCCCCC')
    head = openpyxl.styles.Font(size=14, bold=True)
    subhead = openpyxl.styles.Font(bold=True)
    warn = openpyxl.styles.Font(bold=True, color='FF0000')
    cell_shade = {'Approved': openpyxl.styles.PatternFill(fill_type='solid', start_color='8CFF88'),
                  'Submitted': openpyxl.styles.PatternFill(fill_type='solid', start_color='FFCB8B'),
                  'Draft': openpyxl.styles.PatternFill(fill_type='solid', start_color='DDDDDD'),
                  'Rejected': openpyxl.styles.PatternFill(fill_type='solid', start_color='FF96C3')}

    # name the worksheet and add a heading
    ws = wb.active
    ws.title = 'Grades'
    ws['A1'] = 'Masters grades: downloaded {}'.format(datetime.datetime.today().isoformat())
    ws['A1'].font = head
    
    # load reports and then group reports by student and role
    records = db(db.assignments.id.belongs(ids)).select()
    records = list(records.render()) # to render marker id to name
    records.sort(key = lambda rw: (rw['student_cid'], rw['marker_role']))
    records = {key: list(group) for key, group 
                in itertools.groupby(records, lambda rw: (rw['student_cid'], rw['marker_role']))}
    
    # Find the unique student details, ordered by presentation and surname
    students = db(db.assignments.id.belongs(ids)).select(
                    db.assignments.student_cid,
                    db.assignments.student_last_name,
                    db.assignments.student_first_name,
                    db.assignments.course_presentation,
                    db.assignments.academic_year,
                    orderby=(db.assignments.course_presentation, 
                             db.assignments.student_last_name),
                    distinct=True)
    
    # Layout the headers and data above and below a fixed row
    data_row = 6
    hdr_row = data_row - 1
    
    ws[f'A{hdr_row}'] = 'CID'
    ws[f'B{hdr_row}'] = 'Last Name'
    ws[f'C{hdr_row}'] = 'First Name'
    ws[f'D{hdr_row}'] = 'Course Presentation'
    ws[f'E{hdr_row}'] = 'Year'
    
    # Convert students to a dictionary keyed by CID, assigning a data row per student
    student_dict = {}
    for row, this_student in enumerate(students):
        this_student['row'] = row + data_row
        student_dict[this_student.student_cid] = this_student
    
    # Fill in student details
    for cid, details in student_dict.items():
        
        ws.cell(row = details.row, column=1, value=details.student_cid)
        ws.cell(row = details.row, column=2, value=details.student_last_name)
        ws.cell(row = details.row, column=3, value=details.student_first_name)
        ws.cell(row = details.row, column=4, value=details.course_presentation)
        ws.cell(row = details.row, column=5, value=details.academic_year)
    
    # Now fill in report details for each kind of report in turn
    role_list = current.globalenv['role_list']
    column_pointer = 6
    # A regex to convert '65% (B)' grades to numeric
    grade_regex = re.compile('[0-9]+(?=%)')
    
    for this_role in role_list:
        
        # Get the JSON data on what variables to export
        form_json = current.globalenv['role_dict'][this_role]['form']
        json_path = os.path.join(current.request.folder,'static','form_json', form_json)
        form_json = json.load(open(json_path))
        grade_export = form_json['grade_export']
        cols_per_report = len(grade_export) + 1
        
        # Extract the columns
        filtered_to_role = {key[0]: val for key, val in records.items() if key[1] == this_role}
        
        # Loop over students and reports
        for this_student, these_reports in filtered_to_role.items():
            
            student_details = student_dict[this_student]
            row = student_details.row
            
            for report_num, this_report in enumerate(these_reports):
                
                report_data = this_report.get('assignment_data')
                
                for grade_num, this_grade in enumerate(grade_export):
                    
                    # Do we have any data for this grade - might be nothing at assignment level
                    # or might not be completed in the assignment data
                    val = None if report_data is None else report_data.get(this_grade)
                    val = 'NA' if val is None else val
                    
                    # look for a percentage grade
                    perc_grade = grade_regex.match(val)
                    val = val if perc_grade is None else int(perc_grade.group(0))
                    
                    ws.cell(row = row, 
                            column = column_pointer + cols_per_report * report_num + grade_num,
                            value = val)
                
                # Add marker
                ws.cell(row = row, 
                        column = column_pointer + cols_per_report * report_num + len(grade_export),
                        value = this_report.marker)
        
        # Add role headers
        max_n_reports = max([len(rep) for rep in filtered_to_role.values()])
        for report_number in range(max_n_reports):
            ws.cell(row = data_row - 2, 
                    column= column_pointer + report_number * cols_per_report,
                    value= f"{this_role} {report_number + 1}")
            
            for grade_num, this_grade in enumerate(grade_export):
                ws.cell(row = data_row - 1, 
                        column = column_pointer + cols_per_report * report_number + grade_num,
                        value = this_grade)
            
            ws.cell(row = data_row - 1, 
                    column= column_pointer + report_number * cols_per_report + cols_per_report - 1,
                    value='Marker')
        
        column_pointer += max_n_reports * cols_per_report
    
    current.response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    attachment = 'attachment;filename=Marking_Grades_{}.xlsx'.format(datetime.date.today().isoformat())
    current.response.headers['Content-Disposition'] = attachment
    
    with NamedTemporaryFile() as tmp:
            wb.save(tmp.name)
            tmp.seek(0)
            
            raise HTTP(200, tmp.read(),
                       **{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                          'Content-Disposition':attachment + ';'})

## --------------------------------------------------------------------------------
## PDF generation
## --------------------------------------------------------------------------------

# Subclass of FPDF with a built in confidential page header
class ConfidentialPDF(fpdf.FPDF):
    
    def header(self):
        self.set_y(7)
        self.set_font("Helvetica", size=12)
        self.set_text_color(255, 40, 40)
        self.cell(0, 8, txt = "This is a confidential document and "
                  "must not be circulated to students.", align='C')
        self.set_xy(10,20)


def create_pdf(record, form_json, confidential):
    
    """
    This code writes a simple PDF file of the marking report
    using pyfpdf: very simple, can't do styling or templating easily 
    but no external dependencies and reasonably fast
    """
    
    if confidential:
        pdf = ConfidentialPDF(format='A4')
    else:
        pdf = fpdf.FPDF(format='A4')

    # set up the fonts
    fpdf.set_global('SYSTEM_TTFONTS', current.configuration.get('fpdf.font_dir'))
    pdf.add_font('DejaVu', '', 'DejaVuSansCondensed.ttf', uni=True)
    pdf.add_font('DejaVu', 'B', 'DejaVuSansCondensed-Bold.ttf', uni=True)
    
    #  add first page and insert the logo
    pdf.set_top_margin(20)
    pdf.add_page()
    pdf.image(os.path.join(current.request.folder, 'static','images/imperial_logo_mono.png'), w=60)
    logo_bottom = pdf.get_y()

    # Title block
    pdf.set_xy(80, 20)
    pdf.set_font("DejaVu", style='B', size=14)
    pdf.cell(0, 10, txt="Silwood Park Masters Courses", align="R",  ln=1)
    pdf.cell(0, 10, txt=form_json['pdftitle'], align="R",  ln=1)
    pdf.set_xy(10, logo_bottom + 10)
    pdf.set_font("DejaVu", size=14)
    pdf.set_text_color(0, 0, 0)
    
    # ID table
    label =   ['Student', 'CID', 'Course', 'Year', 'Marker', 'Marker Role']
    content = ['{student_first_name} {student_last_name}',
               '{student_cid}',
               '{course_presentation}',
               '{academic_year}',
               '{marker.first_name} {marker.last_name}',
               '{marker_role}']
    
    for l, c in zip(label, content):
        pdf.set_font("DejaVu", size=12, style='B')
        pdf.cell(60, 8, txt=l, align="L")
        pdf.set_font("DejaVu", size=12)
        pdf.cell(0, 8, txt=c.format(**record), align="L", ln=1)
    
    
    # add the questions in the order they appear in the JSON array
    pdf.set_fill_color(200,200,200)
    
    for q in form_json['questions']:
        
        # skip confidential questions if the report is not confidential
        if not confidential and q['confidential']:
            continue
        
        # insert the question title in a grey bar
        pdf.rect(pdf.get_x(), pdf.get_y(), h=8, w=190, style='F')
        pdf.set_font("DejaVu", size=12, style='B')
        pdf.cell(0, 8, txt=q['title'], align="L", ln=1)
        
        # insert the components
        for c in q['components']:
            
            # skip confidential components if the report is not confidential
            if not confidential and q['confidential']:
                continue
            
            pdf.set_font("DejaVu", size=12, style='B')
            pdf.cell(60, 8, txt=c['label'], align="L")
            pdf.ln()
            pdf.set_font("DejaVu", size=12)
            
            if c['type'] == 'query':
                # This is a tricky line. globals() contains globals functions, so needs
                # the appropriate query function to be imported. All such functions
                # get the assignment record as an input. You could use eval() here but
                # that has security risks - hard to see them applying here, but hey.
                contents = globals()[c['query']](record, pdf=True)
            else:
                contents = record.assignment_data[c['variable']]
            
            if contents is None:
                contents = ""
            pdf.set_left_margin(70)
            pdf.write(6, txt=contents)
            pdf.set_left_margin(10)
            pdf.ln()
        
        # spacer
        pdf.ln()
    
    pdf.close()
    pdf = pdf.output(dest='S').encode('latin-1') # unicode string to bytes
    filename = '{} {} {} {} {}.pdf'.format(record.course_presentation,
                                            record.academic_year, 
                                            record.student_first_name,
                                            record.student_last_name,
                                            record.id)
    
    return (pdf, filename)


## FORM QUERIES
## These function (currently only one) allow a form to include data by specifying a 'query'
## component in the form json. These should accept an assignments record as the first argument
## and then the option to provide either html (default, for web display) or a text repr
## for use in the PDF.

def query_report_marker_grades(record, pdf=False):
    """Creates a table of existing individual report marker grades
    """
    
    db = current.db
    
    report_grades = db((db.assignments.student_cid == record.student_cid) &
                       (db.assignments.course_presentation == record.course_presentation) &
                       (db.assignments.academic_year == record.academic_year) &
                       (db.assignments.marker_role == 'Marker')
                       ).select(
                           db.assignments.marker,
                           db.assignments.assignment_data,
                           db.assignments.status)
    
    report_grades = list(report_grades.render())
    
    report_grades = [(rw.marker, rw.assignment_data['grade']) 
                        if rw.status in ['Submitted', 'Released']
                        else (rw.marker, 'Not submitted')
                        for rw in report_grades]
    
    if pdf:
        report_grades = [f'{rw[0]} ({rw[1]})' for rw in report_grades]
        return '\n'.join(report_grades)
    else:
        return TABLE(report_grades, _class='table')
