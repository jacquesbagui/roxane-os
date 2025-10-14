"""
Roxane OS - API Server
Serveur FastAPI pour l'interface REST et WebSocket
"""

from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List, Optional
import asyncio
from loguru import logger

from core.engine import get_engine, RoxaneResponse


# Modèles Pydantic
class ChatRequest(BaseModel):
    message: str
    user_id: str = "default"
    context: Optional[dict] = None


class ChatResponse(BaseModel):
    text: str
    actions: List[dict]
    confidence: float


class SystemStatus(BaseModel):
    status: str
    model: dict
    services: dict


# Créer l'application FastAPI
app = FastAPI(
    title="Roxane OS API",
    description="API REST et WebSocket pour Roxane OS",
    version="1.0.0"
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# WebSocket connection manager
class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []
    
    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket connected. Total: {len(self.active_connections)}")
    
    def disconnect(self, websocket: WebSocket):
        self.active_connections.remove(websocket)
        logger.info(f"WebSocket disconnected. Total: {len(self.active_connections)}")
    
    async def broadcast(self, message: dict):
        for connection in self.active_connections:
            try:
                await connection.send_json(message)
            except:
                pass


manager = ConnectionManager()


# Routes
@app.get("/")
async def root():
    """Page d'accueil de l'API"""
    return {
        "name": "Roxane OS API",
        "version": "1.0.0",
        "status": "running",
        "endpoints": {
            "chat": "/api/chat",
            "status": "/api/status",
            "websocket": "/ws"
        }
    }


@app.get("/api/status")
async def get_status() -> SystemStatus:
    """Obtient le statut du système"""
    try:
        engine = get_engine()
        model_info = engine.model_manager.get_model_info()
        
        return SystemStatus(
            status="running",
            model=model_info,
            services={
                "core": "active",
                "audio": "active",
                "database": "active"
            }
        )
    except Exception as e:
        logger.error(f"Error getting status: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/api/chat")
async def chat(request: ChatRequest) -> ChatResponse:
    """
    Endpoint de chat principal
    
    Body:
        - message: Message de l'utilisateur
        - user_id: Identifiant utilisateur (optionnel)
        - context: Contexte additionnel (optionnel)
    
    Returns:
        Réponse de Roxane avec texte et actions
    """
    try:
        logger.info(f"Chat request from {request.user_id}: {request.message[:50]}...")
        
        engine = get_engine()
        response = await engine.process_message(
            message=request.message,
            user_id=request.user_id,
            context=request.context
        )
        
        # Broadcaster aux websockets
        await manager.broadcast({
            "type": "chat",
            "user_id": request.user_id,
            "message": request.message,
            "response": response.text
        })
        
        return ChatResponse(
            text=response.text,
            actions=response.actions,
            confidence=response.confidence
        )
    
    except Exception as e:
        logger.error(f"Error in chat: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """
    WebSocket pour communication temps réel
    """
    await manager.connect(websocket)
    
    try:
        engine = get_engine()
        
        while True:
            # Recevoir un message
            data = await websocket.receive_json()
            message = data.get("message")
            user_id = data.get("user_id", "default")
            
            logger.info(f"WebSocket message from {user_id}: {message[:50]}...")
            
            # Envoyer un accusé de réception
            await websocket.send_json({
                "type": "processing",
                "status": "received"
            })
            
            # Traiter le message
            response = await engine.process_message(
                message=message,
                user_id=user_id
            )
            
            # Envoyer la réponse
            await websocket.send_json({
                "type": "response",
                "text": response.text,
                "actions": response.actions,
                "confidence": response.confidence
            })
    
    except WebSocketDisconnect:
        manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        manager.disconnect(websocket)


@app.on_event("startup")
async def startup_event():
    """Initialisation au démarrage"""
    logger.info("🚀 Starting Roxane API Server...")
    
    # Initialiser le moteur
    engine = get_engine()
    
    logger.success("✅ Roxane API Server started")


@app.on_event("shutdown")
async def shutdown_event():
    """Nettoyage à l'arrêt"""
    logger.info("🛑 Shutting down Roxane API Server...")
    
    engine = get_engine()
    await engine.shutdown()
    
    logger.success("✅ Roxane API Server shut down")


# Point d'entrée
if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "api.server:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )