from sqlalchemy import ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.database import Base


class Iteration(Base):
    """Represents one loop step within an execution."""

    __tablename__ = "iterations"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    execution_id: Mapped[int] = mapped_column(ForeignKey("executions.id"), nullable=False, index=True)
    iteration_number: Mapped[int] = mapped_column(Integer, nullable=False)
    prompt: Mapped[str] = mapped_column(String, nullable=False)
    response: Mapped[str | None] = mapped_column(String, nullable=True)
    evaluation: Mapped[str | None] = mapped_column(String, nullable=True)
    score: Mapped[float | None] = mapped_column(Integer, nullable=True)
