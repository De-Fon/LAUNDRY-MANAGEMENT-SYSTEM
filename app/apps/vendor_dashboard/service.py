from datetime import UTC, date, datetime

from fastapi import HTTPException, status
from loguru import logger
from redis import Redis
from sqlalchemy.orm import Session

from app.apps.order_management.models import Order, OrderStatus, OrderStatusLog
from app.apps.order_management.repository import OrderRepository
from app.apps.order_management.service import VALID_TRANSITIONS
from app.apps.vendor_dashboard.models import VendorCapacity, VendorProfile
from app.apps.vendor_dashboard.repository import VendorDashboardRepository
from app.apps.vendor_dashboard.schemas import (
    BulkStatusUpdateResponse,
    DashboardSummaryResponse,
    OrderSummaryResponse,
    VendorCapacityResponse,
    VendorProfileCreate,
    VendorProfileResponse,
    VendorProfileUpdate,
)


DASHBOARD_KEY = "dashboard:{vendor_id}"
DASHBOARD_TTL = 300


class VendorDashboardService:
    def __init__(
        self,
        repository: VendorDashboardRepository,
        order_repository: OrderRepository,
    ) -> None:
        self.repository = repository
        self.order_repository = order_repository

    def setup_vendor_profile(self, db: Session, vendor_id: int, data: VendorProfileCreate) -> VendorProfileResponse:
        if self.repository.get_vendor_profile(db, vendor_id) is not None:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Vendor profile already exists")

        profile = self.repository.create_vendor_profile(
            db,
            VendorProfile(vendor_id=vendor_id, **data.model_dump()),
        )
        self.repository.create_vendor_capacity(db, self._build_capacity(vendor_id, date.today(), profile.max_orders_per_day))
        self._log_profile_created(profile)
        return VendorProfileResponse.model_validate(profile)

    def update_profile(
        self,
        db: Session,
        redis_client: Redis,
        vendor_id: int,
        data: VendorProfileUpdate,
    ) -> VendorProfileResponse:
        self._get_profile_or_404(db, vendor_id)
        profile = self.repository.update_vendor_profile(db, vendor_id, data)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")

        self._invalidate_dashboard(redis_client, vendor_id)
        self._log_profile_updated(vendor_id, list(data.model_dump(exclude_unset=True).keys()))
        return VendorProfileResponse.model_validate(profile)

    def toggle_open_status(
        self,
        db: Session,
        redis_client: Redis,
        vendor_id: int,
        is_open: bool,
    ) -> VendorProfileResponse:
        self._get_profile_or_404(db, vendor_id)
        profile = self.repository.toggle_vendor_open(db, vendor_id, is_open)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")

        self._invalidate_dashboard(redis_client, vendor_id)
        self._log_status_toggled(vendor_id, is_open)
        return VendorProfileResponse.model_validate(profile)

    def fetch_dashboard(self, db: Session, redis_client: Redis, vendor_id: int) -> DashboardSummaryResponse:
        cache_key = self._dashboard_key(vendor_id)
        if cached := redis_client.get(cache_key):
            logger.info("CACHE HIT | dashboard vendor={} timestamp={}", vendor_id, self._timestamp())
            return DashboardSummaryResponse.model_validate_json(cached)

        today = date.today()
        profile = self._get_profile_or_404(db, vendor_id)
        orders = self.repository.get_orders_today(db, vendor_id, today)
        counts = self.repository.count_orders_by_status(db, vendor_id, today)
        revenue = round(self.repository.get_revenue_today(db, vendor_id, today), 2)
        capacity = self.repository.get_vendor_capacity(db, vendor_id, today)

        dashboard = self._build_dashboard(profile, today, orders, counts, revenue, capacity)
        redis_client.setex(cache_key, DASHBOARD_TTL, dashboard.model_dump_json())
        self._log_dashboard_fetched(vendor_id, len(orders), revenue)
        return dashboard

    def bulk_update_status(
        self,
        db: Session,
        redis_client: Redis,
        vendor_id: int,
        order_ids: list[int],
        new_status: OrderStatus,
    ) -> BulkStatusUpdateResponse:
        updated_count = 0
        for order_id in order_ids:
            order = self.order_repository.get_order_by_id_for_update(db, order_id)
            if order is None or order.vendor_id != vendor_id or not self._is_valid_transition(order.status, new_status):
                continue

            self.order_repository.apply_status_transition(
                db,
                order,
                new_status,
                OrderStatusLog(
                    order_id=order.id,
                    previous_status=order.status,
                    new_status=new_status,
                    changed_by=vendor_id,
                    note="Bulk status update from vendor dashboard",
                ),
            )
            updated_count += 1

        self._invalidate_dashboard(redis_client, vendor_id)
        self._log_bulk_update(vendor_id, len(order_ids), new_status)
        return BulkStatusUpdateResponse(updated_count=updated_count)

    def check_capacity(self, db: Session, vendor_id: int, target_date: date) -> VendorCapacityResponse:
        capacity = self.repository.get_vendor_capacity(db, vendor_id, target_date)
        if capacity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor capacity not initialized")

        logger.info(
            "CAPACITY CHECKED | vendor={} date={} available_slots={} timestamp={}",
            vendor_id,
            target_date,
            capacity.available_slots,
            self._timestamp(),
        )
        return VendorCapacityResponse.model_validate(capacity)

    def is_vendor_available(self, db: Session, vendor_id: int) -> bool:
        profile = self.repository.get_vendor_profile(db, vendor_id)
        capacity = self.repository.get_vendor_capacity(db, vendor_id, date.today())
        return bool(profile and profile.is_open and capacity and capacity.available_slots > 0)

    def _build_dashboard(
        self,
        profile: VendorProfile,
        target_date: date,
        orders: list[Order],
        counts: dict[OrderStatus, int],
        revenue: float,
        capacity: VendorCapacity | None,
    ) -> DashboardSummaryResponse:
        return DashboardSummaryResponse(
            vendor_id=profile.vendor_id,
            business_name=profile.business_name,
            is_open=profile.is_open,
            date=target_date,
            total_orders_today=len(orders),
            queued=counts.get(OrderStatus.QUEUED, 0),
            washing=counts.get(OrderStatus.WASHING, 0),
            drying=counts.get(OrderStatus.DRYING, 0),
            ready=counts.get(OrderStatus.READY, 0),
            waiting_to_pick=counts.get(OrderStatus.WAITING_TO_PICK, 0),
            picked_up=counts.get(OrderStatus.PICKED_UP, 0),
            total_revenue_today=revenue,
            available_slots=capacity.available_slots if capacity else 0,
            active_orders=[OrderSummaryResponse.model_validate(order) for order in orders],
        )

    def _build_capacity(self, vendor_id: int, target_date: date, total_slots: int) -> VendorCapacity:
        return VendorCapacity(
            vendor_id=vendor_id,
            date=target_date,
            total_slots=total_slots,
            booked_slots=0,
            available_slots=total_slots,
        )

    def _get_profile_or_404(self, db: Session, vendor_id: int) -> VendorProfile:
        profile = self.repository.get_vendor_profile(db, vendor_id)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
        return profile

    def _is_valid_transition(self, current_status: OrderStatus, new_status: OrderStatus) -> bool:
        return VALID_TRANSITIONS.get(current_status) == new_status

    def _dashboard_key(self, vendor_id: int) -> str:
        return DASHBOARD_KEY.format(vendor_id=vendor_id)

    def _invalidate_dashboard(self, redis_client: Redis, vendor_id: int) -> None:
        redis_client.delete(self._dashboard_key(vendor_id))

    def _log_profile_created(self, profile: VendorProfile) -> None:
        logger.info(
            "VENDOR PROFILE CREATED | vendor={} name={} max_orders={} timestamp={}",
            profile.vendor_id,
            profile.business_name,
            profile.max_orders_per_day,
            self._timestamp(),
        )

    def _log_profile_updated(self, vendor_id: int, fields: list[str]) -> None:
        logger.info("VENDOR PROFILE UPDATED | vendor={} fields={} timestamp={}", vendor_id, fields, self._timestamp())

    def _log_status_toggled(self, vendor_id: int, is_open: bool) -> None:
        label = "OPEN" if is_open else "CLOSED"
        logger.info("VENDOR STATUS TOGGLED | vendor={} status={} timestamp={}", vendor_id, label, self._timestamp())
        if not is_open:
            logger.warning("VENDOR CLOSED | vendor={} is_open=False", vendor_id)

    def _log_dashboard_fetched(self, vendor_id: int, total_orders: int, revenue: float) -> None:
        logger.info(
            "DASHBOARD FETCHED | vendor={} orders={} revenue=KES {} timestamp={}",
            vendor_id,
            total_orders,
            revenue,
            self._timestamp(),
        )

    def _log_bulk_update(self, vendor_id: int, order_count: int, new_status: OrderStatus) -> None:
        logger.info(
            "BULK STATUS UPDATE | vendor={} order_count={} new_status={} timestamp={}",
            vendor_id,
            order_count,
            new_status.value,
            self._timestamp(),
        )

    def _timestamp(self) -> str:
        return datetime.now(UTC).isoformat()
