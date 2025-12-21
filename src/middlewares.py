"""
Middlewares FastAPI
"""
import time
import logging
from typing import Callable
from uuid import uuid4

from fastapi import Request, Response, status
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.middleware.cors import CORSMiddleware

from src.config import settings

# Configuration du logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour logger toutes les requêtes
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Générer un ID unique pour la requête
        request_id = str(uuid4())
        
        # Logger la requête entrante
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Client: {request.client.host if request.client else 'unknown'}"
        )
        
        # Mesurer le temps de traitement
        start_time = time.time()
        
        # Traiter la requête
        response = await call_next(request)
        
        # Calculer le temps de traitement
        process_time = time.time() - start_time
        
        # Logger la réponse
        logger.info(
            f"[{request_id}] {request.method} {request.url.path} - "
            f"Status: {response.status_code} - "
            f"Time: {process_time:.4f}s"
        )
        
        # Ajouter les headers personnalisés
        response.headers["X-Request-ID"] = request_id
        response.headers["X-Process-Time"] = str(process_time)
        
        return response


class ErrorHandlingMiddleware(BaseHTTPMiddleware):
    """
    Middleware pour gérer les erreurs globalement
    """
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        try:
            response = await call_next(request)
            return response
        except ValueError as exc:
            # Erreurs de validation métier
            logger.warning(f"Validation error: {str(exc)}")
            return JSONResponse(
                status_code=status.HTTP_400_BAD_REQUEST,
                content={
                    "detail": str(exc),
                    "type": "validation_error"
                }
            )
        except Exception as exc:
            # Erreurs inattendues
            logger.error(f"Unexpected error: {str(exc)}", exc_info=True)
            return JSONResponse(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                content={
                    "detail": "Une erreur interne est survenue",
                    "type": "internal_error"
                }
            )


class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Middleware simple de rate limiting
    (Pour production, utiliser Redis avec slowapi ou similar)
    """
    
    def __init__(self, app, calls: int = 60, period: int = 60):
        super().__init__(app)
        self.calls = calls
        self.period = period
        self.requests = {}  # IP -> (count, timestamp)
    
    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        # Récupérer l'IP du client
        client_ip = request.client.host if request.client else "unknown"
        
        # Nettoyer les anciennes entrées
        current_time = time.time()
        self.requests = {
            ip: (count, timestamp)
            for ip, (count, timestamp) in self.requests.items()
            if current_time - timestamp < self.period
        }
        
        # Vérifier le rate limit
        if client_ip in self.requests:
            count, timestamp = self.requests[client_ip]
            if current_time - timestamp < self.period:
                if count >= self.calls:
                    return JSONResponse(
                        status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                        content={
                            "detail": f"Trop de requêtes. Limite: {self.calls}/{self.period}s",
                            "retry_after": int(self.period - (current_time - timestamp))
                        }
                    )
                self.requests[client_ip] = (count + 1, timestamp)
            else:
                self.requests[client_ip] = (1, current_time)
        else:
            self.requests[client_ip] = (1, current_time)
        
        response = await call_next(request)
        
        # Ajouter les headers de rate limit
        if client_ip in self.requests:
            count, _ = self.requests[client_ip]
            response.headers["X-RateLimit-Limit"] = str(self.calls)
            response.headers["X-RateLimit-Remaining"] = str(max(0, self.calls - count))
        
        return response


def setup_cors(app):
    """
    Configure CORS pour l'application
    
    Args:
        app: Application FastAPI
    """
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.CORS_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=["X-Request-ID", "X-Process-Time", "X-RateLimit-Limit", "X-RateLimit-Remaining"]
    )


def setup_middlewares(app):
    """
    Configure tous les middlewares de l'application
    
    Args:
        app: Application FastAPI
    """
    # CORS (doit être ajouté en premier)
    setup_cors(app)
    
    # Logging des requêtes
    app.add_middleware(RequestLoggingMiddleware)
    
    # Gestion des erreurs
    app.add_middleware(ErrorHandlingMiddleware)
    
    # Rate limiting
    if not settings.DEBUG:
        app.add_middleware(
            RateLimitMiddleware,
            calls=settings.RATE_LIMIT_PER_MINUTE,
            period=60
        )
    
    logger.info("Middlewares configured successfully")