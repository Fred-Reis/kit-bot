from sqlalchemy import Boolean, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from db import Base


class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    whatsapp_id = Column(String(64), unique=True, index=True, nullable=False)
    name = Column(String(120), nullable=True)
    role = Column(String(32), index=True, nullable=True)

    profile = relationship("Profile", back_populates="user", uselist=False)
    properties = relationship("Property", back_populates="owner")
    leases = relationship("Lease", back_populates="tenant")
    tickets = relationship("Ticket", back_populates="user")
    documents = relationship("Document", back_populates="user")
    events = relationship("Event", back_populates="user")


class Profile(Base):
    __tablename__ = "profiles"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    cpf = Column(String(20), nullable=True)
    email = Column(String(255), nullable=True)
    income = Column(String(32), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="profile")


class Property(Base):
    __tablename__ = "properties"

    id = Column(Integer, primary_key=True)
    owner_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    address = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    owner = relationship("User", back_populates="properties")
    leases = relationship("Lease", back_populates="property")


class Lease(Base):
    __tablename__ = "leases"

    id = Column(Integer, primary_key=True)
    property_id = Column(Integer, ForeignKey("properties.id"), nullable=False, index=True)
    tenant_id = Column(Integer, ForeignKey("users.id"), nullable=False, index=True)
    status = Column(String(32), index=True, nullable=True)
    start_at = Column(DateTime(timezone=True), nullable=True)
    end_at = Column(DateTime(timezone=True), nullable=True)

    property = relationship("Property", back_populates="leases")
    tenant = relationship("User", back_populates="leases")


class Conversation(Base):
    __tablename__ = "conversations"

    id = Column(Integer, primary_key=True)
    chat_id = Column(String(128), unique=True, index=True, nullable=False)
    state = Column(String(64), index=True, nullable=True)
    context_json = Column(JSONB, default=dict, nullable=False)
    updated_at = Column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
    )


class Event(Base):
    __tablename__ = "events"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    chat_id = Column(String(128), index=True, nullable=False)
    type = Column(String(64), index=True, nullable=False)
    payload_json = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="events")


class Ticket(Base):
    __tablename__ = "tickets"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    type = Column(String(64), index=True, nullable=False)
    status = Column(String(32), index=True, nullable=True)
    owner_action_required = Column(Boolean, nullable=False, default=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="tickets")
    approvals = relationship("Approval", back_populates="ticket")


class Document(Base):
    __tablename__ = "documents"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True, index=True)
    type = Column(String(64), index=True, nullable=True)
    status = Column(String(32), index=True, nullable=True)
    path = Column(Text, nullable=True)
    extracted_json = Column(JSONB, default=dict, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    user = relationship("User", back_populates="documents")


class Approval(Base):
    __tablename__ = "approvals"

    id = Column(Integer, primary_key=True)
    ticket_id = Column(Integer, ForeignKey("tickets.id"), nullable=False, index=True)
    approver_role = Column(String(32), index=True, nullable=True)
    status = Column(String(32), index=True, nullable=True)
    reason = Column(Text, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    ticket = relationship("Ticket", back_populates="approvals")
