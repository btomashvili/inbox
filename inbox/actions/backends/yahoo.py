""" Operations for syncing back local datastore changes to Yahoo.

See imap.py for notes about implementation.
"""
from sqlalchemy.orm import joinedload

from inbox.actions.backends.imap import uidvalidity_cb, syncback_action
from inbox.models.backends.imap import ImapThread

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
    raise NotImplementedError("Yahoo has no 'starred' equivalent")


def set_remote_unread(account, thread_id, unread, db_session):
    def fn(account, db_session, crispin_client):
        uids = []
        thread = db_session.query(ImapThread).options(
            joinedload('messages').load_only('id')
            .joinedload('imapuids').load_only('id'))\
            .filter_by(id=thread_id).one()
        for msg in thread.messages:
            uids.extend(msg.imapuids)
        crispin_client.set_unread(uids, unread)

    return syncback_action(fn, account, account.all_folder.name, db_session)


def remote_move(account, thread_id, from_folder, to_folder, db_session):
    if from_folder == to_folder:
        return

    def fn(account, db_session, crispin_client):
        inbox_folder = crispin_client.folder_names()['inbox']
        all_folder = crispin_client.folder_names()['all']
        if from_folder == inbox_folder:
            if to_folder == all_folder:
                return _archive(thread_id, crispin_client)
            else:
                g_thrid = _get_g_thrid(account.namespace.id, thread_id,
                                       db_session)
                _archive(g_thrid, crispin_client)
                crispin_client.add_label(g_thrid, to_folder)
        elif from_folder in crispin_client.folder_names()['labels']:
            if to_folder in crispin_client.folder_names()['labels']:
                g_thrid = _get_g_thrid(account.namespace.id, thread_id,
                                       db_session)
                crispin_client.add_label(g_thrid, to_folder)
            elif to_folder == inbox_folder:
                g_thrid = _get_g_thrid(account.namespace.id, thread_id,
                                       db_session)
                crispin_client.copy_thread(g_thrid, to_folder)
            elif to_folder != all_folder:
                raise Exception("Should never get here! to_folder: {}"
                                .format(to_folder))
            crispin_client.select_folder(crispin_client.folder_names()['all'],
                                         uidvalidity_cb)
            crispin_client.remove_label(g_thrid, from_folder)
            # do nothing if moving to all mail
        elif from_folder == all_folder:
            g_thrid = _get_g_thrid(account.namespace.id, thread_id, db_session)
            if to_folder in crispin_client.folder_names()['labels']:
                crispin_client.add_label(g_thrid, to_folder)
            elif to_folder == inbox_folder:
                crispin_client.copy_thread(g_thrid, to_folder)
            else:
                raise Exception("Should never get here! to_folder: {}"
                                .format(to_folder))
        else:
            raise Exception("Unknown from_folder '{}'".format(from_folder))

    return syncback_action(fn, account, from_folder, db_session)


def remote_copy(account, thread_id, from_folder, to_folder, db_session):
    """ NOTE: We are not planning to use this function yet since Inbox never
        modifies Gmail IMAP labels.
    """
    if from_folder == to_folder:
        return

    def fn(account, db_session, crispin_client):
        inbox_folder = crispin_client.folder_names()['inbox']
        all_folder = crispin_client.folder_names()['all']
        g_thrid = _get_g_thrid(account.namespace.id, thread_id, db_session)
        if to_folder == inbox_folder:
            crispin_client.copy_thread(g_thrid, to_folder)
        elif to_folder != all_folder:
            crispin_client.add_label(g_thrid, to_folder)
        # copy a thread to all mail is a noop

    return syncback_action(fn, account, from_folder, db_session)


def remote_delete(account, thread_id, folder_name, db_session):
    def fn(account, db_session, crispin_client):
        crispin_client.delete_messages(uids)

    return syncback_action(fn, account, folder_name, db_session)


def remote_save_draft(account, folder_name, message, db_session, date=None):
    def fn(account, db_session, crispin_client):
        assert folder_name == crispin_client.folder_names()['drafts']
        crispin_client.save_draft(message, date)

    return syncback_action(fn, account, folder_name, db_session)


def remote_delete_draft(account, folder_name, inbox_uid, db_session):
    def fn(account, db_session, crispin_client):
        assert folder_name == crispin_client.folder_names()['drafts']
        crispin_client.delete_draft(inbox_uid)

    return syncback_action(fn, account, folder_name, db_session)
