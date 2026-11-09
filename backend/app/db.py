from sqlalchemy import create_engine, event
from sqlalchemy.orm import sessionmaker
from .config import settings

def make_engine(url: str):
    engine = create_engine(url, connect_args={'check_same_thread': False, 'timeout': 15})
    @event.listens_for(engine, 'connect')
    def sqlite_pragmas(connection, _):
        connection.execute('PRAGMA foreign_keys=ON')
        connection.execute('PRAGMA busy_timeout=15000')
        connection.execute('PRAGMA journal_mode=WAL')
    return engine

engine = make_engine(settings.database_url)
SessionLocal = sessionmaker(engine, expire_on_commit=False)

def get_session():
    with SessionLocal() as session:
        yield session
