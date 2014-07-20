from sqlalchemy import Column, Integer, MetaData
from sqlalchemy.ext.declarative import as_declarative, declared_attr

from inbox.models.mixins import AutoTimestampMixin


@as_declarative()
class Base(AutoTimestampMixin):
    """
    Provides automated table name, primary key column, and audit timestamps.

    """
    id = Column(Integer, primary_key=True, autoincrement=True)

    @declared_attr
    def __tablename__(cls):
        return cls.__name__.lower()

    @declared_attr
    def __table_args__(cls):
        return {'extend_existing': True}


class MailSyncBase(Base):
    __abstract__ = True
    __table_args__ = {'schema': 'mailsync'}
    metadata = MetaData()
