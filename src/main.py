"""
Application FastAPI principale - Money Transfer API
"""
from fastapi import FastAPI, status
from fastapi.responses import JSONResponse
from contextlib import asynccontextmanager

from src.config import settings
from src.middlewares import setup_middlewares


# Import des routers
from src.api.endpoints.v2 import (
    auth_router,
    currency_router,
    country_router,
    exchange_rate_router,
    payment_partner_router,
    payment_account_router,
    fee_router
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Gestion du cycle de vie de l'application
    """
    # Startup
    print("🚀 Démarrage de l'application...")
    print("✅ Base de données initialisée")
    yield
    # Shutdown
    print("👋 Arrêt de l'application...")


# Création de l'application
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="API complète pour les transferts d'argent internationaux",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json"
)


# Configuration des middlewares
setup_middlewares(app)


# ========================================
# Routes de base
# ========================================

@app.get("/", tags=["Root"])
async def root():
    """
    Route racine de l'API
    """
    return {
        "name": settings.APP_NAME,
        "version": settings.APP_VERSION,
        "status": "running",
        "docs": "/docs",
        "redoc": "/redoc"
    }


@app.get("/health", tags=["Health"])
async def health_check():
    """
    Vérification de l'état de santé de l'API
    """
    return {
        "status": "healthy",
        "version": settings.APP_VERSION
    }


# ========================================
# Inclusion des routers
# ========================================

# Authentification (pas de préfixe /api pour faciliter l'usage)
app.include_router(auth_router)

# API v1
API_V1_PREFIX = "/api/v2"

app.include_router(currency_router, prefix=API_V1_PREFIX)
app.include_router(country_router, prefix=API_V1_PREFIX)
app.include_router(exchange_rate_router, prefix=API_V1_PREFIX)
app.include_router(payment_partner_router, prefix=API_V1_PREFIX)
app.include_router(payment_account_router, prefix=API_V1_PREFIX)
app.include_router(fee_router, prefix=API_V1_PREFIX)


# ========================================
# Gestion d'erreurs globale
# ========================================

@app.exception_handler(404)
async def not_found_handler(request, exc):
    """Handler pour les erreurs 404"""
    return JSONResponse(
        status_code=status.HTTP_404_NOT_FOUND,
        content={"detail": "Resource not found"}
    )


@app.exception_handler(500)
async def internal_error_handler(request, exc):
    """Handler pour les erreurs 500"""
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={"detail": "Internal server error"}
    )


if __name__ == "__main__":
    import uvicorn
    
    uvicorn.run(
        "src.main:app",
        host="0.0.0.0",
        port=8000,
        reload=settings.DEBUG,
        log_level="info"
    )