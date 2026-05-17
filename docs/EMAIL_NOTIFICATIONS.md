# Email Notifications

This project sends email notifications through Resend using the official Python
SDK only. The implementation extends the existing notifications feature and
keeps existing API responses backward compatible.

## Dependency

The official Resend Python SDK is already configured in `requirements.txt`:

```text
resend==2.0.0
```

Install project dependencies with:

```bash
pip install -r requirements.txt
```

## Environment Variables

Add these values to `.env`:

```bash
RESEND_API_KEY=
EMAIL_ENABLED=true
EMAIL_FROM=noreply@yourdomain.com
```

`RESEND_API_KEY` is required before real delivery can happen.
`EMAIL_ENABLED=false` disables delivery without breaking core workflows.
`EMAIL_FROM` must be a sender address allowed by your Resend account/domain.

The older `RESEND_FROM_EMAIL` and `RESEND_FROM_NAME` settings remain supported
for backward compatibility.

## Trigger Flow

Email is queued only after the core operation succeeds.

```text
Route -> Service -> Repository -> Database
                    -> NotificationService -> EmailService -> Resend SDK
```

Email delivery failure does not fail the original transaction, pricing, or
account operation. Failures are logged and the notification record is marked as
failed when possible.

## Current Email Triggers

Transaction completed:

```text
Subject: Laundry Transaction Receipt
```

Triggered when a payment transitions to `success` through manual status update,
Daraja callback, or STK status query.

Digital rate card:

```text
POST /pricing/rate-card/email
Subject: Laundry Service Rate Card
```

Authenticated users can request a service rate card by email.

Account notifications:

```text
Subject: Account Notification
```

Triggered for:

- user registration
- admin-created user accounts
- account profile updates
- password reset notification requests

## Password Reset Notification

Request endpoint:

```text
POST /auth/password-reset
```

The endpoint returns a generic response and does not reveal whether the email
exists.

## Testing

Run email notification tests:

```bash
pytest tests/test_email_notifications.py -v
```

The tests use mocked Resend clients/providers and do not send real emails.

