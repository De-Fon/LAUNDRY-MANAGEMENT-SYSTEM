from datetime import date

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from app.apps.order_management.models import OrderStatus, OrderStatusLog, VALID_TRANSITIONS
from app.apps.order_management.repository import OrderRepository
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

        profile = self.repository.create_vendor_profile(db, VendorProfile(vendor_id=vendor_id, **data.model_dump()))

        capacity = VendorCapacity(
            vendor_id=vendor_id,
            date=date.today(),
            total_slots=profile.max_orders_per_day,
            booked_slots=0,
            available_slots=profile.max_orders_per_day,
        )
        self.repository.create_vendor_capacity(db, capacity)
        return VendorProfileResponse.model_validate(profile)

    def update_profile(
        self,
        db: Session,
        vendor_id: int,
        data: VendorProfileUpdate,
    ) -> VendorProfileResponse:
        profile = self.repository.update_vendor_profile(db, vendor_id, data)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
        return VendorProfileResponse.model_validate(profile)

    def toggle_open_status(
        self,
        db: Session,
        vendor_id: int,
        is_open: bool,
    ) -> VendorProfileResponse:
        profile = self.repository.toggle_vendor_open(db, vendor_id, is_open)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")
        return VendorProfileResponse.model_validate(profile)

    def fetch_dashboard(self, db: Session, vendor_id: int) -> DashboardSummaryResponse:
        today = date.today()
        profile = self.repository.get_vendor_profile(db, vendor_id)
        if profile is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor profile not found")

        orders = self.repository.get_orders_today(db, vendor_id, today)
        counts = self.repository.count_orders_by_status(db, vendor_id, today)
        revenue = round(self.repository.get_revenue_today(db, vendor_id, today), 2)
        capacity = self.repository.get_vendor_capacity(db, vendor_id, today)

        return DashboardSummaryResponse(
            vendor_id=profile.vendor_id,
            business_name=profile.business_name,
            is_open=profile.is_open,
            date=today,
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

    def bulk_update_status(
        self,
        db: Session,
        vendor_id: int,
        order_ids: list[int],
        new_status: OrderStatus,
    ) -> BulkStatusUpdateResponse:
        updated_count = 0
        for order_id in order_ids:
            order = self.order_repository.get_order_by_id_for_update(db, order_id)
            if order is None or order.vendor_id != vendor_id or VALID_TRANSITIONS.get(order.status) != new_status:
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

        return BulkStatusUpdateResponse(updated_count=updated_count)

    def check_capacity(self, db: Session, vendor_id: int, target_date: date) -> VendorCapacityResponse:
        capacity = self.repository.get_vendor_capacity(db, vendor_id, target_date)
        if capacity is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Vendor capacity not initialized")
        return VendorCapacityResponse.model_validate(capacity)

    def is_vendor_available(self, db: Session, vendor_id: int) -> bool:
        profile = self.repository.get_vendor_profile(db, vendor_id)
        capacity = self.repository.get_vendor_capacity(db, vendor_id, date.today())
        return bool(profile and profile.is_open and capacity and capacity.available_slots > 0)
