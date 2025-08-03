#!/usr/bin/env python3
"""Run the application with email monitoring enabled in development mode."""

import asyncio
import sys
from pathlib import Path

# Add project root to path
sys.path.append(str(Path(__file__).parent / "factory_automation"))

# Override the environment check before importing main
import os

os.environ["APP_ENV"] = (
    "production"  # Temporarily set to production to enable monitoring
)

from factory_automation.main import app
from factory_automation.factory_config.settings import settings
import uvicorn


async def run_with_monitoring():
    """Run the app with email monitoring enabled."""
    print("\n" + "=" * 60)
    print("FACTORY AUTOMATION WITH EMAIL MONITORING")
    print("=" * 60)

    # Check configuration
    if not settings.gmail_delegated_email:
        print("\nERROR: GMAIL_DELEGATED_EMAIL not configured!")
        print("Please add to your .env file:")
        print("GMAIL_DELEGATED_EMAIL=your-email@company.com")
        return

    print("\nConfiguration:")
    print(
        f"- AI Orchestrator: {'Enabled' if settings.use_ai_orchestrator else 'Disabled'}"
    )
    print(f"- Monitoring Email: {settings.gmail_delegated_email}")
    print(f"- Poll Interval: {settings.email_poll_interval} seconds")
    print(f"- Dashboard: http://localhost:{settings.app_port}/dashboard")
    print("\nStarting server with email monitoring...\n")

    # Run the FastAPI app
    config = uvicorn.Config(
        app,
        host="0.0.0.0",
        port=settings.app_port,
        reload=False,  # Disable reload to maintain background tasks
        log_level="info",
    )
    server = uvicorn.Server(config)
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(run_with_monitoring())
    except KeyboardInterrupt:
        print("\nShutting down...")
