from inbox.sendmail.base import generate_attachments, SendError
from inbox.sendmail.postel import SMTPClient
from inbox.sendmail.gmail.message import create_gmail_email, create_gmail_reply


class GmailSMTPClient(SMTPClient):
    """ SMTPClient for Gmail. """
    def _send_mail(self, db_session, message, smtpmsg):
        """Send the email message."""
        # Send it using SMTP:
        try:
            return self._send(smtpmsg.recipients, smtpmsg.msg)
        except SendError as e:
            self.log.error(str(e))
            raise

    def send_new(self, db_session, draft, recipients):
        """
        Send a previously created + saved draft email from this user account.

        """
        inbox_uid = draft.inbox_uid
        subject = draft.subject
        body = draft.sanitized_body
        attachments = generate_attachments(draft.attachments)

        smtpmsg = create_gmail_email(self.sender_name, self.email_address,
                                     inbox_uid, recipients, subject, body,
                                     attachments)
        return self._send_mail(db_session, draft, smtpmsg)

    def send_reply(self, db_session, draft, recipients):
        """
        Send a previously created + saved draft email reply from this user
        account.

        """
        inbox_uid = draft.inbox_uid
        subject = draft.subject
        body = draft.sanitized_body
        attachments = generate_attachments(draft.attachments)

        smtpmsg = create_gmail_reply(self.sender_name, self.email_address,
                                     draft.in_reply_to, draft.references,
                                     inbox_uid, recipients, subject, body,
                                     attachments)

        return self._send_mail(db_session, draft, smtpmsg)
