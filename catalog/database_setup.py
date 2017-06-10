import os
import sys
from sqlalchemy import Column, ForeignKey, TEXT,Integer, String, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from sqlalchemy import create_engine


Base = declarative_base()



class User(Base):
    __tablename__ = 'user'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    email = Column(String(250), nullable=False)
    picture =Column(String(250))

class Categories(Base):
    __tablename__ = 'categories'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    @property
    def serialize(self):
        """ Return object data in easily serializeable format """
        return{
            'name': self.name,
            'id': self.id
        }

class CatgeoryItem(Base):
    __tablename__ = 'category_item'

    id = Column(Integer, primary_key=True)
    name = Column(String(250), nullable=False)
    description = Column(TEXT, nullable=False)
    date = Column(DateTime, default=func.now())
    categories_id = Column(Integer, ForeignKey('categories.id'))
    categories = relationship(Categories)
    user_id = Column(Integer, ForeignKey('user.id'))
    user = relationship(User)
    @property
    def serialize(self):
        """ Return object data in easily serializeable format """
        return {
            'catalog_id': self.categories_id,
            'item_title':self.name,
            'description': self.description,
            'id': self.id
        }

engine = create_engine('sqlite:///categorieslist.db')

Base.metadata.create_all(engine)
