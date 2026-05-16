from app.apps.catalog.models import Category, ServiceItem
from app.apps.idempotency.providers import provide_idempotency_repository
from app.apps.idempotency.service import IdempotencyService
from app.apps.order_management.models import Order
from app.apps.payments.models import PaymentStatus
from app.apps.payments.repository import PaymentRepository
from app.apps.payments.schemas import STKPushRequest
from app.apps.payments.service import PaymentService
from app.core.settings import get_settings


class FakeDarajaClient:
    def initiate_stk_push(self, **kwargs):
        return {
            "MerchantRequestID": "29115-34620561-1",
            "CheckoutRequestID": "ws_CO_16052026123456789",
            "ResponseCode": "0",
            "ResponseDescription": "Success. Request accepted for processing",
            "CustomerMessage": "Success. Request accepted for processing",
        }

    def query_stk_push(self, *, checkout_request_id: str):
        return {
            "ResponseCode": "0",
            "CheckoutRequestID": checkout_request_id,
            "ResultCode": "0",
            "ResultDesc": "The service request is processed successfully.",
        }


def build_payment_service():
    settings = get_settings()
    settings.daraja_callback_url = "https://example.com/payments/callback"
    return PaymentService(
        PaymentRepository(),
        IdempotencyService(provide_idempotency_repository()),
        FakeDarajaClient(),
        settings,
    )


def create_order(db_session, test_student, test_vendor):
    category = Category(name="Daraja Test", description=None, is_active=True)
    db_session.add(category)
    db_session.flush()
    service_item = ServiceItem(
        category_id=category.id,
        name="Loan repayment",
        description=None,
        base_price=150.0,
        is_active=True,
    )
    db_session.add(service_item)
    db_session.flush()
    order = Order(
        order_code="ORD-DARAJA-1",
        student_id=test_student.id,
        vendor_id=test_vendor.id,
        service_item_id=service_item.id,
        wash_type="standard",
        quantity=1,
        total_price=150.0,
        special_instructions=None,
    )
    db_session.add(order)
    db_session.flush()
    return order


def test_stk_push_creates_processing_payment(db_session, test_student, test_vendor):
    order = create_order(db_session, test_student, test_vendor)
    service = build_payment_service()

    response = service.initiate_stk_push(
        db_session,
        test_student,
        STKPushRequest(order_id=order.id, phone_number="0712345678", idempotency_key="stk-key-1"),
    )

    assert response.status == PaymentStatus.PROCESSING
    assert response.checkout_request_id == "ws_CO_16052026123456789"


def test_callback_marks_payment_success(db_session, test_student, test_vendor):
    order = create_order(db_session, test_student, test_vendor)
    service = build_payment_service()
    service.initiate_stk_push(
        db_session,
        test_student,
        STKPushRequest(order_id=order.id, phone_number="0712345678", idempotency_key="stk-key-2"),
    )

    callback_payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-1",
                "CheckoutRequestID": "ws_CO_16052026123456789",
                "ResultCode": 0,
                "ResultDesc": "The service request is processed successfully.",
                "CallbackMetadata": {
                    "Item": [
                        {"Name": "Amount", "Value": 150.0},
                        {"Name": "MpesaReceiptNumber", "Value": "TFS7RT61SV"},
                        {"Name": "TransactionDate", "Value": 20260516123456},
                        {"Name": "PhoneNumber", "Value": 254712345678},
                    ]
                },
            }
        }
    }

    service.handle_callback(db_session, callback_payload)
    payment = PaymentRepository().get_by_checkout_request_id(db_session, "ws_CO_16052026123456789")

    assert payment is not None
    assert payment.status == PaymentStatus.SUCCESS
    assert payment.provider_reference == "TFS7RT61SV"
    assert payment.paid_at is not None


def test_duplicate_callback_is_accepted_without_second_processing(db_session, test_student, test_vendor):
    order = create_order(db_session, test_student, test_vendor)
    service = build_payment_service()
    service.initiate_stk_push(
        db_session,
        test_student,
        STKPushRequest(order_id=order.id, phone_number="0712345678", idempotency_key="stk-key-3"),
    )
    payload = {
        "Body": {
            "stkCallback": {
                "MerchantRequestID": "29115-34620561-1",
                "CheckoutRequestID": "ws_CO_16052026123456789",
                "ResultCode": 1032,
                "ResultDesc": "Request cancelled by user",
            }
        }
    }

    first = service.handle_callback(db_session, payload)
    second = service.handle_callback(db_session, payload)
    payment = PaymentRepository().get_by_checkout_request_id(db_session, "ws_CO_16052026123456789")

    assert first.result_code == 0
    assert second.result_description == "Duplicate callback ignored"
    assert payment is not None
    assert payment.status == PaymentStatus.CANCELLED
