"""
Middleware and error handlers for the LLM Router service.

This module contains HTTP middleware for logging and request tracking,
as well as custom exception handlers for service-specific errors.
"""

import time
import uuid

import structlog
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

from app.exceptions import LLMException, ServiceUnavailableError


async def logging_middleware(request: Request, call_next):
    """
    HTTP middleware that logs all requests and responses with timing information.

    Assigns a unique request ID to each request for tracing and logs the
    request method, path, status code, and latency. The request ID is also
    added to response headers as 'X-Request-ID' for debugging.

    Args:
        request: The incoming HTTP request
        call_next: Function to call the next middleware/endpoint

    Returns:
        Response from the endpoint with X-Request-ID header
    """
    request_id = str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(request_id=request_id)

    start_time = time.time()
    try:
        response = await call_next(request)
        process_time = time.time() - start_time

        # Add request ID to response headers for debugging
        response.headers["X-Request-ID"] = request_id

        structlog.get_logger().info(
            "http_request",
            method=request.method,
            path=request.url.path,
            status_code=response.status_code,
            latency_s=process_time,
        )
        return response
    except Exception as e:
        process_time = time.time() - start_time
        structlog.get_logger().error(
            "request_failed",
            method=request.method,
            path=request.url.path,
            latency_s=process_time,
            error=str(e),
        )
        raise


async def service_unavailable_handler(request: Request, exc: ServiceUnavailableError) -> JSONResponse:
    """
    Handler for ServiceUnavailableError exceptions.

    Returns a 503 status code when all providers are unavailable.

    Args:
        request: The HTTP request that triggered the error
        exc: The ServiceUnavailableError exception

    Returns:
        JSONResponse with 503 status code
    """
    return JSONResponse(
        status_code=503,
        content={"detail": str(exc)},
    )


async def llm_exception_handler(request: Request, exc: LLMException) -> JSONResponse:
    """
    Handler for generic LLM-related exceptions.

    Returns a 500 status code for internal LLM errors.

    Args:
        request: The HTTP request that triggered the error
        exc: The LLMException

    Returns:
        JSONResponse with 500 status code
    """
    return JSONResponse(
        status_code=500,
        content={"detail": f"Internal error: {str(exc)}"},
    )


def register_middleware(app: FastAPI) -> None:
    """
    Register all middleware with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    app.middleware("http")(logging_middleware)


def register_error_handlers(app: FastAPI) -> None:
    """
    Register all custom exception handlers with the FastAPI application.

    Args:
        app: The FastAPI application instance
    """
    app.add_exception_handler(ServiceUnavailableError, service_unavailable_handler)
    app.add_exception_handler(LLMException, llm_exception_handler)
