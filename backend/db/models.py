import uuid
from enum import Enum
from sqlalchemy import Column, String, Text, Integer, Boolean, DateTime, ForeignKey, JSON, Enum as SAEnum
from sqlalchemy.orm import declarative_base

Base = declarative_base()

class BollywoodType(Enum):
    STAR = "STAR"
    MOVIE = "MOVIE"

class BollywoodAsset(Base):
    __tablename__ = "bollywood_assets"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    name = Column(String(255), nullable=False)
    type = Column(SAEnum(BollywoodType, name="bollywood_type"), nullable=False)
    identifiers = Column(JSON, nullable=True)
    last_scan = Column(DateTime, nullable=True)

class TrendingReport(Base):
    __tablename__ = "trending_reports"

    id = Column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    asset_id = Column(String(36), ForeignKey("bollywood_assets.id"), nullable=False)
    source = Column(String(64), nullable=False)
    content = Column(Text, nullable=False)
    sentiment = Column(Integer, nullable=False)
    is_bot = Column(Boolean, nullable=False, default=False)
    url = Column(String(512), nullable=True)
