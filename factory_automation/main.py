#!/usr/bin/env python3
"""Main entry point for the Factory Automation System."""
import asyncio
import logging
from pathlib import Path
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import uvicorn
from gradio import mount_gradio_app

from factory_config.settings import settings
from factory_ui.gradio_app import create_dashboard
from factory_rag.chromadb_client import ChromaDBClient
from factory_database.models import init_db
from factory_utils.logging_config import setup_logging, get_logger

# Configure structured logging
setup_logging(
    level=settings.get("log_level", "INFO"),
    log_file=Path("logs/factory_automation.log") if settings.get("log_to_file", False) else None,
    structured=settings.get("structured_logging", False),
    colored=True
)

logger = get_logger(__name__)

# Dynamic orchestrator import based on settings
if settings.use_ai_orchestrator:
    from factory_agents.orchestrator_v2_agent import OrchestratorAgentV2 as OrchestratorAgent
else:
    from factory_agents.orchestrator_agent import OrchestratorAgent

# Log which orchestrator we're using after logger is configured
if settings.use_ai_orchestrator:
    logger.info("Using AI-powered orchestrator (v2) with function tools pattern")
else:
    logger.info("Using traditional orchestrator (v1) with handoff pattern")

# Create FastAPI app
app = FastAPI(
    title="Factory Automation System",
    description="Automated price tag order processing system",
    version="0.1.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global instances
orchestrator: Optional[OrchestratorAgent] = None
chromadb_client: Optional[ChromaDBClient] = None

@app.on_event("startup")
async def startup_event():
    """Initialize services on startup."""
    global orchestrator, chromadb_client
    
    logger.info("Initializing Factory Automation System...")
    
    # Initialize database
    logger.info("Setting up database...")
    await init_db()
    
    # Initialize ChromaDB
    logger.info("Connecting to ChromaDB...")
    chromadb_client = ChromaDBClient()
    await chromadb_client.initialize()
    
    # Initialize orchestrator agent
    orchestrator_type = "AI-powered (v2)" if settings.use_ai_orchestrator else "Traditional (v1)"
    logger.info(f"Starting {orchestrator_type} orchestrator agent...")
    orchestrator = OrchestratorAgent(chromadb_client)
    
    # Start email monitoring in background
    if settings.app_env == "production":
        asyncio.create_task(orchestrator.start_email_monitoring())
    
    logger.info("System initialization complete!")

@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown."""
    logger.info("Shutting down Factory Automation System...")
    if orchestrator:
        await orchestrator.stop()

@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "message": "Factory Automation System is running",
        "version": "0.1.0",
        "status": "healthy"
    }

@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "chromadb": chromadb_client.is_connected() if chromadb_client else False,
        "agent": orchestrator.is_running() if orchestrator else False
    }

# Mount Gradio app
gradio_app = create_dashboard()
app = mount_gradio_app(app, gradio_app, path="/dashboard")

def main():
    """Run the application."""
    logger.info(f"Starting server on port {settings.app_port}...")
    logger.info(f"Gradio dashboard available at http://localhost:{settings.app_port}/dashboard")
    
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=settings.app_port,
        reload=settings.app_env == "development"
    )

if __name__ == "__main__":
    main()