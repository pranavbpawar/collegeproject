#!/usr/bin/env python3
"""
TBAPS - Local SMTP Test Script
This script connects to your local Postfix installation (localhost:25)
and attempts to send a test email. Use this to verify that Postfix is running
and accepting connections before testing via the web interface.
"""

import smtplib
from email.message import EmailMessage
import sys
import os

# Load basic values from .env if present (we only need testing values)
from dotenv import load_dotenv
load_dotenv(".env")

SMTP_HOST = os.getenv("SMTP_HOST", "127.0.0.1")
SMTP_PORT = int(os.getenv("SMTP_PORT", 25))
FROM_EMAIL = os.getenv("EMAIL_FROM_ADDRESS", "noreply@tbaps.local")

def count_args():
    if len(sys.argv) < 2:
        print("Usage: python3 test-smtp.py <destination_email>")
        print("Example: python3 test-smtp.py test-xxxxx@srv1.mail-tester.com")
        sys.exit(1)
    return sys.argv[1]

def send_test_email(to_email):
    print(f"Connecting to local SMTP server at {SMTP_HOST}:{SMTP_PORT}...")
    
    msg = EmailMessage()
    msg.set_content(f"""\
Hello! 

If you are reading this email, it means your local Postfix installation on TBAPS is working correctly!

Please check your Mail-Tester score to verify your SPF and DKIM DNS records.

Best regards,
TBAPS System
""")
    
    msg['Subject'] = 'TBAPS Local Postfix Test'
    msg['From'] = FROM_EMAIL
    msg['To'] = to_email

    try:
        # Connect to local postfix
        server = smtplib.SMTP(SMTP_HOST, SMTP_PORT)
        server.set_debuglevel(1)  # Print communication with SMTP server
        
        print(f"\nSending email from {FROM_EMAIL} to {to_email}...")
        server.send_message(msg)
        server.quit()
        
        print("\n✅ Email successfully injected into the local Postfix queue!")
        print("Note: This does not guarantee delivery to the inbox. Check mail-tester.com for your score.")
        
    except ConnectionRefusedError:
        print(f"\n❌ Connection Refused! Is Postfix running on {SMTP_HOST}:{SMTP_PORT}?")
        print("Hint: Run 'sudo systemctl status postfix' or 'sudo bash scripts/setup-postfix.sh'")
    except Exception as e:
        print(f"\n❌ Failed to send email: {str(e)}")

if __name__ == "__main__":
    target_email = count_args()
    send_test_email(target_email)
