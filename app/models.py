from datetime import datetime

from sqlalchemy import DateTime, Float, ForeignKey, Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Location(Base):
    __tablename__ = "locations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    content_id: Mapped[str] = mapped_column(String(30), unique=True, index=True)
    content_type_id: Mapped[str] = mapped_column(String(10), index=True)
    category_name: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(300), index=True)
    address: Mapped[str | None] = mapped_column(String(500))
    address_detail: Mapped[str | None] = mapped_column(String(500))
    zipcode: Mapped[str | None] = mapped_column(String(20))
    telephone: Mapped[str | None] = mapped_column(String(300))
    longitude: Mapped[float | None] = mapped_column(Float)
    latitude: Mapped[float | None] = mapped_column(Float)
    sigungu_code: Mapped[str | None] = mapped_column(String(20), index=True)
    image_url: Mapped[str | None] = mapped_column(Text)
    thumbnail_url: Mapped[str | None] = mapped_column(Text)
    copyright_code: Mapped[str | None] = mapped_column(String(20))
    source_created_at: Mapped[str | None] = mapped_column(String(20))
    source_modified_at: Mapped[str | None] = mapped_column(String(20), index=True)


class Post(Base):
    __tablename__ = "posts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    category: Mapped[str] = mapped_column(String(30), index=True)
    title: Mapped[str] = mapped_column(String(200), index=True)
    content: Mapped[str] = mapped_column(Text)
    password_hash: Mapped[str] = mapped_column(String(300))
    location_id: Mapped[int | None] = mapped_column(ForeignKey("locations.id"), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.now, onupdate=datetime.now)
    location: Mapped[Location | None] = relationship()
