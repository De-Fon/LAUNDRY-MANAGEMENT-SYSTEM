from app.apps.idempotency.providers import provide_idempotency_repository
from app.apps.idempotency.service import IdempotencyService
from app.apps.payments.providers import provide_daraja_client, provide_payment_repository
from app.apps.payments.service import PaymentService
from app.core.database import SessionLocal
from app.core.settings import get_settings


def reconcile_pending_mpesa_payments(limit: int = 50) -> int:
    settings = get_settings()
    service = PaymentService(
        provide_payment_repository(),
        IdempotencyService(provide_idempotency_repository()),
        provide_daraja_client(settings),
        settings,
    )
    db = SessionLocal()
    try:
        return service.reconcile_due_payments(db, limit=limit)
    finally:
        db.close()
