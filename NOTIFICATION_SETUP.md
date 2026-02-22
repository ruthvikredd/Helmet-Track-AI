# Helmettrack SMS/Notification Setup - Your Personal Guide

## Current Issue
✓ **FIXED**: System now sends alerts **only to YOU** (Admin), not to strangers
✓ **OPTIONS**: Twilio SMS (paid) OR Email (free)

---

## **OPTION 1: Use Email Alerts (FREE) ⭐ RECOMMENDED**

### Why Email?
- ✓ Completely FREE
- ✓ No monthly charges
- ✓ No trial limitations
- ✓ Works instantly
- ✓ No API credits needed

### Setup (5 minutes):

#### Step 1: Create Gmail App Password
1. Go to https://myaccount.google.com/
2. Click **Security** (left menu)
3. Enable **2-Step Verification** (if not already enabled)
4. Scroll down to **App passwords**
5. Select "Mail" and "Windows Computer"
6. Copy the 16-character password generated

#### Step 2: Update `.env` file
Replace the Twilio section with:

```
# ========================================
# EMAIL ALERT CONFIGURATION (FREE)
# ========================================
ADMIN_EMAIL=your_gmail@gmail.com
EMAIL_PASSWORD=xxxx-xxxx-xxxx-xxxx
SEND_EMAIL_ENABLED=True
```

#### Step 3: Update app.py to use email
```python
# At the top of app.py, add:
from notification_email import send_violation_email

# In the violation detection section (where SMS was), replace with:
if SEND_EMAIL_ENABLED:
    result = send_violation_email(ADMIN_EMAIL, violation_details)
    if result['success']:
        print("✓ Alert email sent successfully!")
    else:
        print(f"✗ Email failed: {result['error']}")
```

---

## **OPTION 2: Use Twilio SMS (Paid - $0.0075 per SMS)**

### If you decide to upgrade Twilio:

#### Step 1: Add Payment Method to Twilio
1. Go to https://www.twilio.com/console/billing/overview
2. Click **Billing**
3. Add **Credit Card**
4. Confirm payment details

#### Step 2: Update `.env` with Twilio credentials
```
TWILIO_ACCOUNT_SID=ACxxxxxxxxxxxxxxxxxxxxxxxxxxxxxx
TWILIO_AUTH_TOKEN=your_32_char_token_here
TWILIO_PHONE_NUMBER=+1234567890
ADMIN_PHONE_NUMBER=+919876543210
SEND_SMS_ENABLED=True
```

#### Cost Calculation:
- Cost per SMS: **₹0.60** (approximately)
- If 10 violations/day: **₹6/day = ₹180/month**
- Free trial: Covered until credits run out

---

## **How It Works Now**

### Detection Flow:
```
1. Upload Image → /predict_image
2. YOLO detects no helmet
3. Saves to database
4. Sends **ONE** alert to YOU (admin)
5. You are notified
```

### Before (Wrong):
```
Violation detected → Sends to ALL users in database ❌
```

### Now (Fixed):
```
Violation detected → Sends ONLY to you ✓
```

---

## **Testing Without SMS/Email**

You can test violations without sending alerts:

```python
# In .env file:
SEND_SMS_ENABLED=False    # Disables SMS sending
SEND_EMAIL_ENABLED=False  # Disables email sending
```

Violations will be detected and saved, but no alerts sent.

---

## **File Changes Made**

1. **app.py** - Updated to send to admin only
2. **.env** - Added admin configuration
3. **notification_email.py** - Alternative email system

---

## **Quick Start Checklist**

### For EMAIL (Recommended):
- [ ] Go to https://myaccount.google.com/security
- [ ] Create Gmail App Password
- [ ] Update `.env` with email and password
- [ ] Update `app.py` to use `send_violation_email()`
- [ ] Test by uploading an image
- [ ] Check your email inbox

### For SMS:
- [ ] Go to https://www.twilio.com/console/billing
- [ ] Add payment method
- [ ] Update `.env` with Twilio credentials
- [ ] Update `ADMIN_PHONE_NUMBER` in `.env`
- [ ] System automatically sends SMS on violation

---

## **Troubleshooting**

### Email not arriving?
1. Check spam folder
2. Check if 2-step verification is enabled
3. Check if App Password was copied correctly
4. Run test: `python test_twilio_setup.py`

### SMS failing?
1. Verify Twilio account has payment method
2. Check Account SID and Auth Token are correct
3. Check phone number format: `+919876543210`
4. Check free credits haven't expired

---

## **Questions?**

- **Twilio costs too much?** → Use Email (FREE)
- **Want SMS anyway?** → Add payment to Twilio account
- **Want to test?** → Set `SEND_SMS_ENABLED=False`
