# -*- coding: utf-8 -*-
u"""SMTP connection to send emails

:copyright: Copyright (c) 2018-2019 RadiaSoft LLC.  All Rights Reserved.
:license: http://www.apache.org/licenses/LICENSE-2.0.html
"""

from __future__ import absolute_import, division, print_function
from pykern.pkcollections import PKDict
import email
import smtplib


class SMTP(PKDict):
    def __init__(*args, **kwargs):
        super().__init__(*args, **kwargs)
        self.smtp_port = 587

    def send(self, subject, sender, recipient, body):
        if isinstance(sender, tuple):
            sender = f'{sender[0]} <{sender[1]}>'
        s = None
        try:
            # TODO(e-carlin): Understand line endings issue. EmailMessage
            # defaults to \n RFC expects \r\n
            # See https://docs.python.org/3/library/email.policy.html#email.policy.default
            m = email.message.EmailMessage()
            m['From'] = sender
            m['To'] = recipient
            m['Subject'] = subject
            m.set_content = body
            with smtplib.SMTP(self.smtp_server, self.smtp_port) as s:
                s.starttls()
                s.ehlo()
                s.login(self.smtp_user, self.smtp_password)
                s.send_message(m)
        finally:
            if s:
                s.quit()
