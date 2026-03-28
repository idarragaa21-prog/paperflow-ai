from __future__ import annotations

from pydantic import BaseModel, Field


class BillingModelUsageResponse(BaseModel):
    model: str
    calls: int
    tokens_in: int
    tokens_out: int
    total_tokens: int


class BillingRecentUsageResponse(BaseModel):
    preset: str | None = None
    tokens_in: int
    tokens_out: int
    total_tokens: int
    cost_usd: float
    models: list[dict] = Field(default_factory=list)
    at: str | None = None


class BillingUsageSummaryResponse(BaseModel):
    period: str
    month: str
    tier: str
    quota_calls: int
    calls_used: int
    quota_remaining: int
    tokens_in: int
    tokens_out: int
    total_tokens: int
    cost_usd: float
    models: list[BillingModelUsageResponse] = Field(default_factory=list)
    recent: list[BillingRecentUsageResponse] = Field(default_factory=list)


class BillingUsageMonthResponse(BaseModel):
    month: str
    calls: int
    tokens_in: int
    tokens_out: int
    total_tokens: int
    cost_usd: float


class BillingHistoryResponse(BaseModel):
    months: list[BillingUsageMonthResponse] = Field(default_factory=list)
