"""Database models and setup for PostgreSQL."""
from sqlalchemy import create_engine, Column, Integer, String, Date, Time, Text, DateTime, func
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

DATABASE_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@localhost:5432/meetings_db")

Base = declarative_base()


class Meeting(Base):
    """Meeting model."""
    __tablename__ = "meetings"
    
    id = Column(Integer, primary_key=True, index=True)
    title = Column(String(255), nullable=False)
    meeting_date = Column(Date, nullable=False)
    meeting_time = Column(Time, nullable=True)
    reasoning = Column(Text, nullable=True)
    created_at = Column(DateTime, server_default=func.now())


def create_tables():
    """Create database tables."""
    engine = create_engine(DATABASE_URL)
    Base.metadata.create_all(bind=engine)
    return engine


def get_db():
    """Get database session."""
    engine = create_engine(DATABASE_URL)
    SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
    return SessionLocal()


if __name__ == "__main__":
    # Create tables when run directly
    create_tables()
    print("Database tables created successfully!")

