import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from domain.entities.badge_notification import Notification
from ports.repositories import NotificationService


class EmailNotificationAdapter(NotificationService):

    def __init__(self, host: str, port: int, username: str, password: str):
        self._host = host
        self._port = port
        self._user = username
        self._pass = password

    def send(self, notif: Notification, recipient_email: str) -> bool:
        try:
            msg = MIMEMultipart("alternative")
            msg["Subject"] = "FitTrack Pro Reminder"
            msg["From"] = self._user
            msg["To"] = recipient_email

            body = MIMEText(notif.message, "plain")
            msg.attach(body)

            with smtplib.SMTP(self._host, self._port) as server:
                server.starttls()
                server.login(self._user, self._pass)
                server.sendmail(self._user, recipient_email, msg.as_string())

            notif.mark_sent()
            return True

        except smtplib.SMTPException:
            notif.mark_failed()
            return False
