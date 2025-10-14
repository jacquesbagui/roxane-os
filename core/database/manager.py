"""
Roxane OS - Database Manager
Gestionnaire de base de données PostgreSQL
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional, List, Any
from contextlib import asynccontextmanager
from loguru import logger
from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.pool import QueuePool
from sqlalchemy.exc import SQLAlchemyError

from .models import Base, User, Session as DBSession, Conversation, Message


class DatabaseManager:
    """
    Gestionnaire de base de données PostgreSQL
    
    Single Responsibility: Gestion de la connexion et des opérations DB
    Dependency Inversion: Interface pour différents backends DB
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        Initialise le gestionnaire de base de données
        
        Args:
            config: Configuration PostgreSQL
        """
        self.config = config
        self.engine = None
        self.SessionLocal = None
        self._initialized = False
        
        logger.info("Database manager initialized")
    
    async def initialize(self) -> bool:
        """
        Initialise la connexion à la base de données
        
        Returns:
            True si initialisé avec succès
        """
        try:
            # Construire l'URL de connexion
            db_url = self._build_connection_url()
            
            # Créer l'engine avec pool de connexions
            self.engine = create_engine(
                db_url,
                poolclass=QueuePool,
                pool_size=self.config.get('pool_size', 10),
                max_overflow=self.config.get('max_overflow', 20),
                pool_pre_ping=True,  # Vérifier les connexions avant utilisation
                echo=self.config.get('echo', False),
                echo_pool=self.config.get('echo', False)
            )
            
            # Créer la factory de sessions
            self.SessionLocal = sessionmaker(
                autocommit=False,
                autoflush=False,
                bind=self.engine
            )
            
            # Tester la connexion
            await self._test_connection()
            
            # Créer les tables si nécessaire
            await self._create_tables()
            
            self._initialized = True
            logger.success("✅ Database connection established")
            return True
            
        except Exception as e:
            logger.error(f"Failed to initialize database: {e}")
            return False
    
    def _build_connection_url(self) -> str:
        """Construit l'URL de connexion PostgreSQL"""
        host = self.config.get('host', 'localhost')
        port = self.config.get('port', 5432)
        database = self.config.get('database', 'roxane_db')
        username = self.config.get('user', 'roxane')  # Utiliser 'user' au lieu de 'username'
        password = self.config.get('password', 'roxane_secure_pass_2025')
        ssl_mode = self.config.get('ssl_mode', 'prefer')
        
        url = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        
        if ssl_mode != 'disable':
            url += f"?sslmode={ssl_mode}"
        
        return url
    
    async def _test_connection(self) -> None:
        """Teste la connexion à la base de données"""
        def test_sync():
            with self.engine.connect() as conn:
                result = conn.execute(text("SELECT 1"))
                return result.scalar()
        
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(None, test_sync)
        
        if result != 1:
            raise Exception("Database connection test failed")
        
        logger.info("Database connection test successful")
    
    async def _create_tables(self) -> None:
        """Crée les tables si elles n'existent pas"""
        def create_sync():
            Base.metadata.create_all(bind=self.engine)
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, create_sync)
        
        logger.info("Database tables created/verified")
    
    @asynccontextmanager
    async def get_session(self):
        """
        Contexte manager pour obtenir une session DB
        
        Usage:
            async with db_manager.get_session() as session:
                # Utiliser la session
                pass
        """
        if not self._initialized:
            raise Exception("Database not initialized")
        
        session = self.SessionLocal()
        try:
            yield session
            session.commit()
        except Exception as e:
            session.rollback()
            logger.error(f"Database session error: {e}")
            raise
        finally:
            session.close()
    
    async def get_user_by_username(self, username: str) -> Optional[User]:
        """Récupère un utilisateur par nom d'utilisateur"""
        def get_sync():
            session = self.SessionLocal()
            try:
                return session.query(User).filter(User.username == username).first()
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_sync)
    
    async def create_user(self, username: str, email: Optional[str] = None) -> User:
        """Crée un nouvel utilisateur"""
        def create_sync():
            session = self.SessionLocal()
            try:
                user = User(username=username, email=email)
                session.add(user)
                session.commit()
                session.refresh(user)
                return user
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, create_sync)
    
    async def get_or_create_user(self, username: str, email: Optional[str] = None) -> User:
        """Récupère ou crée un utilisateur"""
        user = await self.get_user_by_username(username)
        if user:
            return user
        
        return await self.create_user(username, email)
    
    async def get_session_by_id(self, session_id: str) -> Optional[DBSession]:
        """Récupère une session par ID"""
        def get_sync():
            session = self.SessionLocal()
            try:
                return session.query(DBSession).filter(DBSession.session_token == session_id).first()
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_sync)
    
    async def create_session(self, user_id: str, session_id: str) -> DBSession:
        """Crée une nouvelle session"""
        def create_sync():
            session = self.SessionLocal()
            try:
                db_session = DBSession(user_id=user_id, session_token=session_id)
                session.add(db_session)
                session.commit()
                session.refresh(db_session)
                return db_session
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, create_sync)
    
    async def get_or_create_session(self, user_id: str, session_id: str) -> DBSession:
        """Récupère ou crée une session"""
        db_session = await self.get_session_by_id(session_id)
        if db_session:
            return db_session
        
        return await self.create_session(user_id, session_id)
    
    async def add_message(
        self,
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
        def add_sync():
            session = self.SessionLocal()
            try:
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
                session.add(message)
                
                # Mettre à jour le compteur de messages
                conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
                if conversation:
                    conversation.message_count += 1
                
                session.commit()
                session.refresh(message)
                return message
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, add_sync)
    
    async def get_conversation_messages(
        self,
        conversation_id: str,
        limit: Optional[int] = None,
        offset: int = 0
    ) -> List[Message]:
        """Récupère les messages d'une conversation"""
        def get_sync():
            session = self.SessionLocal()
            try:
                query = session.query(Message).filter(Message.conversation_id == conversation_id)
                query = query.order_by(Message.timestamp.asc())
                
                if offset > 0:
                    query = query.offset(offset)
                
                if limit:
                    query = query.limit(limit)
                
                return query.all()
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_sync)
    
    async def search_messages(
        self,
        query_text: str,
        user_id: Optional[str] = None,
        limit: int = 10
    ) -> List[Message]:
        """Recherche des messages par contenu"""
        def search_sync():
            session = self.SessionLocal()
            try:
                query = session.query(Message).join(Conversation).join(DBSession)
                
                if user_id:
                    query = query.filter(DBSession.user_id == user_id)
                
                query = query.filter(Message.content.ilike(f'%{query_text}%'))
                query = query.order_by(Message.timestamp.desc())
                query = query.limit(limit)
                
                return query.all()
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, search_sync)
    
    async def update_conversation_message_count(self, conversation_id: str) -> None:
        """Met à jour le compteur de messages d'une conversation"""
        def update_sync():
            session = self.SessionLocal()
            try:
                conversation = session.query(Conversation).filter(Conversation.id == conversation_id).first()
                if conversation:
                    # Compter les messages actuels
                    message_count = session.query(Message).filter(Message.conversation_id == conversation_id).count()
                    conversation.message_count = message_count
                    conversation.updated_at = datetime.utcnow()
                    session.commit()
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        await loop.run_in_executor(None, update_sync)
    
    async def get_stats(self) -> Dict[str, Any]:
        """Retourne les statistiques de la base de données"""
        def get_sync():
            session = self.SessionLocal()
            try:
                stats = {}
                
                # Compter les utilisateurs
                stats['users_count'] = session.query(User).count()
                
                # Compter les sessions
                stats['sessions_count'] = session.query(DBSession).count()
                
                # Compter les conversations
                stats['conversations_count'] = session.query(Conversation).count()
                
                # Compter les messages
                stats['messages_count'] = session.query(Message).count()
                
                return stats
            finally:
                session.close()
        
        loop = asyncio.get_event_loop()
        return await loop.run_in_executor(None, get_sync)
    
    async def cleanup(self) -> None:
        """Nettoie les ressources de la base de données"""
        if self.engine:
            self.engine.dispose()
            logger.info("Database connection closed")
    
    def is_initialized(self) -> bool:
        """Vérifie si la base de données est initialisée"""
        return self._initialized
