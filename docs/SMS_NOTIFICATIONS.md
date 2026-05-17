# SMS Notifications

This project supports SMS notifications through Africa's Talking Sandbox only.
The implementation extends the existing notifications feature and does not
change existing endpoints or core business responses.

## Environment Variables

Add these values to `.env`:

```bash
AFRICASTALKING_USERNAME=sandbox
AFRICASTALKING_API_KEY=YOUR_SANDBOX_KEY
AFRICASTALKING_SENDER_ID=
SMS_ENABLED=true
```

`AFRICASTALKING_USERNAME` must remain `sandbox` for sandbox testing.
`AFRICASTALKING_API_KEY` should be the API key from the Africa's Talking
sandbox dashboard.
`AFRICASTALKING_SENDER_ID` is optional and can stay blank in sandbox tests.
`SMS_ENABLED=false` disables SMS sending without changing API behavior.

## Sandbox Usage

1. Sign in to the Africa's Talking sandbox dashboard.
2. Copy the sandbox API key into `AFRICASTALKING_API_KEY`.
3. Keep `AFRICASTALKING_USERNAME=sandbox`.
4. Start the backend:

```bash
python -m uvicorn app.main:app --reload
```

5. Trigger one of the supported workflows from Swagger UI or tests.
6. Confirm the simulated SMS in the Africa's Talking sandbox simulator.

The sandbox flow is for testing only. The code intentionally uses:

```text
https://api.sandbox.africastalking.com/version1/messaging
```

## Trigger Flow

SMS is sent after the core operation succeeds. If SMS fails, the request still
returns the normal success response for the booking or order operation.

```text
Route -> Service -> Repository -> Database
                    -> NotificationService -> SMSService -> Africa's Talking Sandbox
```

## Current SMS Triggers

Pickup request created:

```text
Your laundry pickup request has been received.
```

Order status changed:

```text
Your laundry order status changed to: {status}
```

Laundry completed, currently when an order reaches `READY`:

```text
Your laundry is ready for pickup.
```

## Error Handling

SMS failures are logged and stored as failed notification records where a record
was created successfully. SMS errors do not raise HTTP errors for booking or
order workflows.

Failures handled gracefully include:

- `SMS_ENABLED=false`
- missing `AFRICASTALKING_API_KEY`
- Africa's Talking sandbox HTTP failures
- rejected sandbox responses
- notification queue errors

## Testing

Run SMS notification tests:

```bash
pytest tests/test_sms_notifications.py -v
```

Run all notification tests:

```bash
pytest tests/test_notifications.py tests/test_sms_notifications.py -v
```

The tests use fake providers and fake HTTP clients. They do not send real SMS.

