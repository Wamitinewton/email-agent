import os
from dotenv import load_dotenv


load_dotenv()

class Config:
    GEMINI_API_KEY = os.getenv('GEMINI_API_KEY')

    EMAIL_ADDRESS = os.getenv('EMAIL_ADDRESS')
    EMAIL_PASSWORD = os.getenv('EMAIL_PASSWORD')
    IMAP_SERVER = os.getenv('IMAP_SERVER', 'imap.gmail.com')
    SMTP_SERVER = os.getenv('SMTP_SERVER', 'smtp.gmail.com')
    IMAP_PORT = int(os.getenv('IMAP_PORT', 993))
    SMTP_PORT = int(os.getenv('SMTP_PORT', 587))
    SECRET_KEY = os.getenv('FLASK_SECRET_KEY')
    DEBUG = os.getenv('FLASK_DEBUG', 'False').lower() == 'true'

    AUTO_REPLY_CATEGORIES = [
        'calendar_invite',
        'newsletter',
        'notification',
        'confirmation'
    ]