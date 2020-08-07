import datetime
import os
import sys
import csv
import itertools
import zipfile
import io
import openpyxl
import simplejson as json
from collections import Counter
import html2text
import fpdf
import importlib
import time
import ssl
import imaplib
import socket
import smtplib
import email

from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from gluon import current, SQLFORM, DIV, LABEL, CAT, B, P, A, URL, HTTP

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
        
        # now create a set of links:
        recs = sorted(recs, key=lambda x: (x.course_presentation, x.marker_role))
        links = [CAT(P(B('Course: '), r.course_presentation,
                       B('; Marking Role: '), r.marker_role,
                       B('; Student: '), A(r.student_first_name, ' ', r.student_last_name, 
                                         _href=URL('write_report', scheme=True, host=True,
                                                   vars={'record':r.id, 'staff_access_token': r.staff_access_token})),
                       B('; Due Date: '), r.due_date)) for r in recs]
        
        success = mailer.sendmail(subject='Silwood Park Masters Project Marking', 
                                  to=marker, email_template='marker_distribute.html',
                                  email_template_dict={'name':recs[0].marker.first_name,
                                                 'links':CAT(links).xml()})
        
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
    
    # load records
    records = [db.assignments(id) for id in ids]
    
    # find the maximum number of entries per student for each role
    # - not assuming 1 supervisor and 2 markers and taking the role
    #   names directly from the definition list in db.py.
    roles = [(r.student_cid, r.marker_role) for r in records]
    roles = list(Counter(roles).items())
    roles = [(r[0][1], r[1]) for r in roles] # dropping student id
    
    n_roles = {}
    for key, group in itertools.groupby(roles, lambda x: x[0]):
        n_roles[key] = max([x[1] for x in group])
    
    # Insert headers and get the starting columns for each role
    ws['A3'] = 'CID'
    ws['B3'] = 'Last Name'
    ws['C3'] = 'First Name'
    ws['D3'] = 'Course Presentation'
    ws['E3'] = 'Year'
    mark_start = 6
    col_starts = {}
    i = 0
    for k, n in n_roles.items():
        col_starts[k] = mark_start + i
        for v in range(n):
            ws.cell(row=3, column = mark_start + i, value='{} {} Grade'.format(k, v+1))
            ws.cell(row=3, column = mark_start + i + 1, value='{} {} Name'.format(k, v+1))
            i +=2
    
    # Write Data
    row = 4
    
    # - group records by student
    records.sort(key=lambda rec: rec['student_cid'])
    students = {k: list(recs) for k, recs in itertools.groupby(records, lambda x: x['student_cid'])}
    
    for cid, student_recs in students.items():
        
        # fill in the student info from the first record
        ws.cell(row = row, column=1, value=student_recs[0].student_cid)
        ws.cell(row = row, column=2, value=student_recs[0].student_last_name)
        ws.cell(row = row, column=3, value=student_recs[0].student_first_name)
        ws.cell(row = row, column=4, value=student_recs[0].course_presentation)
        ws.cell(row = row, column=5, value=student_recs[0].academic_year)
        
        # now split records by role
        student_recs.sort(key=lambda rec: rec['marker_role'])
        student_recs = {k: list(recs) for k, recs in itertools.groupby(student_recs, lambda x: x['marker_role'])}
        
        # output the contents
        for this_role in list(student_recs.keys()):
            
            # start in the right column
            this_col = col_starts[this_role]
            
            for this_record in student_recs[this_role]:
                ws.cell(row = row, column=this_col+1, value=this_record.marker.first_name + ' ' + this_record.marker.last_name)
                if (this_record.form_data is not None and 'grade' in list(this_record.form_data.keys()) 
                    and this_record.form_data['grade'] is not None):
                    # slice off the text part of the grade from the dropdown
                    g = this_record.form_data['grade']
                    g = int(g[0:g.index('%')])
                    ws.cell(row = row, column=this_col, value=g)
                this_col += 2
        
        # advance to next row
        row += 1
    
    current.response.headers['Content-Type'] = 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    attachment = 'attachment;filename=Marking_Grades_{}.xlsx'.format(datetime.date.today().isoformat())
    current.response.headers['Content-Disposition'] = attachment
    content = openpyxl.writer.excel.save_virtual_workbook(wb)
    raise HTTP(200, content,
               **{'Content-Type':'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                  'Content-Disposition':attachment + ';'})

## --------------------------------------------------------------------------------
## E-MAILING SETUP
## Emailing uses view templates - the message body is created by taking a template
## name, filling it with values from template dictionary.
## The Mail class can log in to the mail server to send the email (SMTP) and store
## it in an mailbox on the account using IMAP. A Mail instance can be used just to
## send a single message but can also be created, logged in and recycled for several
## messages to reduce handling time.
## --------------------------------------------------------------------------------

class Mail:
    
    def __init__(self):
        # Load the credentials from config
        self.send_address = current.myconf.get('email.send_address')
        self.password = current.myconf.get('email.password') 

        self.smtp_host = current.myconf.get('email.smtp_host')
        self.smtp_user = current.myconf.get('email.smtp_user') 
        self.smtp_server = None

        self.imap_host = current.myconf.get('email.imap_host')
        self.imap_user = current.myconf.get('email.imap_user') 
        self.imap_server = None
        
        self.logged_in = None # ternary: None, False (failed) and True

    def login(self):
        # creates connections to the smtp and imap servers for mail
        # send and storage
        
        smtp_server = smtplib.SMTP(self.smtp_host) 
        smtp_server.ehlo() 
        start_tls = smtp_server.starttls()
        
        try:
            status, message = smtp_server.login(self.smtp_user, self.password)
        except smtplib.SMTPAuthenticationError as e:
            # Logout to close any connetions and then set False to show failure
            self.logout()
            self.logged_in = False
            return
        
        self.smtp_server = smtp_server
        
        imap_server = imaplib.IMAP4_SSL(self.imap_host, 993)
        try:
            imap_server.login(self.imap_user, self.password)
        except socket.error:
            # Logout to close any connetions and then set False to show failure
            self.logout()
            self.logged_in = False
            return

        self.imap_server = imap_server
        
        self.logged_in = True

    def logout(self):
        
        if self.smtp_server is not None:
            self.smtp_server.quit()
        
        if self.imap_server is not None:
            self.imap_server.logout()
        
        self.logged_in = None

    def sendmail(self, to, subject, email_template=None, email_template_dict=None, text=None):
        """
        This sends an html body text to a recipient, including a text representation.
        If the Mail instance hasn't already been logged in, then it will log in
        just for this email.
        """
        
        if self.logged_in is None:
            local_login = True
            self.login()
        elif self.logged_in:
            local_login = False
        
        if not self.logged_in:
            self._logmail(False, 'mail send error - server logins failed',
                          to=to, subject=subject, email_template=email_template, 
                          email_template_dict=email_template_dict)
            return False
        
        # Create message container - the correct MIME type is multipart/alternative.
        message = MIMEMultipart('alternative')
        message["From"] = self.send_address
        message["To"] = to
        message["Subject"] = subject
        
        # Get a rendered message as both text/plain and text/html, using message
        # as the content if provided
        if text is not None:
            message.attach(MIMEText(text, 'plain'))
        elif email_template is not None and email_template_dict is not None:
            html_body = current.response.render('email_templates/' + email_template, email_template_dict)
            message.attach(MIMEText(html2text.html2text(html_body), 'plain'))
            message.attach(MIMEText(html_body, 'html'))
        else:
            raise RuntimeError('text or email template and data required')
        
        try:
            self.smtp_server.sendmail(self.send_address, to, message.as_string())
        except smtplib.SMTPException:
            self._logmail(False, 'Message did not send (SMTP error)',
                          to=to, subject=subject, email_template=email_template, 
                          email_template_dict=email_template_dict)
            return False
            
        try:
            self.imap_server.append('"Marking_Reports"', '\\Seen', 
                                    imaplib.Time2Internaldate(time.time()), 
                                    message.as_bytes())
        except socket.error:
            self._logmail(False, 'Message did not store (IMAP error) - it _did_ send',
                          to=to, subject=subject, email_template=email_template, 
                          email_template_dict=email_template_dict)
            
            return False
        
        if local_login:
            self.logout()
        
        self._logmail(True, 'success',
                      to=to, subject=subject, email_template=email_template, 
                      email_template_dict=email_template_dict)
        
        return True

    def _logmail(self, sent, status, to, subject, email_template, email_template_dict):
        
        # log it in the database
        current.db.email_log.insert(email_to=to, 
                                    subject=subject, 
                                    email_template=email_template,
                                    email_template_dict=json.dumps(email_template_dict),
                                    email_cc=None,
                                    sent=sent,
                                    status = status,
                                    message_date=datetime.datetime.now())
        current.db.commit()


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
    fpdf.set_global('SYSTEM_TTFONTS', current.myconf.get('fpdf.font_dir'))
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
    label =   ['Student', 'CID', 'Course', 'Marker', 'Marker Role']
    content = ['{student_first_name} {student_last_name}',
               '{student_cid}',
               '{course_presentation}',
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
            pdf.set_font("DejaVu", size=12, style='B')
            pdf.cell(60, 8, txt=c['label'], align="L")
            pdf.set_font("DejaVu", size=12)
            contents = record.form_data[c['variable']]
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
                                            record.year, 
                                            record.student_first_name,
                                            record.student_last_name,
                                            record.id)
    
    return (pdf, filename)




