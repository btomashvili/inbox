""" Operations for syncing back local datastore changes to Yahoo.

See imap.py for notes about implementation.
"""
from sqlalchemy.orm import joinedload

from inbox.actions.backends.imap import uidvalidity_cb, syncback_action
from inbox.models.backends.imap import ImapThread, ImapUid
from inbox.models.message import Message, SpoolMessage
import pdb

PROVIDER = 'yahoo'

__all__ = ['set_remote_archived', 'set_remote_starred', 'set_remote_unread',
           'remote_save_draft', 'remote_delete_draft']


def set_remote_archived(account, thread_id, archived, db_session):
    assert account.archive_folder, "account {} has no detected archive folder"\
        .format(account.id)
    if archived:
        return remote_move(account, thread_id, account.inbox_folder,
                           account.archive_folder, db_session)
    else:
        return remote_move(account, thread_id, account.archive_folder,
                           account.inbox_folder, db_session)


def set_remote_starred(account, thread_id, starred, db_session):
    def fn(account, db_session, crispin_client):
        uids = []
        # FIXME @karim: We can probably get away with a lighter
        # query.
        thread = db_session.query(ImapThread).options(
            joinedload("messages").joinedload("imapuids"))\
            .filter_by(id=thread_id).one()
        import pdb
        pdb.set_trace()

        for msg in thread.messages:
            uids.extend([uid.msg_uid for uid in msg.imapuids])

        crispin_client.set_starred(uids, starred)

    return syncback_action(fn, account, account.inbox_folder.name, db_session)


def set_remote_unread(account, thread_id, unread, db_session):
    def fn(account, db_session, crispin_client):
        uids = []
        thread = db_session.query(ImapThread).options(
            joinedload("messages").joinedload("imapuids"))\
            .filter_by(id=thread_id).one()

        for msg in thread.messages:
            uids.extend([uid.msg_uid for uid in msg.imapuids])
        crispin_client.set_unread(uids, unread)

    return syncback_action(fn, account, account.inbox_folder.name, db_session)


def remote_move(account, thread_id, from_folder, to_folder, db_session):
    if from_folder == to_folder:
        return

    def fn(account, db_session, crispin_client):
        folders = crispin_client.folder_names()

        if from_folder not in folders.values() and \
           from_folder not in folders["extra"]:
                raise Exception("Unknown from_folder '{}'".format(from_folder))

        if to_folder not in folders.values() and \
           to_folder not in folders["extra"]:
                raise Exception("Unknown to_folder '{}'".format(to_folder))

        crispin_client.select_folder(from_folder, uidvalidity_cb)
        uids = []
        thread = db_session.query(ImapThread).options(
            joinedload("messages").joinedload("imapuids"))\
            .filter_by(id=thread_id).one()

        for msg in thread.messages:
            uids.extend([uid.msg_uid for uid in msg.imapuids])

        crispin_client.copy_uids(uids, to_folder)
        crispin_client.delete_uids(uids)

    return syncback_action(fn, account, from_folder, db_session)


def remote_copy(account, thread_id, from_folder, to_folder, db_session):
    """ NOTE: We are not planning to use this function yet since Inbox never
        modifies Gmail IMAP labels.
    """
    if from_folder == to_folder:
        return

    def fn(account, db_session, crispin_client):
        uids = []
        folders = crispin_client.folder_names()

        if from_folder not in folders.values() and \
           from_folder not in folders["extra"]:
                raise Exception("Unknown from_folder '{}'".format(from_folder))

        if to_folder not in folders.values() and \
           to_folder not in folders["extra"]:
                raise Exception("Unknown to_folder '{}'".format(to_folder))


        thread = db_session.query(ImapThread).options(
            joinedload("messages").joinedload("imapuids"))\
            .filter_by(id=thread_id).one()

        for msg in thread.messages:
            uids.extend([uid.msg_uid for uid in msg.imapuids])

        crispin_client.copy_uids(uids, to_folder)

    return syncback_action(fn, account, from_folder, db_session)


def remote_delete(account, thread_id, folder_name, db_session):
    def fn(account, db_session, crispin_client):
        uids = []

        thread = db_session.query(ImapThread).options(
            joinedload("messages").joinedload("imapuids"))\
            .filter_by(id=thread_id).one()

        for msg in thread.messages:
            uids.extend([uid.msg_uid for uid in msg.imapuids])

        crispin_client.delete_uids(uids)

    return syncback_action(fn, account, folder_name, db_session)

# FIXME @karim: Why do we pass folder_name to the function if we just use it
# to check it's equal to "Drafts"?
def remote_save_draft(account, folder_name, message, db_session, date=None):
    def fn(account, db_session, crispin_client):
        assert folder_name == crispin_client.folder_names()['drafts']
        crispin_client.save_draft(message, date)

    return syncback_action(fn, account, folder_name, db_session)


def remote_delete_draft(account, folder_name, inbox_uid, db_session):
    def fn(account, db_session, crispin_client):
        assert folder_name == crispin_client.folder_names()['drafts']
        # FIXME @karim: forgot to make this work.
        db_session.query(SpoolMessage).options(joinedload("imapuids")).filter_by(public_id=inbox_uid).one()
        crispin_client.delete_draft(inbox_uid)

    return syncback_action(fn, account, folder_name, db_session)
