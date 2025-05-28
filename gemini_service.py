import google.generativeai as genai
from typing import List, Dict, Optional
from config import Config

class GeminiService:
    def __init__(self):
        self.config = Config()
        genai.configure(api_key=self.config.GEMINI_API_KEY)
        self.model = genai.GenerativeModel('gemini-2.0-flash')
        
    def summarize_emails(self, emails: List[Dict]) -> str:
        """Generate summary of unread emails"""
        if not emails:
            return "No unread emails found."
        email_texts = []
        for email in emails:
            email_text = f"From: {email['sender']}\nSubject: {email['subject']}\nContent: {email['body'][:500]}..."
            email_texts.append(email_text)
            
        prompt = f"""
        Please provide a concise summary of these {len(emails)} unread emails:
        
        {chr(10).join(email_texts)}
        
        Summarize:
        1. Key senders and topics
        2. Urgent items that need attention
        3. Overall themes or categories
        
        Keep the summary brief and actionable
        """
        
        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating summary: {e}"
        
    def categorize_email(self, email: Dict) -> str:
        """Categorize email for auto reply decisions"""
        prompt = f"""
        Categorize this email into one of these categories:
        - calendar_invite: Meeting invitations, calendar events
        - newsletter: Marketing emails, newsletters, promotions
        - notification: System notifications, confirmations, receipts
        - confirmation: Booking confirmations, order confirmations
        - personal: Personal correspondence requiring human response
        - business: Business emails requiring human attention
        - urgent: Emails marked urgent or requiring immediate attention
        
        Email:
        From: {email['sender']}
        Subject: {email['subject']}
        Content: {email['body'][:300]}
        
        Respond with just the category name.
        """
        
        try:
            reponse = self.model.generate_content(prompt)
            return reponse.text.strip().lower()
        except Exception as e:
            return "unknown"
        
    def generate_reply(self, email: Dict, user_preferences: Optional[Dict]= None) -> str:
        """Generate appropriate email reply"""
        category = self.categorize_email(email)

        preferences_context = ""
        if user_preferences:
            preferences_context = f"User preferences: {user_preferences}"

        if category == "calendar_invite":
            prompt = f"""
            Generate a polite response to this calendar invitation:

            From: {email['sender']}
            Subject: {email['subject']}
            Content: {email['body'][:500]}

            {preferences_context}

            The response should:
            - Be professional and brief
            - Accept tentatively if it's a reasonable request
            - Ask for more details if needed
            - Be friendly but not overly casual
            """
        elif category in ["newsletter", "notification"]:
            prompt = f"""
            Generate a brief acknowledgment for this {category}:

            From: {email['sender']}
            Subject: {email['subject']}

            The response should:
            - Be very brief (1-2 sentences)
            - Acknowledge receipt
            - Be polite but minimal
            """
        else:
            prompt = f"""
            Generate a professional email reply for:

            From: {email['sender']}
            Subject: {email['subject']}
            Content: {email['body'][:500]}

            {preferences_context}

            The reply should:
            - Be professional and helpful
            - Address the main points
            - Be concise but thorough
            - Ask clarifying questions if needed
            - Match the tone of the original email
            """

        try:
            response = self.model.generate_content(prompt)
            return response.text
        except Exception as e:
            return f"Error generating reply: {e}"

    def should_auto_reply(self, email: Dict) -> bool:
        """Determine if email should receive auto-reply"""
        category = self.categorize_email(email)
        return category in self.config.AUTO_REPLY_CATEGORIES
    
    def learn_from_user_action(self, email: Dict, user_action: str, user_reply: Optional[str] = None):
        """Learn from user actions for future improvement"""
        learning_data = {
            'email_category': self.categorize_email(email),
            'user_action': user_action,  # 'approved', 'rejected', 'modified'
            'user_reply': user_reply,
            'original_sender': email['sender'],
            'subject_keywords': email['subject'].split()
        }
        
        print(f"Learning data: {learning_data}")
      
