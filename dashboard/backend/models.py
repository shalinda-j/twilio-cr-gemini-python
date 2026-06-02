# models.py - the data model. companies -> users / phone_numbers / calls -> messages.
from sqlalchemy import (
    Boolean,
    Column,
    DateTime,
    ForeignKey,
    Integer,
    String,
    Text,
    func,
)
from sqlalchemy.orm import relationship

from .database import Base


class Company(Base):
    __tablename__ = "companies"
    id = Column(Integer, primary_key=True)
    name = Column(String(200), nullable=False)
    # Each company can have its own AI persona / instructions.
    system_prompt = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    users = relationship("User", back_populates="company", cascade="all, delete-orphan")
    numbers = relationship("PhoneNumber", back_populates="company", cascade="all, delete-orphan")
    calls = relationship("Call", back_populates="company", cascade="all, delete-orphan")


class User(Base):
    __tablename__ = "users"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    email = Column(String(255), unique=True, nullable=False, index=True)
    password_hash = Column(String(255), nullable=False)
    role = Column(String(20), default="admin")  # admin | viewer
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="users")


class PhoneNumber(Base):
    __tablename__ = "phone_numbers"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False)
    number = Column(String(32), nullable=False, index=True)
    label = Column(String(120), nullable=True)
    provider = Column(String(120), nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    company = relationship("Company", back_populates="numbers")


class Call(Base):
    __tablename__ = "calls"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    call_uuid = Column(String(64), index=True)
    caller = Column(String(64), nullable=True)
    direction = Column(String(16), default="inbound")
    language = Column(String(8), nullable=True)
    status = Column(String(16), default="in_progress")  # in_progress | completed | failed
    started_at = Column(DateTime(timezone=True), server_default=func.now())
    ended_at = Column(DateTime(timezone=True), nullable=True)
    duration_seconds = Column(Integer, default=0)
    turns = Column(Integer, default=0)

    company = relationship("Company", back_populates="calls")
    messages = relationship(
        "Message", back_populates="call", cascade="all, delete-orphan", order_by="Message.id"
    )


class Message(Base):
    __tablename__ = "messages"
    id = Column(Integer, primary_key=True)
    call_id = Column(Integer, ForeignKey("calls.id"), nullable=False, index=True)
    role = Column(String(16), nullable=False)  # user | assistant
    text = Column(Text, nullable=False)
    language = Column(String(8), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    call = relationship("Call", back_populates="messages")


class Provider(Base):
    """A SIP trunk / carrier connection a company brings."""
    __tablename__ = "providers"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    name = Column(String(120), nullable=False)
    kind = Column(String(32), default="sip")        # sip | other
    host = Column(String(255), nullable=True)
    username = Column(String(120), nullable=True)
    password = Column(String(255), nullable=True)
    notes = Column(Text, nullable=True)
    active = Column(Boolean, default=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())


class Setting(Base):
    """Flexible company-scoped key/value store (TTS choice, API keys, webhooks…)."""
    __tablename__ = "settings"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    key = Column(String(120), nullable=False, index=True)
    value = Column(Text, nullable=True)


class KnowledgeEntry(Base):
    """A piece of knowledge/dataset that can be fed to the assistant for a company."""
    __tablename__ = "knowledge"
    id = Column(Integer, primary_key=True)
    company_id = Column(Integer, ForeignKey("companies.id"), nullable=False, index=True)
    title = Column(String(200), nullable=False)
    content = Column(Text, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
