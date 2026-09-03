import uuid

from sqlalchemy import Boolean, ForeignKey, Integer, SmallInteger, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import UUID
from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy.sql import func

from app.db import Base


class CasCategoryYear(Base):
    __tablename__ = "cas_category_years"

    year: Mapped[int] = mapped_column(Integer, primary_key=True)


class CasCategory(Base):
    __tablename__ = "cas_categories"
    __table_args__ = (
        UniqueConstraint(
            "year", "major", "minor", "zone", "is_top", name="uq_cas_categories_tuple"
        ),
    )

    id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid()
    )
    year: Mapped[int] = mapped_column(
        Integer, ForeignKey("cas_category_years.year", ondelete="CASCADE"), nullable=False
    )
    major: Mapped[str] = mapped_column(String(64), nullable=False)
    minor: Mapped[str] = mapped_column(String(128), nullable=False)
    zone: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    is_top: Mapped[bool] = mapped_column(Boolean, nullable=False, server_default="false")


class JournalCasCategory(Base):
    __tablename__ = "journal_cas_categories"

    journal_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("journals.id", ondelete="CASCADE"),
        primary_key=True,
    )
    category_id: Mapped[uuid.UUID] = mapped_column(
        UUID(as_uuid=True),
        ForeignKey("cas_categories.id", ondelete="CASCADE"),
        primary_key=True,
    )
