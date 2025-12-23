"""
Correlation IDs used across the system.

- request_id: per HTTP request (provided by `asgi-correlation-id`)
- transaction_id: for transaction lifecycle logs/events
- idempotency_key: for safely retryable creates
"""

REQUEST_ID_HEADER = "X-Request-Id"
TRANSACTION_ID_HEADER = "X-Transaction-Id"
IDEMPOTENCY_KEY_HEADER = "Idempotency-Key"

CTX_REQUEST_ID = "request_id"
CTX_TRANSACTION_ID = "transaction_id"
CTX_IDEMPOTENCY_KEY = "idempotency_key"


