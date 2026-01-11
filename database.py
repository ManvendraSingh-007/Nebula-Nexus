from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
from config import Config


# Pull database credentials from the environment
database_user = Config.DB_USER
database_password = Config.DB_PASSWORD
database_host = Config.DB_HOST
database_port = Config.DB_PORT
database_name = Config.DB_NAME

# Construct the connection string for the MySQL database using the PyMySQL driver
DATABASE_URL = f"mysql+pymysql://{database_user}:{database_password}@{database_host}:{database_port}/{database_name}"

# Create the Engine, 'echo=True' makes it log every SQL query to the terminal for Debugging
engine = create_engine(DATABASE_URL, echo=True)

# A factory for creating individual database sessions/connections
SessionLocal = sessionmaker(bind=engine)

# The base class that all database table models must inherit from
Base = declarative_base()

# A generator function (dependency) that opens a database connection for a request 
# and ensures it is closed once the request is finished.
def get_database():
    database = SessionLocal()
    try:
        yield database
    finally:
        database.close()