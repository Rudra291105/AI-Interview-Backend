from sqlalchemy import create_engine #this is the library we use to connect to the database and perform operations on it.
from sqlalchemy.orm import sessionmaker, declarative_base #sessionmaker is a factory for creating new Session objects, and declarative_base is a factory function that constructs a base class for declarative class definitions.
from dotenv import load_dotenv
import os

load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL")


engine = engine = create_engine( DATABASE_URL, pool_pre_ping=True )

SessionLocal = sessionmaker(#create database session
    autocommit=False,#Changes are not automatically saved
    autoflush=False,
    bind=engine
)

Base = declarative_base()
def get_db():
    db = SessionLocal()
    try:                        #from here return database session to the api
        yield db
    finally:
        db.close()