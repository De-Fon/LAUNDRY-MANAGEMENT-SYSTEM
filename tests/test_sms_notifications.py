from datetime import UTC, datetime, timedelta

from sqlalchemy import select

from app.apps.bookings.repository import BookingRepository
from app.apps.bookings.schemas import BookingCreate, BookingItemCreate
from app.apps.bookings.service import BookingService
from app.apps.catalog.models import Category, ServiceItem
from app.apps.catalog.repository import CatalogRepository
from app.apps.notifications.models import Notification, NotificationChannel, NotificationStatus
from app.apps.notifications.repository import NotificationRepository
from app.apps.notifications.service import (
    LAUNDRY_COMPLETED_SMS,
    PICKUP_CREATED_SMS,
    NotificationService,
)
from app.apps.notifications.sms import AfricaTalkingSandboxSMSProvider, SMSSendResult, SMSService
from app.apps.order_management.models import Order, OrderStatus
from app.apps.order_management.repository import OrderRepository
from app.apps.order_management.schemas import OrderStatusUpdate
from app.apps.order_management.service import OrderService
from app.apps.pricing.models import WashType
from app.apps.pricing.repository import PricingRepository


class FakeSMSProvider:
    def __init__(self) -> None:
        self.sent: list[tuple[str, str]] = []

    def send_sms(self, to_phone: str, message: str) -> SMSSendResult:
        self.sent.append((to_phone, message))
        return SMSSendResult(success=True, provider="fake", status="sent")


class FakeNotificationService:
    def __init__(self) -> None:
        self.pickups: list[int] = []
        self.status_updates: list[tuple[int, str]] = []
        self.completed: list[int] = []

    def notify_pickup_created(self, db, background_tasks, *, user_id: int) -> None:
        self.pickups.append(user_id)

    def notify_order_status_changed(self, db, background_tasks, *, user_id: int, order_status: str) -> None:
        self.status_updates.append((user_id, order_status))

    def notify_laundry_completed(self, db, background_tasks, *, user_id: int) -> None:
        self.completed.append(user_id)


class FakeHTTPResponse:
    def raise_for_status(self) -> None:
        return None

    def json(self) -> dict:
        return {
            "SMSMessageData": {
                "Recipients": [
                    {
                        "number": "0700000001",
                        "status": "Success",
                        "messageId": "ATXid_test",
                    }
                ]
            }
        }


class FakeHTTPClient:
    def __init__(self) -> None:
        self.requests: list[dict] = []

    def post(self, url: str, *, data: dict, headers: dict) -> FakeHTTPResponse:
        self.requests.append({"url": url, "data": data, "headers": headers})
        return FakeHTTPResponse()


def create_service_item(db_session) -> ServiceItem:
    category = Category(name="Laundry", description="Laundry services")
    db_session.add(category)
    db_session.flush()
    service_item = ServiceItem(category_id=category.id, name="Wash", base_price=100.0)
    db_session.add(service_item)
    db_session.flush()
    return service_item


def test_africastalking_sandbox_provider_posts_to_sandbox_endpoint():
    client = FakeHTTPClient()
    provider = AfricaTalkingSandboxSMSProvider(client=client)
    original_sms_enabled = provider.settings.sms_enabled
    original_api_key = provider.settings.africastalking_api_key
    original_username = provider.settings.africastalking_username
    original_sender_id = provider.settings.africastalking_sender_id
    provider.settings.sms_enabled = True
    provider.settings.africastalking_api_key = "sandbox-key"
    provider.settings.africastalking_username = "sandbox"
    provider.settings.africastalking_sender_id = ""

    try:
        result = provider.send_sms("0700000001", PICKUP_CREATED_SMS)
    finally:
        provider.settings.sms_enabled = original_sms_enabled
        provider.settings.africastalking_api_key = original_api_key
        provider.settings.africastalking_username = original_username
        provider.settings.africastalking_sender_id = original_sender_id

    assert result.success is True
    assert client.requests[0]["url"] == "https://api.sandbox.africastalking.com/version1/messaging"
    assert client.requests[0]["data"]["username"] == "sandbox"
    assert client.requests[0]["data"]["to"] == "0700000001"
    assert client.requests[0]["data"]["message"] == PICKUP_CREATED_SMS
    assert client.requests[0]["headers"]["apiKey"] == "sandbox-key"


def test_notification_service_sends_sms_with_mock_provider(db_session, test_student):
    provider = FakeSMSProvider()
    service = NotificationService(NotificationRepository(), SMSService(provider))

    service.notify_pickup_created(db_session, None, user_id=test_student.id)

    notification = db_session.scalar(select(Notification).where(Notification.user_id == test_student.id))
    assert notification is not None
    assert notification.channel == NotificationChannel.sms
    assert notification.status == NotificationStatus.sent
    assert notification.message == PICKUP_CREATED_SMS
    assert provider.sent == [(test_student.phone, PICKUP_CREATED_SMS)]


def test_booking_creation_triggers_pickup_sms(db_session, test_student):
    service_item = create_service_item(db_session)
    notification_service = FakeNotificationService()
    service = BookingService(BookingRepository(), notification_service)

    booking = service.create_booking(
        db_session,
        test_student,
        BookingCreate(
            pickup_address="Main campus gate",
            pickup_at=datetime.now(UTC) + timedelta(days=1),
            items=[BookingItemCreate(service_item_id=service_item.id, quantity=2)],
        ),
    )

    assert booking.customer_id == test_student.id
    assert notification_service.pickups == [test_student.id]


def test_order_ready_status_triggers_update_and_completion_sms(db_session, test_student, test_vendor):
    service_item = create_service_item(db_session)
    wash_type = WashType(name="Normal", price_multiplier=1.0, duration_hours=24)
    db_session.add(wash_type)
    db_session.flush()
    order = Order(
        order_code="ORD-SMS001",
        student_id=test_student.id,
        vendor_id=test_vendor.id,
        service_item_id=service_item.id,
        wash_type=wash_type.name,
        quantity=1,
        total_price=100.0,
        status=OrderStatus.DRYING,
    )
    db_session.add(order)
    db_session.commit()
    db_session.refresh(order)
    notification_service = FakeNotificationService()
    service = OrderService(
        OrderRepository(),
        CatalogRepository(),
        PricingRepository(),
        notification_service,
    )

    updated_order = service.update_status(
        db_session,
        order.id,
        OrderStatusUpdate(status=OrderStatus.READY),
        test_vendor.id,
    )

    assert updated_order.status == OrderStatus.READY
    assert notification_service.status_updates == [(test_student.id, OrderStatus.READY.value)]
    assert notification_service.completed == [test_student.id]
