from database import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean
import datetime

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(200), nullable=False)
    
    
class Message(Base):
    __tablename__ = "messages"
    
    id = Column(Integer, primary_key=True, index=True)
    

class PendingUser(Base):
    __tablename__ = "pending_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    password = Column(String(200), nullable=False) # Hashed
    otp_code = Column(String(20), nullable=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    isVerified = Column(Boolean, default=False, nullable=False)