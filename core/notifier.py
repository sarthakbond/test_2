import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import config

def send_alert_email(recipient_email: str, person_name: str, video_name: str, summary: str):
    """
    Sends an email alert using Python's built-in smtplib.
    Uses SMTP_SSL for secure connection to Gmail.
    """
    if not recipient_email:
        print("[SWARAKSHA Notifier] No email provided for this person. Skipping email alert.")
        return False
        
    if config.SMTP_PASSWORD == "ENTER_YOUR_APP_PASSWORD_HERE":
        print("[SWARAKSHA Notifier] Email alert skipped: SMTP_PASSWORD is not configured in config.py")
        return False
        
    try:
        msg = MIMEMultipart()
        msg['From'] = config.SMTP_SENDER
        msg['To'] = recipient_email
        msg['Subject'] = f"🚨 SWARAKSHA ALERT: High Risk Content Detected for {person_name}"
        
        body = f"""
Hello,

SWARAKSHA has detected HIGH RISK manipulated content containing your identity.
All three forensic flags (Identity Match, AI Generation, Context Discrepancy) were triggered.

Video Name: {video_name}
Summary: {summary}

Please log into the SWARAKSHA dashboard to review the evidence.

Best,
SWARAKSHA Automated System
        """
        msg.attach(MIMEText(body, 'plain'))
        
        server = smtplib.SMTP_SSL(config.SMTP_SERVER, config.SMTP_PORT)
        server.login(config.SMTP_SENDER, config.SMTP_PASSWORD)
        server.send_message(msg)
        server.quit()
        
        print(f"[SWARAKSHA Notifier] Email alert sent successfully to {recipient_email}")
        return True
    except Exception as e:
        print(f"[SWARAKSHA Notifier] Failed to send email alert: {e}")
        return False
