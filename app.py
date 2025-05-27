from flask import Flask, render_template, request, jsonify, redirect, url_for
from email_agent import EmailAgent
from config import Config
import threading
import time

app = Flask(__name__)
app.config.from_object(Config)

# Global email agent instance
email_agent = EmailAgent()

@app.route('/')
def index():
    """Main dashboard"""
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process_inbox():
    """Process inbox and return results"""
    try:
        result = email_agent.process_inbox()
        return jsonify({
            'success': True,
            'data': result
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/send_reply', methods=['POST'])
def send_reply():
    """Send a manual reply"""
    data = request.get_json()
    email_id = data.get('email_id')
    reply_text = data.get('reply_text')
    
    if not email_id or not reply_text:
        return jsonify({
            'success': False,
            'error': 'Missing email_id or reply_text'
        }), 400
    
    try:
        success = email_agent.send_manual_reply(email_id, reply_text)
        return jsonify({
            'success': success,
            'message': 'Reply sent successfully' if success else 'Failed to send reply'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/approve_reply', methods=['POST'])
def approve_reply():
    """Approve and send suggested reply"""
    data = request.get_json()
    email_id = data.get('email_id')
    
    if not email_id:
        return jsonify({
            'success': False,
            'error': 'Missing email_id'
        }), 400
    
    try:
        success = email_agent.approve_suggested_reply(email_id)
        return jsonify({
            'success': success,
            'message': 'Reply sent successfully' if success else 'Failed to send reply'
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/preferences', methods=['GET', 'POST'])
def preferences():
    """Get or update user preferences"""
    if request.method == 'GET':
        return jsonify({
            'success': True,
            'preferences': email_agent.user_preferences
        })
    
    if request.method == 'POST':
        try:
            new_preferences = request.get_json()
            email_agent.update_preferences(new_preferences)
            return jsonify({
                'success': True,
                'message': 'Preferences updated successfully'
            })
        except Exception as e:
            return jsonify({
                'success': False,
                'error': str(e)
            }), 500

@app.route('/stats')
def stats():
    """Get agent statistics"""
    try:
        stats = email_agent.get_stats()
        return jsonify({
            'success': True,
            'stats': stats
        })
    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500

@app.route('/auto_process')
def auto_process():
    """Start autonomous processing in background"""
    def autonomous_processing():
        while True:
            try:
                if email_agent.user_preferences.get('auto_reply_enabled', False):
                    result = email_agent.process_inbox()
                    print(f"Auto-processed {result.get('total_unread', 0)} emails, "
                          f"sent {result.get('auto_replies_sent', 0)} auto-replies")
                time.sleep(300)  # Check every 5 minutes
            except Exception as e:
                print(f"Auto-processing error: {e}")
                time.sleep(60)  # Wait 1 minute before retry
    
    # Start background thread
    thread = threading.Thread(target=autonomous_processing, daemon=True)
    thread.start()
    
    return jsonify({
        'success': True,
        'message': 'Autonomous processing started'
    })

if __name__ == '__main__':
    app.run(debug=app.config['DEBUG'])