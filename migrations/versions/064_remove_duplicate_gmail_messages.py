"""Remove duplicate Gmail messages

Previous bugs creating ImapUid entries caused some Gmail messages to be
"dangled" (having no ImapUid entries), which would cause the sync engine to
try to create duplicate message entries when it re-downloaded the messages.

Revision ID: 38b457375db0
Revises: 4fd3fcd46a3b
Create Date: 2014-07-19 16:50:28.463900

"""

# revision identifiers, used by Alembic.
revision = '38b457375db0'
down_revision = '2d05e116bdb7'

from alembic import op


def upgrade():
    op.execute("DELETE FROM message WHERE g_msgid IS NOT NULL AND id NOT IN (SELECT message_id FROM imapuid);")


def downgrade():
    pass
