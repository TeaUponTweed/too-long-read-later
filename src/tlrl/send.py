import os
import smtplib
from contextlib import contextmanager
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Iterator, Optional


def create_message(
    subject: str, receiver: str, contents_html: str, sender: str
) -> MIMEMultipart:
    # Create message container - the correct MIME type is multipart/alternative.
    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = sender
    msg["To"] = receiver

    # Record the MIME type - text/html.
    # TODO can add style https://developers.google.com/gmail/design/css#example
    part1 = MIMEText(contents_html, "html", "utf-8")

    # Attach parts into message container
    msg.attach(part1)

    return msg


# Sending the email
@contextmanager
def _get_server() -> Iterator[smtplib.SMTP]:
    # Credentials
    username = os.environ["SMTP_UN"]
    password = os.environ["SMTP_PW"]
    server = smtplib.SMTP("smtp.sendgrid.net", 587)
    server.ehlo()
    server.starttls()
    server.login(username, password)
    try:
        yield server
    finally:
        server.quit()


def send_mesage(to: str, subject: str, msg: str, from_address: Optional[str] = None):
    if from_address is None:
        from_address = os.environ["EMAIL_ADDRESS"]
    if from_address == "TEST_DO_NOT_SEND":
        print("Not sending. from from_address == 'TEST_DO_NOT_SEND'")
        return
    msg = create_message(
        receiver=to, subject=subject, contents_html=msg, sender=from_address
    )
    with _get_server() as server:
        server.sendmail(from_address, to, msg.as_string())
