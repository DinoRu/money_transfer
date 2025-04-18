from fastapi_mail import  ConnectionConfig, MessageSchema, FastMail, MessageType
from pydantic import EmailStr

import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from src.config import settings


smtp_server = "smtp.mailmug.net"
port = 2525
login = "3ilpqpzrmlczkvjh"
password = "059l7cnworh775rb"


mail_conf = ConnectionConfig(
    MAIL_USERNAME = settings.MAIL_USERNAME,
    MAIL_PASSWORD = settings.MAIL_PASSWORD,
    MAIL_FROM = settings.MAIL_FROM,
    MAIL_PORT = settings.MAIL_PORT,
    MAIL_SERVER = settings.MAIL_SERVER,
    MAIL_FROM_NAME= settings.MAIL_FROM_NAME,
    MAIL_STARTTLS = True,
    MAIL_SSL_TLS = False,
    USE_CREDENTIALS = True,
    VALIDATE_CERTS = True
)


mail = FastMail(
    config=mail_conf
)

def create_message(
        recipients: list[EmailStr], subject: str, body: str
):
    messages = MessageSchema(
        recipients=recipients,
        subject=subject, body=body,
        subtype=MessageType.html
    )

    return messages