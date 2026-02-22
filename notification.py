"""
SMS Notification Module
Handles sending SMS alerts when helmet violations are detected
"""

from twilio.rest import Client
import os

# Twilio Configuration
# Get these credentials from your Twilio account at https://www.twilio.com/console
TWILIO_ACCOUNT_SID = os.environ.get('TWILIO_ACCOUNT_SID', 'your_account_sid_here')
TWILIO_AUTH_TOKEN = os.environ.get('TWILIO_AUTH_TOKEN', 'your_auth_token_here')
TWILIO_PHONE_NUMBER = os.environ.get('TWILIO_PHONE_NUMBER', '+1234567890')  # Your Twilio phone number


def send_violation_sms(phone_number, violation_details):
    """
    Send SMS notification for helmet violation
    
    Args:
        phone_number (str): Phone number to send SMS to (format: +country_code_number)
        violation_details (dict): Dictionary containing violation information
            - timestamp: When the violation was detected
            - fine_amount: Amount of fine
            - location: Where violation was detected (optional)
    
    Returns:
        dict: Response containing success status and message ID or error
    """
    try:
        # Initialize Twilio client
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        
        # Format phone number if needed
        if not phone_number.startswith('+'):
            phone_number = '+91' + phone_number  # Default to India (+91)
        
        # Construct violation message
        timestamp = violation_details.get('timestamp', 'N/A')
        fine_amount = violation_details.get('fine_amount', 500)
        
        message_body = f"""
HELMET VIOLATION ALERT
━━━━━━━━━━━━━━━━━━━━━
A helmet violation has been detected.

📍 Timestamp: {timestamp}
💰 Fine Amount: ₹{fine_amount}
⚠️  Action Required: Please pay the fine at your nearest traffic office.

For more details, login to Helmettrack dashboard.

Traffic Safety Division
        """.strip()
        
        # Send SMS via Twilio
        message = client.messages.create(
            body=message_body,
            from_=TWILIO_PHONE_NUMBER,
            to=phone_number
        )
        
        return {
            'success': True,
            'message_id': message.sid,
            'status': message.status,
            'phone_number': phone_number
        }
    
    except Exception as e:
        print(f"SMS Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'phone_number': phone_number
        }


def send_bulk_violation_sms(phone_numbers, violation_details):
    """
    Send SMS to multiple phone numbers for a violation
    
    Args:
        phone_numbers (list): List of phone numbers to notify
        violation_details (dict): Violation information
    
    Returns:
        list: List of response dictionaries for each SMS
    """
    results = []
    for phone_number in phone_numbers:
        result = send_violation_sms(phone_number, violation_details)
        results.append(result)
    
    return results


def validate_phone_number(phone_number):
    """
    Validate phone number format
    
    Args:
        phone_number (str): Phone number to validate
    
    Returns:
        tuple: (is_valid, formatted_number)
    """
    import re
    
    # Remove spaces, hyphens, and parentheses
    cleaned = re.sub(r'[\s\-\(\)]', '', phone_number)
    
    # Check if starts with + or country code
    if cleaned.startswith('+'):
        pass
    elif cleaned.startswith('91'):  # India country code
        cleaned = '+' + cleaned
    elif len(cleaned) == 10:  # Assuming 10-digit number (India)
        cleaned = '+91' + cleaned
    else:
        return False, None
    
    # Validate length (10-15 digits after country code)
    digits = re.sub(r'\D', '', cleaned)
    if len(digits) < 10 or len(digits) > 15:
        return False, None
    
    return True, cleaned


def test_sms_connection():
    """
    Test if Twilio credentials are configured correctly
    
    Returns:
        bool: True if connection successful, False otherwise
    """
    try:
        client = Client(TWILIO_ACCOUNT_SID, TWILIO_AUTH_TOKEN)
        account = client.api.accounts(TWILIO_ACCOUNT_SID).fetch()
        print(f"✓ Twilio connection successful - Account: {account.friendly_name}")
        return True
    except Exception as e:
        print(f"✗ Twilio connection failed: {str(e)}")
        return False
