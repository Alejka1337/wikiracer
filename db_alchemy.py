from sqlalchemy import create_engine, select, insert, delete
from sqlalchemy.orm import Session
from db_models import Article

engine = create_engine("postgresql://postgres:postgres@127.0.0.1:5432/postgres", echo=True)


def create_start_article(name: str):
    session = Session(engine)
    new_article = insert(Article).values(name=name)
    session.execute(new_article)
    session.commit()
    session.close()


def select_article_id(name: str):
    session = Session(engine)
    result = session.scalar(select(Article.id).where(Article.name == name))
    session.close()
    return result


def select_article_name(id: int):
    session = Session(engine)
    result = session.scalar(select(Article.name).where(Article.id == id))
    session.close()
    return result


def select_id_where_find(name: str):
    session = Session(engine)
    result = session.scalar(select(Article.id_where_find).where(Article.name == name))
    session.close()
    return result


def create_article_with_params(name: str, depth: int, id_where_find: int, count_incoming_links: int):
    session = Session(engine)
    new_article = insert(Article).values(name=name, depth=depth,
                                         id_where_find=id_where_find,
                                         incoming_links=count_incoming_links)
    session.execute(new_article)
    session.commit()
    session.close()


def select_articles_without_outbound_links():
    session = Session(engine)
    result = session.query(Article).filter(Article.outbound_links == 0).limit(100)
    session.close()
    return result.all()


def check_if_article_exists(name: str):
    session = Session(engine)

    try:
        session.query(Article).filter(Article.name == name).one()
        return False
    except Exception as e:
        print(e)
        return True
    finally:
        session.close()


def update_incoming_links(name: str, quantity: int):
    session = Session(engine)
    select_article = session.scalar(select(Article).where(Article.name == name))
    select_article.incoming_links += quantity
    session.commit()
    session.close()


def update_outbound_links(name: str, quantity: int):
    session = Session(engine)
    select_article = session.scalar(select(Article).where(Article.name == name))
    select_article.outbound_links = quantity
    session.commit()
    session.close()


