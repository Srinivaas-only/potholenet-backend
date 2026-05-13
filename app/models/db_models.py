import uuid
from datetime import datetime, timezone

from sqlalchemy import Column, String, Float, Integer, Text, DateTime
from app.database import Base


class HazardReport(Base):
    """SQLAlchemy ORM model for pothole hazard reports."""

    __tablename__ = "hazard_reports"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    severity_score = Column(Integer, default=1)
    confidence = Column(Float, nullable=False)
    vehicle_type = Column(String, nullable=False)
    first_reported = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    last_seen = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )
    thumbnail_base64 = Column(Text, nullable=True)


class RetrainingContribution(Base):
    """SQLAlchemy ORM model for false-negative retraining submissions."""

    __tablename__ = "retraining_contributions"

    id = Column(String, primary_key=True, default=lambda: str(uuid.uuid4()))
    latitude = Column(Float, nullable=False)
    longitude = Column(Float, nullable=False)
    image_paths = Column(Text, nullable=False)  # JSON array of file paths
    created_at = Column(
        DateTime, default=lambda: datetime.now(timezone.utc)
    )