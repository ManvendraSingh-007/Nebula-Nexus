from .database import Base
from sqlalchemy import Column, Integer, String, DateTime, Boolean, func, text, ForeignKey

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    password = Column(String(200), nullable=False)
    

class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True, index=True)
    sender_id = Column(Integer, ForeignKey("users.id"))
    receiver_id = Column(Integer, ForeignKey("users.id"))
    content = Column(String(1000))
    timestamp = Column(DateTime(timezone=True), server_default=func.now())

    

class PendingUser(Base):
    __tablename__ = "pending_users"
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), nullable=False)
    email = Column(String(100), nullable=False)
    password = Column(String(200), nullable=False) # Hashed
    otp_code = Column(String(20), nullable=False)
    created_at = Column(DateTime, server_default=text("(UTC_TIMESTAMP())"))
    isVerified = Column(Boolean, default=False, nullable=False)

class PasswordResetToken(Base):
    __tablename__ = "password_reset_tokens"
    
    id = Column(Integer, primary_key=True, index=True)
    email = Column(String(255), index=True)
    token = Column(String(255), unique=True, index=True)
    expires_at = Column(DateTime)
    created_at = Column(DateTime, server_default=text("(UTC_TIMESTAMP())"))
