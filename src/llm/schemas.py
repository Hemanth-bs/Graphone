"""
Canonical entity schemas for GraphOne / FrontierAtlas ingestion pipeline.

These mirror the expected entity schemas used by the ingestion pipeline.
Pydantic provides validation and JSON-schema generation for LLM extraction.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import List, Optional

from pydantic import BaseModel, Field


class RecordType(str, Enum):
    STARTUP = "STARTUP"
    PRODUCT = "PRODUCT"
    RESEARCH_PAPER = "RESEARCH_PAPER"
    JOB = "JOB"
    NEWS = "NEWS"


class PricingModel(str, Enum):
    FREE = "FREE"
    FREEMIUM = "FREEMIUM"
    PAID = "PAID"
    ENTERPRISE = "ENTERPRISE"


class SourceMeta(BaseModel):
    name: str = Field(
        ...,
        description="Name of the source site, e.g. 'TechCrunch'",
    )
    url: str = Field(
        ...,
        description="Original source URL this record was extracted from",
    )


class BaseEntity(BaseModel):
    schemaVersion: str = "1.0"
    recordType: RecordType
    source: SourceMeta
    collectedAt: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc)
    )


class StartupContentData(BaseModel):
    employeeCount: Optional[int] = None


class StartupContent(BaseModel):
    entityName: str
    data: StartupContentData = Field(
        default_factory=StartupContentData
    )


class StartupEntity(BaseEntity):
    recordType: RecordType = RecordType.STARTUP
    content: StartupContent


class ProductContent(BaseModel):
    startupName: str
    pricingModel: Optional[PricingModel] = None


class ProductEntity(BaseEntity):
    recordType: RecordType = RecordType.PRODUCT
    content: ProductContent


class ResearchPaperContent(BaseModel):
    title: str
    authors: List[str] = Field(default_factory=list)
    paper_url: str
    github_url: Optional[str] = None
    github_stars: Optional[int] = None
    published_date: Optional[datetime] = None


class ResearchPaperEntity(BaseEntity):
    recordType: RecordType = RecordType.RESEARCH_PAPER
    content: ResearchPaperContent


class JobContent(BaseModel):
    company: str
    date: Optional[datetime] = None
    is_remote: Optional[bool] = None
    role_family: Optional[str] = None


class JobEntity(BaseEntity):
    recordType: RecordType = RecordType.JOB
    content: JobContent


class NewsContent(BaseModel):
    title: str
    published_date: Optional[datetime] = None
    excerpt: Optional[str] = None


class NewsEntity(BaseEntity):
    recordType: RecordType = RecordType.NEWS
    content: NewsContent


SCHEMA_MAP = {
    RecordType.STARTUP: StartupEntity,
    RecordType.PRODUCT: ProductEntity,
    RecordType.RESEARCH_PAPER: ResearchPaperEntity,
    RecordType.JOB: JobEntity,
    RecordType.NEWS: NewsEntity,
}


def json_schema_for(record_type: RecordType) -> dict:
    """Return the content schema used in LLM extraction prompts."""
    model = SCHEMA_MAP[record_type]
    content_field = model.model_fields["content"].annotation
    return content_field.model_json_schema()