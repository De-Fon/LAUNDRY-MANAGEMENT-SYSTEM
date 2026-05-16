# Daraja Payment Integration

## Overall Architecture

The payment flow keeps the backend architecture layered:

```text
Route -> Service -> Repository -> Database
                -> Integration Client -> Safaricom Daraja
```

Routes only expose HTTP endpoints. `PaymentService` owns business rules, the payment state machine, idempotency decisions, callback processing, and reconciliation. `PaymentRepository` owns SQLAlchemy persistence. `DarajaClient` owns OAuth, STK password generation, STK Push, and STK Query HTTP calls.

## Payment Lifecycle

1. A student calls `POST /payments/stk-push`.
2. The service validates ownership of the order and normalizes the phone number.
3. A `Payment` and `PaymentAttempt` are created.
4. Daraja accepts or rejects the STK Push request.
5. If accepted, the payment moves from `pending` to `processing`.
6. Safaricom later calls `POST /payments/callback`.
7. The callback is logged by payload hash, then applied idempotently.
8. If callbacks fail or never arrive, reconciliation calls STK Query for due processing payments.

## State Machine

Allowed transitions:

```text
pending -> processing | failed | cancelled | timeout
processing -> success | failed | cancelled | timeout | reversed
success -> reversed
failed -> terminal
cancelled -> terminal
timeout -> terminal
reversed -> terminal
```

Payments are asynchronous because STK Push only means Safaricom accepted the prompt request. The actual customer action happens later on the phone. Callbacks can be delayed, duplicated, lost, or arrive after a query result, so every provider event is logged and every terminal transition is guarded.

## Files

`app/apps/payments/models.py`
Defines `Payment`, `PaymentAttempt`, `Transaction`, `CallbackLog`, and `PaymentStatusHistory`. These tables make the lifecycle auditable.

`app/apps/payments/schemas.py`
Defines API contracts for STK Push, STK Query, callbacks, payment reads, and error responses.

`app/apps/payments/repository.py`
Contains database queries and persistence helpers only.

`app/apps/payments/service.py`
Contains payment workflows, state transitions, callback idempotency, Daraja result mapping, and reconciliation.

`app/apps/payments/routes.py`
Exposes the HTTP API while delegating all work to the service layer.

`app/apps/payments/providers.py`
Wires repository, idempotency service, settings, and Daraja client through FastAPI dependency injection.

`app/integrations/daraja/client.py`
Isolates Safaricom HTTP behavior: OAuth token generation, token caching, STK password generation, STK Push, and STK Query.

`app/utils/phone.py`
Normalizes Kenyan phone numbers into `2547...` or `2541...` format before sending to Daraja.

`app/workers/payment_reconciliation.py`
Provides an entry point for a scheduler or worker to query overdue processing payments.

`alembic/versions/20260516_0002_daraja_payments.py`
Adds Daraja lifecycle columns and audit tables.

## Environment Setup

Add these to `.env`:

```env
DARAJA_ENVIRONMENT=sandbox
DARAJA_CONSUMER_KEY=your_sandbox_consumer_key
DARAJA_CONSUMER_SECRET=your_sandbox_consumer_secret
DARAJA_BUSINESS_SHORT_CODE=174379
DARAJA_PASSKEY=your_sandbox_lipa_na_mpesa_passkey
DARAJA_CALLBACK_URL=https://your-public-url.example.com/payments/callback
DARAJA_ACCOUNT_REFERENCE_PREFIX=HELB
DARAJA_TRANSACTION_DESC=Loan repayment
DARAJA_REQUEST_TIMEOUT_SECONDS=30
DARAJA_STK_TIMEOUT_MINUTES=3
DARAJA_RECONCILIATION_INTERVAL_MINUTES=2
DARAJA_MAX_QUERY_RETRIES=5
```

For local callback testing, expose the app with ngrok and set `DARAJA_CALLBACK_URL` to the HTTPS ngrok URL plus `/payments/callback`.

## API Endpoints

`POST /payments/stk-push`
Authenticated. Creates a payment attempt and sends the STK prompt. Returns `202` because final payment status is async.

`GET /payments/{id}`
Authenticated. Returns a payment if the caller owns it, or is vendor/admin.

`GET /payments/status/{checkout_request_id}`
Queries Daraja and applies the result to the local payment.

`POST /payments/callback`
Public provider webhook. Logs raw payload, deduplicates by hash, applies final state, and records transaction details.

## Reconciliation

Run the worker function from a scheduler:

```bash
python -c "from app.workers.payment_reconciliation import reconcile_pending_mpesa_payments; print(reconcile_pending_mpesa_payments())"
```

Production should run this on a fixed interval using Celery, APScheduler, cron, or a managed worker.

## Debugging

Token errors usually mean consumer key/secret mismatch or the sandbox app is not enabled for the API.

Callback failures usually mean the callback URL is not public HTTPS, ngrok changed URLs, or the app returned non-2xx.

Timeouts mean the customer did not complete the prompt in time, the handset was offline, or Daraja did not deliver a callback. Reconciliation should query the checkout request.

Duplicate callbacks are expected. The callback table uses a payload hash unique constraint so retry delivery does not double-credit a payment.

Never log Daraja secrets, OAuth tokens, passkeys, or full authorization headers.
