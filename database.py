from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Correct URL-encoded password
SQLALCHEMY_DATABASE_URL = "mysql+pymysql://invoice_user:Sinu%40123@localhost/invoice_app"

engine = create_engine(
    SQLALCHEMY_DATABASE_URL,
    echo=True,  # prints SQL queries for debugging
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()
