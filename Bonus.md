# Bonus Feature: User Budget Enforcement

## Overview

The LLM Routing Service implements a per-user spending cap of **$1.00** total across all requests. This prevents cost overruns and enables predictable billing for multi-tenant deployments.

## How It Works

### Budget Tracking

Each user is identified by an optional `user_id` field in the chat request:

```json
{
  "prompt": "Your prompt here",
  "user_id": "user123",
  "preferences": {
    "priority": "quality"
  }
}
```

If `user_id` is provided:
1. The system checks current total spend for that user
2. If spend exceeds $1.00, the request is rejected with HTTP 402 (Payment Required)
3. If within budget, the request proceeds normally
4. After successful completion, the response cost is added to the user's total spend

### Storage

User spending is tracked in-memory using the `MemoryStore` singleton:

```python
user_spend: dict[str, float]  # user_id -> total_cost
```

Thread-safe operations ensure concurrent requests don't corrupt the budget counters.

### Budget Check Flow

```
1. Request arrives with user_id="user123"
2. Query: get_user_spend("user123") → $0.87
3. Check: $0.87 <= $1.00 ✓ (proceed)
4. Route request to provider
5. Receive response with cost=$0.05
6. Update: add_user_spend("user123", $0.05)
7. New total: $0.92
8. Return response to client
```

### Budget Exceeded Response

When a user exceeds their $1.00 limit:

**HTTP Status**: 402 Payment Required

**Response Body**:
```json
{
  "detail": "Budget exceeded"
}
```

This standard HTTP status code signals that the user needs to add funds or upgrade their plan before making additional requests.

## Implementation Details

### Cost Calculation

Costs are estimated using the same formula as the routing strategy:

```python
tokens = ceil(len(prompt) / 4)
cost = tokens × provider.cost_per_token
```

Actual costs from the `ChatResponse` are used for budget accounting, ensuring accuracy even if the mock provider's actual latency differs slightly from the estimate.

### Anonymous Requests

If `user_id` is not provided (or is `null`), no budget tracking occurs. The request proceeds without spending limits. This is useful for:

- Testing and development
- Anonymous public endpoints
- Internal system requests

### Resetting Budgets

In the current in-memory implementation, budgets reset when the service restarts. For production deployments, consider:

- Periodic budget resets (daily/monthly)
- Database persistence for budget tracking across restarts
- Admin endpoints to adjust or reset user budgets

### Future Enhancements

**Database Persistence**: When migrating to PostgreSQL (see spec appendix), user budgets will be stored in a `UserSpend` table with a `total_spend` column.

**Budget Tiers**: Different users could have different spending caps based on subscription level.

**Soft Limits**: Warn users at 80% budget utilization before hard cutoff.

**Budget Analytics**: Track spending patterns per user for insights and optimization.

## Testing the Feature

1. Make a request with a user_id:
```bash
curl -X POST http://localhost:8000/chat/completions \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Write a very long essay about the history of computing with lots of details and examples",
    "user_id": "testuser"
  }'
```

2. Repeat the request multiple times until total cost exceeds $1.00

3. Observe the 402 response:
```json
{
  "detail": "Budget exceeded"
}
```

4. Check analytics to see the user's total spend:
```bash
curl http://localhost:8000/routing/analytics
```

## Security Considerations

- User IDs should be authenticated (not shown in this implementation)
- In production, validate user_id against a session or JWT token
- Rate limiting prevents budget exhaustion attacks
- Consider adding audit logs for budget-related events
