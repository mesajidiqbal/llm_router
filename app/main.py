"""
Main application module for the LLM Routing Service.

Contains the create_app factory function for configuring and initializing
the FastAPI application with all routers, middleware, and error handlers.
"""

from fastapi import FastAPI

from app.api import analytics_router, chat_router, health_router, providers_router
from app.logging_config import configure_logging
from app.middleware import register_error_handlers, register_middleware


def create_app() -> FastAPI:
    """
    Creates and configures the FastAPI application instance.

    Sets up logging, middleware, error handlers, and API routers.

    Dependency injection is handled through app/dependencies.py using
    @lru_cache() for singleton management.

    Returns:
        Configured FastAPI application
    """
    configure_logging()

    app = FastAPI(
        title="LLM Routing Service",
        description="Intelligent LLM request routing with circuit breakers, rate limiting, and cost optimization.",
        version="1.0.0",
    )

    # Register middleware and error handlers
    register_error_handlers(app)
    register_middleware(app)

    # Include routers
    app.include_router(health_router)
    app.include_router(chat_router)
    app.include_router(providers_router)
    app.include_router(analytics_router)

    return app


app = create_app()
