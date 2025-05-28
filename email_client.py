import imaplib
import smtplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
import ssl
from typing import List, Dict, Optional
import os
import re
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
                "imap.gmail.com",
                993
            )
                      
            self.imap_connection.login(self.config.EMAIL_ADDRESS, self.config.EMAIL_PASSWORD)
            print("IMAP connection successful")
            return True
        except Exception as e:
            print(f"IMAP connection failed: {e}")
            return False
            
    def connect_smtp(self):
        """Connect to SMTP server"""
        try:
            self.smtp_connection = smtplib.SMTP(
                "smtp.gmail.com",
                587
            )
            self.smtp_connection.ehlo()
            self.smtp_connection.starttls()
            self.smtp_connection.ehlo()
            
            self.smtp_connection.login(self.config.EMAIL_ADDRESS, self.config.EMAIL_PASSWORD)
            print("SMTP connection successful")
            return True
        except Exception as e:
            print(f"SMTP connection failed: {e}")
            return False

    def send_reply(self, sender_email: str, subject: str, reply_body: str) -> bool:
        """Send a reply to an email"""
        if not self.connect_smtp():
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.EMAIL_ADDRESS
            msg['To'] = sender_email
            
            # Set subject - add Re: if not already present
            if not subject.lower().startswith('re:'):
                msg['Subject'] = f"Re: {subject}"
            else:
                msg['Subject'] = subject
            
            # Attach the reply body
            msg.attach(MIMEText(reply_body, 'plain'))
            
            # Send the email
            text = msg.as_string()
            self.smtp_connection.sendmail(self.config.EMAIL_ADDRESS, sender_email, text)
            
            print(f"Reply sent successfully to {sender_email}")
            return True
            
        except Exception as e:
            print(f"Error sending reply: {e}")
            return False
        finally:
            if self.smtp_connection:
                try:
                    self.smtp_connection.quit()
                except:
                    pass

    def send_email(self, to_email: str, subject: str, body: str, cc: List[str] = None, bcc: List[str] = None) -> bool:
        """Send a new email"""
        if not self.connect_smtp():
            return False
        
        try:
            # Create message
            msg = MIMEMultipart()
            msg['From'] = self.config.EMAIL_ADDRESS
            msg['To'] = to_email
            msg['Subject'] = subject
            
            if cc:
                msg['Cc'] = ', '.join(cc)
            if bcc:
                msg['Bcc'] = ', '.join(bcc)
            
            # Attach the body
            msg.attach(MIMEText(body, 'plain'))
            
            # Prepare recipient list
            recipients = [to_email]
            if cc:
                recipients.extend(cc)
            if bcc:
                recipients.extend(bcc)
            
            # Send the email
            text = msg.as_string()
            self.smtp_connection.sendmail(self.config.EMAIL_ADDRESS, recipients, text)
            
            print(f"Email sent successfully to {to_email}")
            return True
            
        except Exception as e:
            print(f"Error sending email: {e}")
            return False
        finally:
            if self.smtp_connection:
                try:
                    self.smtp_connection.quit()
                except:
                    pass

    def _extract_email_address(self, email_string: str) -> str:
        """Extract email address from string like 'Name <email@domain.com>'"""
        if '<' in email_string and '>' in email_string:
            match = re.search(r'<([^>]+)>', email_string)
            if match:
                return match.group(1)
        return email_string.strip()
        
    def get_unread_emails(self, limit: int = 10) -> List[Dict]:
        """Fetch unread emails"""
        if not self.connect_imap():
            return []
            
        emails = []
        try:
            self.imap_connection.select('INBOX')
            status, messages = self.imap_connection.search(None, 'UNSEEN')
            
            print(f"Search status: {status}")
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                print(f"Found {len(email_ids)} unread emails")
                
                # Get the last 'limit' emails (most recent)
                email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
                
                for email_id in email_ids:
                    try:
                        status, msg_data = self.imap_connection.fetch(email_id, '(RFC822)')
                        if status == 'OK' and msg_data[0] is not None:
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # Decode The Subject
                            subject_header = email_message.get("Subject", "")
                            if subject_header:
                                subject = decode_header(subject_header)[0][0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode('utf-8', errors='ignore')
                            else:
                                subject = "No Subject"
                            
                            # Get email content
                            body = self._extract_email_body(email_message)
                            
                            emails.append({
                                'id': email_id.decode(),
                                'subject': subject,
                                'sender': email_message.get("From", "Unknown"),
                                'body': body,
                                'date': email_message.get("Date", "Unknown"),
                                'message_id': email_message.get("Message-ID", "")
                            })
                            
                    except Exception as e:
                        print(f"Error processing email {email_id}: {e}")
                        continue
            else:
                print("No unread emails found")
                
        except Exception as e:
            print(f"Error fetching emails: {e}")
        finally:
            if self.imap_connection:
                try:
                    self.imap_connection.close()
                    self.imap_connection.logout()
                except:
                    pass
        
        return emails

    def _extract_email_body(self, email_message) -> str:
        """Extract plain text body from email"""
        body = ""
        
        if email_message.is_multipart():
            # Walk through all parts of the email
            for part in email_message.walk():
                content_type = part.get_content_type()
                content_disposition = str(part.get("Content-Disposition", ""))
                
                # Look for plain text content that's not an attachment
                if content_type == "text/plain" and "attachment" not in content_disposition:
                    try:
                        body = part.get_payload(decode=True).decode('utf-8', errors='ignore')
                        break
                    except Exception as e:
                        print(f"Error decoding email part: {e}")
                        continue
        else:
            # Single part email
            try:
                body = email_message.get_payload(decode=True).decode('utf-8', errors='ignore')
            except Exception as e:
                print(f"Error decoding email body: {e}")
                body = "Could not decode email body"
        
        return body.strip() if body else "No readable content"
    
    def mark_as_read(self, email_id: str):
        """Mark email as read"""
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
                try:
                    self.imap_connection.close()
                    self.imap_connection.logout()
                except:
                    pass

    def get_all_emails(self, limit: int = 10) -> List[Dict]:
        """Fetch all emails (for testing purposes)"""
        if not self.connect_imap():
            return []
            
        emails = []
        try:
            self.imap_connection.select('INBOX')
            status, messages = self.imap_connection.search(None, 'ALL')
            
            print(f"Search status: {status}")
            
            if status == 'OK' and messages[0]:
                email_ids = messages[0].split()
                print(f"Found {len(email_ids)} total emails")
                
                # Get the last 'limit' emails (most recent)
                email_ids = email_ids[-limit:] if len(email_ids) > limit else email_ids
                
                for email_id in email_ids:
                    try:
                        status, msg_data = self.imap_connection.fetch(email_id, '(RFC822)')
                        if status == 'OK' and msg_data[0] is not None:
                            email_body = msg_data[0][1]
                            email_message = email.message_from_bytes(email_body)
                            
                            # Decode The Subject
                            subject_header = email_message.get("Subject", "")
                            if subject_header:
                                subject = decode_header(subject_header)[0][0]
                                if isinstance(subject, bytes):
                                    subject = subject.decode('utf-8', errors='ignore')
                            else:
                                subject = "No Subject"
                            
                            emails.append({
                                'id': email_id.decode(),
                                'subject': subject,
                                'sender': email_message.get("From", "Unknown"),
                                'date': email_message.get("Date", "Unknown"),
                                'message_id': email_message.get("Message-ID", "")
                            })
                            
                    except Exception as e:
                        print(f"Error processing email {email_id}: {e}")
                        continue
                        
        except Exception as e:
            print(f"Error fetching emails: {e}")
        finally:
            if self.imap_connection:
                try:
                    self.imap_connection.close()
                    self.imap_connection.logout()
                except:
                    pass
        
        return emails


# Test the connection and new functionality
if __name__ == "__main__":
    client = EmailClient()
    
    if client.connect_imap():
        print("Successfully connected to Gmail!")
        
        unread_emails = client.get_unread_emails(5)
        print(f"Retrieved {len(unread_emails)} unread emails")
        
        for email_data in unread_emails:
            print(f"Subject: {email_data['subject']}")
            print(f"From: {email_data['sender']}")
            print(f"Date: {email_data['date']}")
            print("-" * 50)
        
        if unread_emails:
            first_email = unread_emails[0]
            sender_email = client._extract_email_address(first_email['sender'])
            reply_body = "Thank you for your email. I have received it and will respond accordingly."
        
        if not unread_emails:
            print("No unread emails found. Checking for any emails...")
            all_emails = client.get_all_emails(5)
            print(f"Retrieved {len(all_emails)} total emails")
            
            for email_data in all_emails:
                print(f"Subject: {email_data['subject']}")
                print(f"From: {email_data['sender']}")
                print(f"Date: {email_data['date']}")
                print("-" * 50)
    else:
        print("Failed to connect to Gmail")