"""Schemas for TERA Trust Shield disaster-fraud protection."""

from __future__ import annotations

from typing import Any, Literal

from pydantic import BaseModel, Field

RiskSeverity = Literal["info", "low", "medium", "high", "critical"]
TrustInputType = Literal["url", "message", "field_report", "supply_request"]
RiskLevel = Literal["low", "medium", "high", "critical"]


class RiskSignal(BaseModel):
    source: str
    severity: RiskSeverity
    code: str
    message: str


class UrlThreatResult(BaseModel):
    url: str
    checked: bool
    provider: str
    matched: bool
    threat_types: list[str] = Field(default_factory=list)
    raw: dict[str, Any] | None = None


class UrlReputationResult(BaseModel):
    url: str
    provider: str
    malicious: int | None = None
    suspicious: int | None = None
    harmless: int | None = None
    undetected: int | None = None
    raw: dict[str, Any] | None = None


class DomainReputationResult(BaseModel):
    domain: str
    provider: str
    reputation: int | None = None
    categories: dict[str, Any] | None = None
    raw: dict[str, Any] | None = None


class DomainMetadata(BaseModel):
    domain: str
    registrar: str | None = None
    created_at: str | None = None
    updated_at: str | None = None
    expires_at: str | None = None
    raw: dict[str, Any] | None = None


class UrlScanResult(BaseModel):
    url: str
    scan_id: str | None = None
    verdict: str | None = None
    contacted_domains: list[str] = Field(default_factory=list)
    screenshot_url: str | None = None
    raw: dict[str, Any] | None = None


class TrustAssessment(BaseModel):
    input_type: TrustInputType
    value: str
    risk_score: int = Field(..., ge=0, le=100)
    risk_level: RiskLevel
    signals: list[RiskSignal] = Field(default_factory=list)
    recommendation: str
    checked_sources: list[str] = Field(default_factory=list)
    skipped_sources: list[str] = Field(default_factory=list)
    requires_human_approval: bool


class UrlCheckRequest(BaseModel):
    url: str = Field(..., min_length=1, max_length=2048)
    context: str | None = Field(default=None, max_length=2000)


class MessageTrustRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    source: str | None = Field(default=None, max_length=200)


class SupplyRequestTrustRequest(BaseModel):
    request: dict[str, Any]
