from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker, Session, declarative_base
import os
from dotenv import load_dotenv

# Load key-value pairs from the .env file into environment variables.
load_dotenv()

# Pull database credentials from the environment
database_user = os.getenv("DATABASE_USER")
database_password = os.getenv("DATABASE_PASSWORD")
database_host = os.getenv("DATABASE_HOST")
database_port = os.getenv("DATABASE_PORT")
database_name = os.getenv("DATABASE_NAME")

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