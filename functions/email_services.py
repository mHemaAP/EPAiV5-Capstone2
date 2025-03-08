import os
import smtplib
import pytz
from datetime import datetime
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import logging

def ai_send_email(subject: str, body: str)-> None:
    """
    Sends an email with the given subject and body using Gmail's SMTP server.

    The function retrieves the email password from an environment variable 
    (`EMAIL_PASSWORD`) for security reasons. 

    Args:
        subject (str): The subject of the email.
        body (str): The body/content of the email.

    Returns:
        None
        
    Raises:
        ValueError: If the EMAIL_PASSWORD environment variable is not set.
        Exception: If an error occurs while sending the email.
    """
    logging.info(f"Starting email send process for subject: {subject}")
    
    # Load email credentials from environment variables
    EMAIL_ADDRESS = "haptestmail9@gmail.com"
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")  # Fetch from environment variable

    if not EMAIL_PASSWORD:
        logging.error("EMAIL_PASSWORD environment variable is not set")
        raise ValueError("EMAIL_PASSWORD environment variable is not set.")

    logging.info(f"Attempting to send email from: {EMAIL_ADDRESS}")
    # logging.info(f"EMAIL_PASSWORD (partial): {EMAIL_PASSWORD[4]}****")

    # Create the email message
    msg = MIMEText(body)
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = "studentmhap@gmail.com"
    msg["Subject"] = subject

    # Attempt to send the email securely
    try:
        # with smtplib.SMTP("smtp.gmail.com", 465) as server:
        server = smtplib.SMTP_SSL("smtp.gmail.com", 465)
        logging.info("Connecting to SMTP server (SSL)...")

        # logging.info("Running ehlo...")             
        # server.ehlo()  # Identify with the server

        # logging.info("Starting TLS...")
        # server.starttls()

        # logging.info("Running ehlo again...")            
        # server.ehlo()  # Identify with the server

        server.login(EMAIL_ADDRESS, EMAIL_PASSWORD) # Authenticate with SMTP server
        logging.info("Logged in successfully")
        
        server.sendmail(EMAIL_ADDRESS, "studentmhap@gmail.com", msg.as_string()) # Send email
        logging.info("Email sent successfully!")
        
    except smtplib.SMTPAuthenticationError as e:
        logging.error(f"Authentication failed: {e}")
        raise
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}") # Print error message if sending fails
        raise
    finally:
        if 'server' in locals():
            server.quit()

def ai_send_calendar_invite(subject: str, body: str, start_time: str, end_time: str, timezone: str):
    """
    Sends a calendar invite (ICS file) via email with proper time zone handling.

    Parameters:
        subject (str): The subject of the calendar event.
        body (str): The description of the event.
        start_time (str): Event start time in `YYYY-MM-DD HH:MM:SS` format (local time).
        end_time (str): Event end time in `YYYY-MM-DD HH:MM:SS` format (local time).
        timezone (str): The time zone of the event (e.g., "Asia/Kolkata", "America/New_York").

    Raises:
        ValueError: If EMAIL_PASSWORD is not set or invalid timezone.
        Exception: If email sending fails.
    """

    # Load email credentials
    EMAIL_ADDRESS = "haptestmail9@gmail.com"
    EMAIL_PASSWORD = os.getenv("EMAIL_PASSWORD")

    if not EMAIL_PASSWORD:
        raise ValueError("EMAIL_PASSWORD environment variable is not set.")

    to_email = EMAIL_ADDRESS  # Sending to self

    # Convert local time to UTC
    try:
        local_tz = pytz.timezone(timezone)  # Get the time zone object
    except pytz.UnknownTimeZoneError:
        raise ValueError(f"Invalid time zone: {timezone}")

    def convert_to_utc(dt_str):
        """Converts a datetime string from local time to UTC in iCalendar format (YYYYMMDDTHHMMSSZ)."""
        local_time = datetime.strptime(dt_str, "%Y-%m-%d %H:%M:%S")  # Parse input string
        local_time = local_tz.localize(local_time)  # Assign local timezone
        utc_time = local_time.astimezone(pytz.utc)  # Convert to UTC
        return utc_time.strftime("%Y%m%dT%H%M%SZ")  # Return iCalendar format

    start_time_utc = convert_to_utc(start_time)
    end_time_utc = convert_to_utc(end_time)

    # Create calendar invite (.ics file content)
    ics_content = f"""BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//AI Invite//Example//EN
BEGIN:VEVENT
UID:1234567890@example.com
DTSTAMP:{start_time_utc}
DTSTART:{start_time_utc}
DTEND:{end_time_utc}
SUMMARY:{subject}
DESCRIPTION:{body}
LOCATION:Online
STATUS:CONFIRMED
END:VEVENT
END:VCALENDAR
"""

    # Create email message with attachment
    msg = MIMEMultipart()
    msg["From"] = EMAIL_ADDRESS
    msg["To"] = to_email
    msg["Subject"] = subject

    # Add email body
    msg.attach(MIMEText(body, "plain"))

    # Attach ICS file
    ics_attachment = MIMEText(ics_content, "calendar")
    ics_attachment.add_header("Content-Disposition", "attachment", filename="invite.ics")
    msg.attach(ics_attachment)

    # Send email
    try:
        with smtplib.SMTP_SSL("smtp.gmail.com", 465) as server:
            # server.starttls()
            server.login(EMAIL_ADDRESS, EMAIL_PASSWORD)
            server.sendmail(EMAIL_ADDRESS, to_email, msg.as_string())
        logging.info("Calendar invite sent successfully!")
    except Exception as e:
        logging.info(f"Error: {e}")


if __name__ == "__main__":
    # Example usage: Sending an invite in IST (Indian Standard Time)
    subject = "Team Meeting"
    body = "Join us for a team meeting."
    start_time = "2025-03-11 15:30:00"  # Local time in IST
    end_time = "2025-03-11 16:00:00"    # One-hour meeting
    timezone = "Asia/Kolkata"  # Specify the time zone

    ai_send_calendar_invite(subject, body, start_time, end_time, timezone)
