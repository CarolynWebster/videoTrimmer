"""Email notifications for video trimming app"""

import os

import smtplib

from email.mime.text import MIMEText

# get email info
gmail_user = os.environ['GMAIL_USER']
gmail_password = os.environ['GMAIL_PASS']

def create_message(sender, to, subject, message_text):
    """Create a message for an email.

    Args:
    sender: Email address of the sender.
    to: Email address of the receiver.
    subject: The subject of the email message.
    message_text: The text of the email message.

    Returns:
    An object containing a base64url encoded email object.
    """

    # creates a message to be sent
    message = MIMEText(message_text, 'html')
    message['to'] = to
    message['from'] = sender
    message['subject'] = subject

    return message.as_string()


def send_email(recipient, file_url):
    """Sends user a notification email"""

    # set up email content
    sent_from = gmail_user
    to = recipient
    subject = 'Update from Cut To The Point'
    body = 'Hey, Your video is ready! Here is a link <a href=http://localhost:5000{}>to download</a>'.format(file_url)

    # create a message
    email_text = create_message(sent_from, to, subject, body)

    # try sending it
    try:
        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.ehlo()
        server.login(gmail_user, gmail_password)
        server.sendmail(sent_from, to, email_text)
        server.close()

        print 'Email sent!'
    except:
        print 'Something went wrong...'
