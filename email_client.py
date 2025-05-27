import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import ssl
from typing import List, Dict, Optional
from config import Config


class EmailClient:
    def __init__(self):
        self.config = Config()
        self.imap_connection = None
        self.smtp_connection = None

    def connect_imap(self):
        """Connect to IMAP server"""
        try:
            self.imap_connection = imaplib.IMAP4_SSL(
                self.config.IMAP_SERVER,
                self.config.IMAP_PORT
            )
            self.imap_connection.login(
                self.config.EMAIL_ADDRESS, 
                self.config.EMAIL_PASSWORD
            )
            return True
        except Exception as e:
            print(f"IMAP connection failed: {e}")
            return False
            
    def connect_smtp(self):
        """Connect to SMTP server"""
        try:
            self.smtp_connection = smtplib.SMTP(
                self.config.SMTP_SERVER,
                self.config.SMTP_PORT
            )
            self.smtp_connection.ehlo()
            self.smtp_connection.starttls()
            self.smtp_connection.ehlo()
            self.smtp_connection.login(
                self.config.EMAIL_ADDRESS,
                self.config.EMAIL_PASSWORD
            )
            return True
        except Exception as e:
            print(f"SMTP connection failed: {e}")
            return False
        
    def get_unread_emails(self, limit: int = 10) -> List[Dict]:
        """Fetch unread emails"""
        if not self.connect_imap():
            return []
        emails = []
        try:
            self.imap_connection.select('INBOX')
            status, messages = self.imap_connection.search(None, 'UNSEEN')
            
            if status == 'OK':
             email_ids = messages[0].split()[-limit:]
             
             for email_id in email_ids:
                 status, msg_data = self.imap_connection.fetch(email_id, '(RFC822)')
                 if status == 'OK':
                     email_body = msg_data[0][1]
                     email_message = email.message_from_bytes(email_body)
                     
                     # Decode The Subject
                     subject = decode_header(email_message["Subject"])[0][0]
                     if isinstance(subject, bytes):
                         subject = subject.decode()
                         
                         # Get email content
                         body = self._extract_email_body(email_message)
                         
                         emails.append({
                            'id': email_id.decode(),
                            'subject': subject,
                            'sender': email_message["From"],
                            'body': body,
                            'date': email_message["Date"]
                        })
        except Exception as e:
            print(f"Error fetching emails: {e}")
        finally:
            if self.imap_connection:
                self.imap_connection.close()
                self.imap_connection.logout()
                         
                         
                        

    def _extract_email_body(self, email_message) -> str:
        """Extract plain text body from email"""
        body = ""
        if email_message.is_multipart():
            for part in email_message.walk():
                if part.get_content_type() == "text/plain":
                    body = part.get_payload(decode=True).decode()
                    break
            else:
                body = email_message.get_payload(decode=True).decode()
            return body    
    
    def mark_as_read(self, email_id: str):
        """ Mark email as read"""
        if not self.connect_imap():
            return False
        
        try:
            self.imap_connection.select('INBOX')
            self.imap_connection.store(email_id, '+FLAGS', '\\Seen')
            return True
        
        except Exception as e:
            print(f"Error marking email as read: {e}")
            return False
        finally:
            if self.imap_connection:
                self.imap_connection.close()
                self.imap_connection.logout()