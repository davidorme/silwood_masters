## --------------------------------------------------------------------------------
## E-MAILING SETUP
## Emailing uses view templates - the message body is created by taking a template
## name, filling it with values from template dictionary.
## The Mail class can log in to the mail server to send the email (SMTP) and store
## it in an mailbox on the account using IMAP. A Mail instance can be used just to
## send a single message but can also be created, logged in and recycled for several
## messages to reduce handling time.
## --------------------------------------------------------------------------------
import datetime
import time
import ssl
import imaplib
import socket
import smtplib
import email
import simplejson as json
from email.mime.base import MIMEBase
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
import html2text

from gluon import current

class Mail:
    
    def __init__(self):
        # Load the credentials from config
        self.send_address = current.configuration.get('email.send_address')
        self.password = current.configuration.get('email.password') 

        self.smtp_host = current.configuration.get('email.smtp_host')
        self.smtp_user = current.configuration.get('email.smtp_user') 
        self.smtp_server = None

        self.imap_host = current.configuration.get('email.imap_host')
        self.imap_user = current.configuration.get('email.imap_user') 
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
