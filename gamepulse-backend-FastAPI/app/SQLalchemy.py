import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base

class CustomBase:
    @classmethod
    def __tablename__(cls):
        if hasattr(cls, '__tablename__'):
            return cls.__tablename__
        return cls.__name__.lower()

Base = declarative_base(cls=CustomBase)

