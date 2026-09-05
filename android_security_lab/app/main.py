"""
Android Security Lab - Main Application

FastAPI application entry point.
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from .config import get_settings
from .api.routes import router as api_router
from .security.authentication_lab import auth_lab
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


def create_app() -> FastAPI:
    """Create and configure FastAPI application."""
    settings = get_settings()
    
    app = FastAPI(
        title=settings.app_name,
        description="Educational cybersecurity testing tool for authorized security testing",
        version=settings.app_version,
        docs_url="/docs",
        redoc_url="/redoc"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],  # Configure appropriately for production
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
    
    # Include API routes
    app.include_router(api_router, prefix="/api")
    
    # Include authentication lab routes
    app.include_router(auth_lab.app.router, prefix="/auth-lab")
    
    @app.on_event("startup")
    async def startup_event():
        """Startup event handler."""
        logger.info(f"Starting {settings.app_name} v{settings.app_version}")
        logger.info(f"Lab Mode: {settings.lab_mode}")
        
        if not settings.lab_mode:
            logger.warning("⚠️  LAB MODE IS DISABLED - Safety restrictions are not active!")
    
    @app.on_event("shutdown")
    async def shutdown_event():
        """Shutdown event handler."""
        logger.info("Shutting down...")
    
    return app


# Create app instance
app = create_app()


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
