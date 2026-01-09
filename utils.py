import bcrypt
import random
import smtplib
import ssl
from email.message import EmailMessage
import os

def generate_otp():
    return f"{random.randint(100000, 999999)}"

def send_otp_email(receiver_email: str, code: str):
    msg = EmailMessage()
    msg.set_content(f"Your Nebula Nexus verification code is: {code}")
    msg['Subject'] = 'Verify your Stellar Account'
    msg['From'] = "nebulanexus.system@gmail.com"
    msg['To'] = receiver_email

    smtp_server = "smtp.gmail.com"
    smtp_port = 587
    sender_email = "nebulanexus.system@gmail.com"
    
    # Replace this with your actual 16-character App Password from Google
    app_password = os.getenv("MAIL_APP_PASSWORD")

    # 3. Security context for the connection
    context = ssl.create_default_context()

    try:
        # Use 'with' to ensure the connection closes automatically
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            server.starttls(context=context)  # Secure the connection
            server.login(sender_email, app_password)
            server.send_message(msg)
            print(f"--- EMAIL SENT TO {receiver_email}: CODE IS {code} ---")
    except Exception as e:
        print(f"Error: {e}")
    
# takes raw password -> returns an hashed one (#####)
def hash_password(password: str) -> str:
    return bcrypt.hashpw(password=password.encode(), salt=bcrypt.gensalt())

# checks the raw password with the respected hashed one
def verify_password(password: str, hashed_password: str) -> bool:
    return bcrypt.checkpw(password=password.encode(), hashed_password=hashed_password.encode())