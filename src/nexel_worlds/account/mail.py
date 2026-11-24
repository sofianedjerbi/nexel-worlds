"""The one mail the account service sends: your code. Plain SMTP, so the same lines reach Mailpit on this machine
(nothing leaves it) or a real mail service later: only the address and the password change."""

import smtplib
from email.message import EmailMessage

from .store import CODE_S


class Mailer:
    def __init__(self, host: str, port: int, sender: str, user: str = "", password: str = "", tls: bool = False):
        self.host, self.port, self.sender, self.user, self.password, self.tls = host, port, sender, user, password, tls

    def send_code(self, to: str, code: str):
        m = EmailMessage()
        m["From"], m["To"], m["Subject"] = self.sender, to, f"{code} is your Nexel Worlds code"
        m.set_content(f"Your code is {code}\n\nType it on the first screen to wake up. It works for {CODE_S // 60} minutes, once.\n"
                      "If you did not ask for it, do nothing: nobody gets in without it.\n")
        with smtplib.SMTP(self.host, self.port, timeout=10) as s:
            if self.tls:
                s.starttls()
            if self.user:
                s.login(self.user, self.password)
            s.send_message(m)
