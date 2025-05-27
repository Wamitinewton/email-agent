from typing import List, Dict, Optional
from email_client import EmailClient
from gemini_service import GeminiService
import json
import os

class EmailAgent:
    def __init__(self):
        self.email_client = EmailClient()
        self.gemini_service = GeminiService()
        self.user_preferences = self._load_user_preferences()
    
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
        """Main function to process inbox"""
        # Get unread emails
        unread_emails = self.email_client.get_unread_emails()
        
        if not unread_emails:
            return {
                'summary': 'No unread emails found.',
                'processed_emails': [],
                'auto_replies_sent': 0
            }
        
        # Generate summary
        summary = self.gemini_service.summarize_emails(unread_emails)
        
        processed_emails = []
        auto_replies_sent = 0
        
        for email in unread_emails:
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
        
        return {
            'summary': summary,
            'processed_emails': processed_emails,
            'auto_replies_sent': auto_replies_sent,
            'total_unread': len(unread_emails)
        }
    
    def send_manual_reply(self, email_id: str, reply_text: str) -> bool:
        """Send a manually crafted reply"""
        # Find the email by ID
        unread_emails = self.email_client.get_unread_emails()
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
        unread_emails = self.email_client.get_unread_emails()
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
    
    def _extract_email_address(self, sender: str) -> str:
        """Extract email address from sender string"""
        import re
        match = re.search(r'<(.+?)>', sender)
        return match.group(1) if match else sender
    
    def get_stats(self) -> Dict:
        """Get agent statistics"""
        return {
            'preferences': self.user_preferences,
            'last_processed': 'Not implemented yet',
            'total_processed': 'Not implemented yet',
            'auto_reply_rate': 'Not implemented yet'
        }