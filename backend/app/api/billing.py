from __future__ import annotations

from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.deps import get_current_user, get_db
from app.models.user import User
from app.schemas.billing import BillingHistoryResponse, BillingUsageSummaryResponse
from app.services.billing.usage_tracker import UsageTracker

router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/usage", response_model=BillingUsageSummaryResponse)
async def get_billing_usage(
    period: str = Query(default="month"),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tracker = UsageTracker(db=db)
    return await tracker.get_usage_summary(user.id, period=period)


@router.get("/history", response_model=BillingHistoryResponse)
async def get_billing_history(
    months: int = Query(default=6, ge=1, le=24),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    tracker = UsageTracker(db=db)
    return await tracker.get_usage_history(user.id, months=months)
