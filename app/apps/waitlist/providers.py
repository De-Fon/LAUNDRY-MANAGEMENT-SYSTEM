from typing import Annotated

from fastapi import Depends

from app.apps.waitlist.repository import WaitlistRepository
from app.apps.waitlist.service import WaitlistService


def provide_waitlist_repository() -> WaitlistRepository:
    return WaitlistRepository()


def provide_waitlist_service(
    repository: Annotated[WaitlistRepository, Depends(provide_waitlist_repository)],
) -> WaitlistService:
    return WaitlistService(repository)

