"""
Alternative: Send Violation Alerts via Email Instead of SMS
This is FREE and doesn't require Twilio
"""

from flask import Flask, render_template, request, redirect, session
from db_connection import get_connection
from detection.realtime import run_camera_detection
from detection.video_detect import detect_video
from ultralytics import YOLO
import os
import cv2
from datetime import datetime
from dotenv import load_dotenv
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

# Load environment variables
load_dotenv()

# Email Configuration (FREE)
ADMIN_EMAIL = os.environ.get('ADMIN_EMAIL', 'your_email@gmail.com')
EMAIL_PASSWORD = os.environ.get('EMAIL_PASSWORD', 'your_app_password')
SEND_EMAIL_ENABLED = os.environ.get('SEND_EMAIL_ENABLED', 'True').lower() == 'true'

def send_violation_email(admin_email, violation_details):
    """
    Send violation alert via email (FREE alternative to SMS)
    
    Args:
        admin_email (str): Admin email address
        violation_details (dict): Violation information
    
    Returns:
        dict: Success/failure response
    """
    try:
        # Gmail SMTP Configuration
        smtp_server = "smtp.gmail.com"
        smtp_port = 587
        
        # Create message
        message = MIMEMultipart()
        message['From'] = ADMIN_EMAIL
        message['To'] = admin_email
        message['Subject'] = "🚨 HELMET VIOLATION DETECTED - HELMETTRACK ALERT"
        
        timestamp = violation_details.get('timestamp', 'N/A')
        fine_amount = violation_details.get('fine_amount', 500)
        
        body = f"""
HELMET VIOLATION ALERT
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A helmet violation has been detected in your traffic zone.

Details:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
📍 Timestamp: {timestamp}
💰 Fine Amount: ₹{fine_amount}
⚠️  Status: VIOLATION RECORDED

Action Required:
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
1. Login to Helmettrack dashboard
2. Review the violation details
3. Take necessary action

Traffic Safety Division
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

This is an automated alert from Helmettrack System.
        """
        
        message.attach(MIMEText(body, 'plain'))
        
        # Send email via Gmail
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls()
            server.login(ADMIN_EMAIL, EMAIL_PASSWORD)
            server.send_message(message)
        
        return {
            'success': True,
            'message': f'Email sent to {admin_email}',
            'email': admin_email
        }
    
    except Exception as e:
        print(f"Email Error: {str(e)}")
        return {
            'success': False,
            'error': str(e),
            'email': admin_email
        }


# EXAMPLE USAGE in your app.py:
"""
# When a violation is detected:
if SEND_EMAIL_ENABLED:
    result = send_violation_email(ADMIN_EMAIL, violation_details)
    if result['success']:
        print("✓ Alert email sent successfully!")
    else:
        print(f"✗ Email failed: {result['error']}")
"""
