"""Travel planner dataset model."""

from sqlalchemy import Integer, String, Text
from sqlalchemy.orm import Mapped, mapped_column

from core.database import Base


class TravelPlanner(Base):
    """Seed dataset loaded from test.csv."""

    __tablename__ = "travel_planner"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    org: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    dest: Mapped[str] = mapped_column(String(255), nullable=False, index=True)
    days: Mapped[int] = mapped_column(Integer, nullable=False)
    date: Mapped[str] = mapped_column(Text, nullable=False)
    query: Mapped[str] = mapped_column(Text, nullable=False)
    level: Mapped[str] = mapped_column(String(64), nullable=False)
    reference_information: Mapped[str] = mapped_column(Text, nullable=False)
