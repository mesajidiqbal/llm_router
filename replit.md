# LLM Routing Service

## Project Overview

This is an intelligent LLM request routing service built with Python 3.12, FastAPI, and Pydantic v2. The service routes chat requests across multiple LLM providers (OpenAI and Google) with sophisticated features including:

- Circuit breaker pattern for resilience
- Rate limiting per provider
- Cost optimization and budget enforcement
- Automatic fallback handling
- Comprehensive metrics tracking

## Architecture

### Core Components

1. **Provider Registry** (`app/config.py`): Defines static provider specifications including costs, latency, rate limits, and specialties

2. **Data Models** (`app/models.py`): Pydantic v2 models for requests, responses, and provider status

3. **Memory Store** (`app/storage/memory.py`): Thread-safe singleton for tracking provider health, metrics, and user budgets

4. **Classification** (`app/routing/classifier.py`): Analyzes prompts to determine request type (code/writing/analysis)

5. **Circuit Breaker** (`app/routing/circuit_breaker.py`): Implements CLOSED/OPEN/HALF_OPEN pattern with 3-failure threshold and 60s recovery

6. **Routing Strategy** (`app/routing/strategy.py`): Intelligent provider selection based on classification, availability, cost, and user preferences

7. **Mock Providers** (`app/providers/factory.py`): Deterministic mock implementations with 10% random failure rate

8. **Router Service** (`app/main.py`): FastAPI application with endpoints for chat, analytics, and provider management

## Recent Changes

**November 24, 2025**: Initial implementation completed
- Full project scaffold created with all modules
- All Phase 1, 2, and 3 features implemented
- FastAPI server running successfully on port 5000
- All endpoints tested and working
- Docker configuration created
- Complete documentation written (README, ROUTING_STRATEGY, Bonus)

## User Preferences

**Not specified yet** - This project follows the specification requirements exactly as provided.

## Project Structure

```
.
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI app & RouterService
│   ├── models.py               # Pydantic models
│   ├── config.py               # Provider registry
│   ├── providers/
│   │   ├── __init__.py
│   │   ├── base.py             # Abstract provider client
│   │   └── factory.py          # Mock provider implementation
│   ├── routing/
│   │   ├── __init__.py
│   │   ├── classifier.py       # Prompt classification
│   │   ├── circuit_breaker.py  # Circuit breaker pattern
│   │   ├── strategy.py         # Routing strategy
│   │   └── metrics.py          # Metrics service
│   └── storage/
│       ├── __init__.py
│       └── memory.py           # In-memory state store
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Docker configuration
├── docker-compose.yml          # Docker Compose setup
├── README.md                   # Main documentation
├── ROUTING_STRATEGY.md         # Routing algorithm explanation
├── Bonus.md                    # User budget feature docs
└── .gitignore                  # Git ignore rules

## Technical Decisions

### Python Version
- **Specification called for Python 3.13**, but used Python 3.12 in Replit
- **Reason**: Python 3.13 is only available as `python-base-3.13` (interpreter only) in Replit, while Python 3.12 includes full tooling (pip, poetry, pyright, debugpy)
- **Impact**: None - the code doesn't use Python 3.13-specific features

### Package Management
- Using `pip` with `requirements.txt`
- Installed via: `pip install -r requirements.txt`

### Environment Configuration
- Python module: `python-3.12`
- Nix packages: `libxcrypt`, `libyaml`

## Running the Service

The service is configured to run automatically via the workflow. The server runs on port 5000 and is accessible via the webview.

### Manual Run
```bash
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 5000
```

## Key Features Implemented

✅ Provider registry with OpenAI (gpt-5.1) and Google (gemini-pro)
✅ Pydantic v2 models for all data structures
✅ Thread-safe in-memory state store with asyncio locks
✅ Prompt classification (code/writing/analysis)
✅ Circuit breaker with 3-failure threshold and 60s recovery
✅ Intelligent routing: classify → filter → rank → boost → fallback
✅ Mock providers with deterministic randomness (seed=42)
✅ 10% random failure simulation
✅ Rate limiting with rolling 60s windows
✅ User budget enforcement ($1.00 cap)
✅ Comprehensive metrics (global + per-provider)
✅ FastAPI endpoints: /chat/completions, /providers, /routing/analytics, /simulate/failure
✅ Docker containerization
✅ Complete documentation

## API Endpoints

- **POST /chat/completions**: Route a chat request
- **GET /providers**: Get provider status and metrics
- **GET /routing/analytics**: Get global and per-provider analytics
- **POST /simulate/failure**: Simulate provider downtime for testing

See [README.md](README.md) for detailed API documentation and curl examples.

## Future Enhancements

The specification includes a migration path to PostgreSQL 18.0:
- Add PostgreSQL service to docker-compose
- Implement SQLModel/SQLAlchemy async tables
- Migrate MemoryStore to database-backed repository
- Persist provider health, user spend, and request metrics

## Dependencies

Core:
- fastapi - Web framework
- uvicorn - ASGI server
- pydantic - Data validation (v2)
- pydantic-settings - Settings management

Additional:
- httpx - Async HTTP client
- PyYAML - YAML parsing
- python-dotenv - Environment variables

## Notes

- LSP errors about imports not resolved are cosmetic (packages are installed and working)
- The service uses deterministic randomness (seed=42) for reproducible mock behavior
- Average latency metrics are computed only over successful requests
- Rate limit errors don't count as circuit breaker failures (by design)
