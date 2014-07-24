# -*- coding: utf-8 -*-
import os, sys, pkgutil, time, re
from inbox.log import get_logger


def or_none(value, selector):
    if value is None:
        return None
    else:
        return selector(value)


def strip_plaintext_quote(text):
    """
    Strip out quoted text with no inline responses.

    TODO: Make sure that the line before the quote looks vaguely like
    a quote header. May be hard to do in an internationalized manner?

    """
    found_quote = False
    lines = text.strip().splitlines()
    quote_start = None
    for i, line in enumerate(lines):
        if line.startswith('>'):
            found_quote = True
            if quote_start is None:
                quote_start = i
        else:
            found_quote = False
    if found_quote:
        return '\n'.join(lines[:quote_start-1])
    else:
        return text


def parse_ml_headers(headers):
    """
    Parse the mailing list headers described in RFC 4021,
    these headers are optional (RFC 2369).

    """
    attrs = {}
    attrs['List-Archive'] = headers.get('List-Archive')
    attrs['List-Help'] = headers.get('List-Help')
    attrs['List-Id'] = headers.get('List-Id')
    attrs['List-Owner'] = headers.get('List-Owner')
    attrs['List-Post'] = headers.get('List-Post')
    attrs['List-Subscribe'] = headers.get('List-Subscribe')
    attrs['List-Unsubscribe'] = headers.get('List-Unsubscribe')

    return attrs


def parse_references(references, in_reply_to):
    """
    Determine the message_ids that the message references, as per JWZ.
    (http://www.jwz.org/doc/threading.html)

    Returns
    -------
    str
        references : a string of tab-separated message_ids.

    """
    replyto = in_reply_to.split()[0] if in_reply_to else in_reply_to

    if not references:
        return [replyto]

    references = references.split()
    if replyto not in references:
        references.append(replyto)
    return references


def cleanup_subject(subject_str):
    """Clean-up a message subject-line.
    For instance, 'Re: Re: Re: Birthday party' becomes 'Birthday party'"""
    cleanup_regexp = "^((Re:|RE:|fwd:|FWD:)\s+)+"
    return re.sub(cleanup_regexp, "", subject_str)


def thread_messages(messages_list):
    """Order a list of messages in a conversation (à la gmail)"""
    msgs_by_date = sorted(messages_list, key=lambda x: x.received_date)
    l = []
    for msg in msgs_by_date:
        insert_message_in_thread(msg, l)
    return l

def insert_after(l, after_element, to_insert):
    index = l.index(after_element)
    l.insert(index + 1, to_insert)

def find_closest_sibling(l, to_insert):
    closest_sibling = None
    for index, message in enumerate(l):
        if index + 1 > len(l):
            closest_sibling = l[-1]
        if (message.received_date < to_insert.received_date and
            l[index+1].received_date > to_insert.received_date):
                closest_sibling = reply

    return closest_sibling

def find_first_more_recent(l, to_insert):
    for msg in l:
        if msg.received_date > to_insert.received_date:
            return msg
    return None

def insert_before(l, before_element, to_insert):
    index = l.index(before_element)
    l.insert(index, to_insert)


def insert_message_in_thread(message, messages_list):
    if message.in_reply_to:
        parent_messages = [msg for msg in messages_list if msg.message_id_header == msg.in_reply_to]
        if len(parent_messages) > 0:
            # We've found the corresponding message-id
            parent_message = parent_messages[0]

            # insert the message after the parent and after any reply to the parent
            direct_replies = [reply for reply in messages_list if reply.in_reply_to == message.in_reply_to]

            if direct_replies == []:
                # insert directly after parent
                insert_after(messages_list, parent_message, message)
                return
            else:
                closest_sibling = find_first_more_recent(direct_replies, message)
                if closest_sibling != None:
                    insert_before(messages_list, closest_sibling, message)
                else:
                    messages_list.append(message)
                return

        if len(message.references) > 1:
            # We couldn't find the message id but we have references. Let's try
            # to insert the message to the closest message-id we could find.
            for reference in reversed(message.references):
                parent_messages = [msg for msg in messages_list if msg.message_id_header == reference]
                if len(parent_messages) > 0:
                    closest_sibling = find_first_more_recent(messages_list, parent_messages[0])
                    if closest_sibling != None:
                        insert_before(messages_list, closest_sibling, message)
                    else:
                        messages_list.append(message)
                    return

        # couldn't find references either
        closest_sibling = find_first_more_recent(messages_list, message)
        if closest_sibling != None:
            insert_before(messages_list, closest_sibling, message)
        else:
            # empty list or message received after everything else. Insert at the end.
            messages_list.append(message)
        return
    elif message.references != []:
        pass
    else:
        # We've got a message without reply to information. It probably belongs next
        # to similar messages which occured at around the same time so we insert
        # the message next to the closest message with only one reference

        direct_replies = [msg for msg in messages_list if len(msg.references) < 2]
        closest_sibling = find_first_more_recent(direct_replies, message)
        if closest_sibling == None:
            # Can't find such a message.
            # We can only use dates in this case.
            closest_sibling = find_first_more_recent(messages_list, message)

        if closest_sibling != None:
            insert_before(messages_list, closest_sibling, message)
        else:
            messages_list.append(message)

def timed(fn):
    """ A decorator for timing methods. """
    def timed_fn(self, *args, **kwargs):
        start_time = time.time()
        ret = fn(self, *args, **kwargs)

        # TODO some modules like gmail.py don't have self.logger
        try:
            if self.log:
                fn_logger = self.log
        except AttributeError:
            fn_logger = get_logger()
            # out = None
        fn_logger.info("[timer] {0} took {1:.3f} seconds.".format(str(fn), float(time.time() - start_time)))
        return ret
    return timed_fn


# Based on: http://stackoverflow.com/a/8556471
def load_modules(base_name, base_path):
    """
    Imports all modules underneath `base_module` in the module tree.

    Note that if submodules are located in different directory trees, you
    need to use `pkgutil.extend_path` to make all the folders appear in
    the module's `__path__`.

    Returns
    -------
    list
        All the modules in the base module tree.
    """
    modules = []

    for importer, module_name, _ in pkgutil.iter_modules(base_path):
        full_module_name = '{}.{}'.format(base_name, module_name)

        if full_module_name not in sys.modules:
            module = importer.find_module(module_name).load_module(
                full_module_name)
        else:
            module = sys.modules[full_module_name]
        modules.append(module)

    return modules


def register_backends(base_name, base_path):
    """
    Dynamically loads all packages contained within thread
    backends module, including those by other module install paths
    """
    modules = load_modules(base_name, base_path)

    mod_for = {}
    for module in modules:
        if hasattr(module, 'PROVIDER'):
            provider = module.PROVIDER
            mod_for[provider] = module

    return mod_for
