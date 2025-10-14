"""
Roxane OS - Database Models
Modèles SQLAlchemy pour PostgreSQL
"""

from datetime import datetime
from typing import Optional, List
from sqlalchemy import (
    Column, Integer, String, Text, DateTime, Float, Boolean, 
    ForeignKey, Index, JSON, LargeBinary
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, Session
from sqlalchemy.dialects.postgresql import UUID
import uuid

Base = declarative_base()


class User(Base):
    """Modèle utilisateur"""
    __tablename__ = 'users'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    username = Column(String(100), unique=True, nullable=False, index=True)
    email = Column(String(255), unique=True, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    preferences = Column(JSON, default=dict)
    
    # Relations
    sessions = relationship("Session", back_populates="user", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<User(id={self.id}, username='{self.username}')>"


class Session(Base):
    """Modèle session utilisateur"""
    __tablename__ = 'sessions'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    user_id = Column(UUID(as_uuid=True), ForeignKey('users.id'), nullable=False)
    session_token = Column(String(255), unique=True, nullable=False, index=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    expires_at = Column(DateTime)
    last_activity = Column(DateTime, default=datetime.utcnow)
    is_active = Column(Boolean, default=True, nullable=False)
    meta_data = Column(JSON, default=dict)
    
    # Relations
    user = relationship("User", back_populates="sessions")
    conversations = relationship("Conversation", back_populates="session", cascade="all, delete-orphan")
    
    def __repr__(self):
        return f"<Session(id={self.id}, session_token='{self.session_token}')>"


class Conversation(Base):
    """Modèle conversation"""
    __tablename__ = 'conversations'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    session_id = Column(UUID(as_uuid=True), ForeignKey('sessions.id'), nullable=False)
    title = Column(String(255), nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    message_count = Column(Integer, default=0, nullable=False)
    summary = Column(Text, nullable=True)
    meta_data = Column(JSON, default=dict)
    
    # Relations
    session = relationship("Session", back_populates="conversations")
    messages = relationship("Message", back_populates="conversation", cascade="all, delete-orphan")
    
    # Indexes
    __table_args__ = (
        Index('idx_conversation_session', 'session_id'),
        Index('idx_conversation_created', 'created_at'),
    )
    
    def __repr__(self):
        return f"<Conversation(id={self.id}, title='{self.title}')>"


class Message(Base):
    """Modèle message"""
    __tablename__ = 'messages'
    
    id = Column(UUID(as_uuid=True), primary_key=True, default=uuid.uuid4)
    conversation_id = Column(UUID(as_uuid=True), ForeignKey('conversations.id'), nullable=False)
    role = Column(String(20), nullable=False)  # 'user', 'assistant', 'system'
    content = Column(Text, nullable=False)
    timestamp = Column(DateTime, default=datetime.utcnow, nullable=False)
    
    # NLP fields
    intent = Column(String(100), nullable=True)
    intent_confidence = Column(Float, nullable=True)
    entities = Column(JSON, default=dict)
    
    # Response fields
    response_text = Column(Text, nullable=True)
    response_confidence = Column(Float, nullable=True)
    tokens_used = Column(Integer, nullable=True)
    latency = Column(Float, nullable=True)
    
    # Embedding
    embedding = Column(LargeBinary, nullable=True)  # Vector embedding
    
    # Metadata
    meta_data = Column(JSON, default=dict)
    
    # Relations
    conversation = relationship("Conversation", back_populates="messages")
    
    # Indexes
    __table_args__ = (
        Index('idx_message_conversation', 'conversation_id'),
        Index('idx_message_timestamp', 'timestamp'),
        Index('idx_message_role', 'role'),
        Index('idx_message_intent', 'intent'),
    )
    
    def __repr__(self):
        return f"<Message(id={self.id}, role='{self.role}', content='{self.content[:50]}...')>"


# Fonctions utilitaires
def create_user(db: Session, username: str, email: Optional[str] = None) -> User:
    """Crée un nouvel utilisateur"""
    user = User(username=username, email=email)
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


def get_user_by_username(db: Session, username: str) -> Optional[User]:
    """Récupère un utilisateur par nom d'utilisateur"""
    return db.query(User).filter(User.username == username).first()


def create_session(db: Session, user_id: str, session_id: str) -> Session:
    """Crée une nouvelle session"""
    session = Session(user_id=user_id, session_id=session_id)
    db.add(session)
    db.commit()
    db.refresh(session)
    return session


def get_session_by_id(db: Session, session_id: str) -> Optional[Session]:
    """Récupère une session par ID"""
    return db.query(Session).filter(Session.session_id == session_id).first()


def create_conversation(db: Session, session_id: str, title: Optional[str] = None) -> Conversation:
    """Crée une nouvelle conversation"""
    conversation = Conversation(session_id=session_id, title=title)
    db.add(conversation)
    db.commit()
    db.refresh(conversation)
    return conversation


def add_message(
    db: Session,
    conversation_id: str,
    role: str,
    content: str,
    intent: Optional[str] = None,
    intent_confidence: Optional[float] = None,
    entities: Optional[dict] = None,
    response_text: Optional[str] = None,
    response_confidence: Optional[float] = None,
    tokens_used: Optional[int] = None,
    latency: Optional[float] = None,
    embedding: Optional[bytes] = None,
    metadata: Optional[dict] = None
) -> Message:
    """Ajoute un message à une conversation"""
    message = Message(
        conversation_id=conversation_id,
        role=role,
        content=content,
        intent=intent,
        intent_confidence=intent_confidence,
        entities=entities or {},
        response_text=response_text,
        response_confidence=response_confidence,
        tokens_used=tokens_used,
        latency=latency,
        embedding=embedding,
        metadata=metadata or {}
    )
    db.add(message)
    
    # Mettre à jour le compteur de messages
    conversation = db.query(Conversation).filter(Conversation.id == conversation_id).first()
    if conversation:
        conversation.message_count += 1
        conversation.updated_at = datetime.utcnow()
    
    db.commit()
    db.refresh(message)
    return message


def get_conversation_messages(
    db: Session, 
    conversation_id: str, 
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Message]:
    """Récupère les messages d'une conversation"""
    query = db.query(Message).filter(Message.conversation_id == conversation_id)
    query = query.order_by(Message.timestamp.asc())
    
    if offset > 0:
        query = query.offset(offset)
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def get_user_conversations(
    db: Session,
    user_id: str,
    limit: Optional[int] = None,
    offset: int = 0
) -> List[Conversation]:
    """Récupère les conversations d'un utilisateur"""
    query = db.query(Conversation).join(Session).filter(Session.user_id == user_id)
    query = query.order_by(Conversation.updated_at.desc())
    
    if offset > 0:
        query = query.offset(offset)
    
    if limit:
        query = query.limit(limit)
    
    return query.all()


def search_messages(
    db: Session,
    query_text: str,
    user_id: Optional[str] = None,
    limit: int = 10
) -> List[Message]:
    """Recherche des messages par contenu"""
    query = db.query(Message).join(Conversation).join(Session)
    
    if user_id:
        query = query.filter(Session.user_id == user_id)
    
    query = query.filter(Message.content.ilike(f'%{query_text}%'))
    query = query.order_by(Message.timestamp.desc())
    query = query.limit(limit)
    
    return query.all()
