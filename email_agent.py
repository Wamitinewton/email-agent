from typing import List, Dict, Optional
from email_client import EmailClient
from gemini_service import GeminiService
import json
import os

class EmailAgent:
    def __init__(self, max_emails_to_process: int = 5):
        self.email_client = EmailClient()
        self.gemini_service = GeminiService()
        self.user_preferences = self._load_user_preferences()
        self.max_emails_to_process = max_emails_to_process
    
    def _load_user_preferences(self) -> Dict:
        """Load user preferences from file"""
        try:
            if os.path.exists('user_preferences.json'):
                with open('user_preferences.json', 'r') as f:
                    return json.load(f)
        except Exception as e:
            print(f"Error loading preferences: {e}")
        
        return {
            'auto_reply_enabled': True,
            'response_tone': 'professional',
            'signature': 'Best regards',
            'working_hours': {'start': 9, 'end': 17},
            'auto_categories': ['calendar_invite', 'newsletter']
        }
    
    def _save_user_preferences(self):
        """Save user preferences to file"""
        try:
            with open('user_preferences.json', 'w') as f:
                json.dump(self.user_preferences, f, indent=2)
        except Exception as e:
            print(f"Error saving preferences: {e}")
    
    def process_inbox(self) -> Dict:
        """Main function to process inbox - LIMITED to first few emails to save API quota"""
        # Get unread emails but limit the fetch itself to save resources
        unread_emails = self.email_client.get_unread_emails(limit=self.max_emails_to_process)
        
        total_unread_count = self._get_total_unread_count()
        
        if not unread_emails:
            return {
                'summary': 'No unread emails found.',
                'processed_emails': [],
                'auto_replies_sent': 0,
                'total_unread': total_unread_count,
                'processed_count': 0,
                'quota_limited': False
            }
        
        # Limit processing to avoid quota exhaustion
        emails_to_process = unread_emails[:self.max_emails_to_process]
        quota_limited = len(unread_emails) > self.max_emails_to_process
        
        print(f"Processing {len(emails_to_process)} out of {total_unread_count} unread emails (quota limit: {self.max_emails_to_process})")
        
        # Generate summary only for the limited set
        summary = self.gemini_service.summarize_emails(emails_to_process)
        
        processed_emails = []
        auto_replies_sent = 0
        
        for email in emails_to_process:
            try:
                print(f"Processing email: {email['subject'][:50]}...")
                
                # Generate reply
                suggested_reply = self.gemini_service.generate_reply(
                    email, self.user_preferences
                )
                
                # Check if should auto-reply
                should_auto_reply = (
                    self.user_preferences.get('auto_reply_enabled', False) and
                    self.gemini_service.should_auto_reply(email)
                )
                
                email_result = {
                    'email': email,
                    'suggested_reply': suggested_reply,
                    'auto_reply_sent': False,
                    'category': self.gemini_service.categorize_email(email)
                }
                
                # Send auto-reply if enabled and appropriate
                if should_auto_reply:
                    sender_email = self._extract_email_address(email['sender'])
                    if self.email_client.send_reply(
                        sender_email, 
                        email['subject'], 
                        suggested_reply
                    ):
                        email_result['auto_reply_sent'] = True
                        auto_replies_sent += 1
                        
                        # Mark as read
                        self.email_client.mark_as_read(email['id'])
                
                processed_emails.append(email_result)
                
            except Exception as e:
                print(f"Error processing email '{email['subject'][:30]}...': {e}")
                # Add basic info even if processing failed
                processed_emails.append({
                    'email': email,
                    'suggested_reply': f"Error processing: {str(e)}",
                    'auto_reply_sent': False,
                    'category': 'error',
                    'error': str(e)
                })
        
        return {
            'summary': summary,
            'processed_emails': processed_emails,
            'auto_replies_sent': auto_replies_sent,
            'total_unread': total_unread_count,
            'processed_count': len(emails_to_process),
            'quota_limited': quota_limited,
            'remaining_unread': max(0, total_unread_count - len(emails_to_process))
        }
    
    def _get_total_unread_count(self) -> int:
        """Get total count of unread emails without fetching full content"""
        try:
            if self.email_client.connect_imap():
                self.email_client.imap_connection.select('INBOX')
                status, messages = self.email_client.imap_connection.search(None, 'UNSEEN')
                if status == 'OK' and messages[0]:
                    return len(messages[0].split())
        except Exception as e:
            print(f"Error getting unread count: {e}")
        return 0
    
    def process_next_batch(self, skip_count: int = 0) -> Dict:
        """Process the next batch of emails, skipping the first 'skip_count' emails"""
        # This would require modifying email_client to support offset/skip
        # For now, we'll implement a simple version
        unread_emails = self.email_client.get_unread_emails(limit=skip_count + self.max_emails_to_process)
        
        if len(unread_emails) <= skip_count:
            return {
                'summary': 'No more emails to process.',
                'processed_emails': [],
                'auto_replies_sent': 0,
                'total_unread': len(unread_emails),
                'processed_count': 0,
                'quota_limited': False
            }
        
        # Skip the first 'skip_count' emails and process the next batch
        emails_to_process = unread_emails[skip_count:skip_count + self.max_emails_to_process]
        
        print(f"Processing batch starting from email {skip_count + 1}")
        
        # Process this batch (reuse the same logic as process_inbox)
        processed_emails = []
        auto_replies_sent = 0
        
        for email in emails_to_process:
            try:
                print(f"Processing email: {email['subject'][:50]}...")
                
                suggested_reply = self.gemini_service.generate_reply(
                    email, self.user_preferences
                )
                
                should_auto_reply = (
                    self.user_preferences.get('auto_reply_enabled', False) and
                    self.gemini_service.should_auto_reply(email)
                )
                
                email_result = {
                    'email': email,
                    'suggested_reply': suggested_reply,
                    'auto_reply_sent': False,
                    'category': self.gemini_service.categorize_email(email)
                }
                
                if should_auto_reply:
                    sender_email = self._extract_email_address(email['sender'])
                    if self.email_client.send_reply(sender_email, email['subject'], suggested_reply):
                        email_result['auto_reply_sent'] = True
                        auto_replies_sent += 1
                        self.email_client.mark_as_read(email['id'])
                
                processed_emails.append(email_result)
                
            except Exception as e:
                print(f"Error processing email: {e}")
                processed_emails.append({
                    'email': email,
                    'suggested_reply': f"Error processing: {str(e)}",
                    'auto_reply_sent': False,
                    'category': 'error',
                    'error': str(e)
                })
        
        summary = self.gemini_service.summarize_emails(emails_to_process)
        
        return {
            'summary': summary,
            'processed_emails': processed_emails,
            'auto_replies_sent': auto_replies_sent,
            'total_unread': len(unread_emails),
            'processed_count': len(emails_to_process),
            'batch_start': skip_count + 1,
            'quota_limited': True
        }
    
    def send_manual_reply(self, email_id: str, reply_text: str) -> bool:
        """Send a manually crafted reply"""
        # Find the email by ID from a limited set
        unread_emails = self.email_client.get_unread_emails(limit=50)  # Reasonable limit for finding specific email
        target_email = None
        
        for email in unread_emails:
            if email['id'] == email_id:
                target_email = email
                break
        
        if not target_email:
            return False
        
        sender_email = self._extract_email_address(target_email['sender'])
        success = self.email_client.send_reply(
            sender_email, 
            target_email['subject'], 
            reply_text
        )
        
        if success:
            # Mark as read
            self.email_client.mark_as_read(email_id)
            
            # Learn from user action
            self.gemini_service.learn_from_user_action(
                target_email, 
                'manual_reply', 
                reply_text
            )
        
        return success
    
    def approve_suggested_reply(self, email_id: str) -> bool:
        """Approve and send a suggested reply"""
        unread_emails = self.email_client.get_unread_emails(limit=50)
        target_email = None
        
        for email in unread_emails:
            if email['id'] == email_id:
                target_email = email
                break
        
        if not target_email:
            return False
        
        # Generate reply again
        reply_text = self.gemini_service.generate_reply(
            target_email, self.user_preferences
        )
        
        sender_email = self._extract_email_address(target_email['sender'])
        success = self.email_client.send_reply(
            sender_email, 
            target_email['subject'], 
            reply_text
        )
        
        if success:
            self.email_client.mark_as_read(email_id)
            self.gemini_service.learn_from_user_action(
                target_email, 'approved', reply_text
            )
        
        return success
    
    def update_preferences(self, new_preferences: Dict):
        """Update user preferences"""
        self.user_preferences.update(new_preferences)
        self._save_user_preferences()
    
    def set_processing_limit(self, limit: int):
        """Update the maximum number of emails to process"""
        self.max_emails_to_process = max(1, min(limit, 50))  # Keep between 1 and 50
        print(f"Email processing limit set to {self.max_emails_to_process}")
    
    def _extract_email_address(self, sender: str) -> str:
        """Extract email address from sender string"""
        import re
        match = re.search(r'<(.+?)>', sender)
        return match.group(1) if match else sender
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            'preferences': self.user_preferences,
            'max_emails_to_process': self.max_emails_to_process,
            'last_processed': 'Not implemented yet',
            'total_processed': 'Not implemented yet',
            'auto_reply_rate': 'Not implemented yet'
        }


# Example usage with quota management
if __name__ == "__main__":
    # Initialize agent with 5 email limit
    agent = EmailAgent(max_emails_to_process=5)
    
    print("Processing first batch of emails...")
    result = agent.process_inbox()
    
    print(f"Summary: {result['summary']}")
    print(f"Processed: {result['processed_count']} out of {result['total_unread']} unread emails")
    print(f"Auto-replies sent: {result['auto_replies_sent']}")
    
    if result['quota_limited']:
        print(f"Quota limited: {result['remaining_unread']} emails remaining")
  