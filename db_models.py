from sqlalchemy import Column, Integer, String, ForeignKey
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import create_engine


engine = create_engine("postgresql://postgres:postgres@127.0.0.1:5432/postgres", echo=True)
Base = declarative_base()


class Article(Base):
    __tablename__ = "Article"

    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False, unique=True)
    incoming_links = Column(Integer, default=0)
    outbound_links = Column(Integer, default=0)
    depth = Column(Integer, default=0)
    id_where_find = Column(Integer, ForeignKey("Article.id"))

    def __repr__(self):
        return f'{self.name} - {self.id}'


Base.metadata.create_all(engine)