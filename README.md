# LLM Routing Service

An intelligent LLM request routing service built with Python 3.13, FastAPI, and Pydantic v2. This service routes chat requests across multiple LLM providers (OpenAI, Google) with circuit breaker patterns, rate limiting, cost optimization, and automatic fallback handling.

## Features

- **Intelligent Routing**: Classifies prompts and routes to the best provider based on user preferences (cost, speed, or quality)
- **Circuit Breaker**: Automatically detects failing providers and routes around them
- **Rate Limiting**: Per-provider rolling 60-second rate limit enforcement
- **Cost Optimization**: Estimates costs and respects per-request budget caps
- **User Budgets**: Enforces $1.00 spending cap per user
- **Automatic Fallback**: Tries multiple providers in order until success
- **Comprehensive Metrics**: Global and per-provider analytics

## Running Locally

### Prerequisites
- Python 3.13+
- pip

### Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
```

2. Run the service:
```bash
uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

The service will be available at `http://localhost:8000`

## Running with Docker

### Quick Start

```bash
docker compose up
```

The service will be available at `http://localhost:8000`

### Build and run manually

```bash
docker build -t llm-router .
docker run -p 8000:8000 llm-router
```

## API Endpoints

### POST /chat/completions

Send a chat request to be routed to the best available provider.

**Request:**
```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a Python function to calculate fibonacci numbers",
    "preferences": {
      "priority": "cost",
      "max_cost_per_request": 0.01,
      "timeout_ms": 5000
    },
    "user_id": "user123"
  }'
```

**Response:**
```json
{
  "provider_used": "google",
  "content": "Mock response from google: Write a Python function to calculate fibonacci...",
  "latency_ms": 252,
  "cost": 0.000675
}
```

### GET /providers

Get status of all providers including circuit breaker status and metrics.

**Request:**
```bash
curl http://localhost:8000/providers
```

**Response:**
```json
[
  {
    "name": "openai",
    "model": "gpt-5.1",
    "cost_per_token": 0.00002,
    "latency_ms": 200,
    "rate_limit_rpm": 100,
    "specialties": ["code", "analysis", "writing"],
    "quality_score": 0.95,
    "is_down": false,
    "circuit_status": "CLOSED",
    "success_rate": 0.89
  },
  {
    "name": "google",
    "model": "gemini-pro",
    "cost_per_token": 0.000015,
    "latency_ms": 250,
    "rate_limit_rpm": 150,
    "specialties": ["writing", "analysis"],
    "quality_score": 0.94,
    "is_down": false,
    "circuit_status": "CLOSED",
    "success_rate": 0.92
  }
]
```

### GET /routing/analytics

Get comprehensive analytics including global and per-provider metrics.

**Request:**
```bash
curl http://localhost:8000/routing/analytics
```

**Response:**
```json
{
  "global": {
    "total_requests": 150,
    "total_success": 135,
    "total_failures": 15,
    "avg_latency_ms": 215.3,
    "total_cost": 0.0456,
    "success_rate": 0.9
  },
  "providers": {
    "openai": {
      "requests": 70,
      "success": 62,
      "failures": 8,
      "success_rate": 0.886,
      "avg_latency_ms": 203.4,
      "is_down": false,
      "circuit_status": "CLOSED"
    },
    "google": {
      "requests": 80,
      "success": 73,
      "failures": 7,
      "success_rate": 0.9125,
      "avg_latency_ms": 225.8,
      "is_down": false,
      "circuit_status": "CLOSED"
    }
  }
}
```

### POST /simulate/failure

Simulate provider failures for testing circuit breaker behavior.

**Request:**
```bash
curl -X POST http://localhost:8000/simulate/failure \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "down": true
  }'
```

**Response:**
```json
{
  "message": "Provider openai set to down=true"
}
```

To bring the provider back up:
```bash
curl -X POST http://localhost:8000/simulate/failure \
  -H "Content-Type: application/json" \
  -d '{
    "provider": "openai",
    "down": false
  }'
```

## User Preferences

### Priority Options

- **`cost`** (default): Selects the cheapest provider
- **`speed`**: Selects the fastest provider
- **`quality`**: Selects the highest quality provider

### Max Cost Per Request

Set a budget cap for individual requests. Providers exceeding this cost will be filtered out.

```json
{
  "preferences": {
    "priority": "quality",
    "max_cost_per_request": 0.005
  }
}
```

### User Budget Enforcement

Each user has a total spending cap of $1.00. Once exceeded, requests return HTTP 402 (Payment Required).

```json
{
  "prompt": "Hello world",
  "user_id": "user123"
}
```

## Architecture

The service implements a sophisticated routing strategy:

1. **Classification**: Analyzes prompts to determine type (code, writing, analysis)
2. **Filtering**: Removes unavailable providers and those exceeding budget
3. **Ranking**: Sorts by user priority (cost/speed/quality)
4. **Boosting**: Prioritizes providers with matching specialties
5. **Fallback**: Automatically tries next provider on failure

See [ROUTING_STRATEGY.md](ROUTING_STRATEGY.md) for detailed explanation.

## Documentation

- [ROUTING_STRATEGY.md](ROUTING_STRATEGY.md) - Detailed routing algorithm explanation
- [Bonus.md](Bonus.md) - User budget enforcement details

## Interactive API Documentation

Once the service is running, visit:

- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc
