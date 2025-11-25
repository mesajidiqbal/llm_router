"""
API routers for the LLM Routing Service.

This package contains all API endpoint routers organized by functionality.
"""

from app.api.analytics import router as analytics_router
from app.api.chat import router as chat_router
from app.api.health import router as health_router
from app.api.providers import router as providers_router

__all__ = ["health_router", "chat_router", "providers_router", "analytics_router"]
