from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base

DATABASE_URL = "mysql+pymysql://sql12796897:hPwq3iZJmL@sql12.freesqldatabase.com:3306/sql12796897" 
engine = create_engine(DATABASE_URL, echo=True)

SessionLocal = sessionmaker(bind=engine)

Base = declarative_base()

def get_database():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()