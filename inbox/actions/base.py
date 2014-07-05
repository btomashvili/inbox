from inbox.models.session import session_scope
from inbox.models import Account, SpoolMessage
from inbox.sendmail.base import generate_attachments
from inbox.sendmail.message import create_email, Recipients

from inbox.actions.backends import module_registry


class ActionError(Exception):
    pass


def archive(account_id, thread_id):
    """Sync an archive action back to the backend. """
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)

        set_remote_archived = module_registry[account.provider]. \
            set_remote_archived
        set_remote_archived(account, thread_id, True, db_session)


def unarchive(account_id, thread_id):
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)

        set_remote_archived = module_registry[account.provider]. \
            set_remote_archived
        set_remote_archived(account, thread_id, False, db_session)


def star(account_id, thread_id):
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)

        set_remote_starred = module_registry[account.provider]. \
            set_remote_starred
        set_remote_starred(account, thread_id, True, db_session)


def unstar(account_id, thread_id):
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)

        set_remote_starred = module_registry[account.provider]. \
            set_remote_starred
        set_remote_starred(account, thread_id, False, db_session)


def mark_unread(account_id, thread_id):
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)
        set_remote_unread = module_registry[account.provider]. \
            set_remote_unread
        set_remote_unread(account, thread_id, True, db_session)


def mark_read(account_id, thread_id):
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)
        set_remote_unread = module_registry[account.provider]. \
            set_remote_unread
        set_remote_unread(account, thread_id, False, db_session)


def mark_spam(account_id, thread_id):
    raise NotImplementedError


def unmark_spam(account_id, thread_id):
    raise NotImplementedError


def mark_trash(account_id, thread_id):
    raise NotImplementedError


def unmark_trash(account_id, thread_id):
    raise NotImplementedError


def save_draft(account_id, message_id):
    """ Sync a new/updated draft back to the remote backend. """
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)
        message = db_session.query(SpoolMessage).get(message_id)

        recipients = Recipients(message.to_addr, message.cc_addr,
                                message.bcc_addr)
        attachments = generate_attachments(message.attachments)
        mimemsg = create_email(account.sender_name, account.email_address,
                               message.inbox_uid, recipients, message.subject,
                               message.sanitized_body, attachments)

        remote_save_draft = module_registry[account.provider].remote_save_draft
        remote_save_draft(account, account.drafts_folder.name,
                          mimemsg.to_string(), message.created_date)

        if message.parent_draft:
            return delete_draft(account_id, message.parent_draft.inbox_uid)


def delete_draft(account_id, inbox_uid):
    """ Delete a draft from the remote backend. """
    with session_scope() as db_session:
        account = db_session.query(Account).get(account_id)
        remote_delete_draft = \
            module_registry[account.provider].remote_delete_draft
        remote_delete_draft(account, account.drafts_folder.name, inbox_uid,
                            db_session)
