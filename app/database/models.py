from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Integer, String, func
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.database.base import Base


class Department(Base):
    __tablename__ = "departments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    name: Mapped[str] = mapped_column(String(200), nullable=False)
    parent_id: Mapped[int | None] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="RESTRICT"),
        nullable=True,
        index=True,
    )
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    parent: Mapped["Department | None"] = relationship(
        "Department",
        back_populates="children",
        remote_side="Department.id",
        lazy="select",
    )
    children: Mapped[list["Department"]] = relationship(
        "Department",
        back_populates="parent",
        lazy="select",
        cascade="all, delete-orphan",
    )
    employees: Mapped[list["Employee"]] = relationship(
        "Employee",
        back_populates="department",
        lazy="select",
        cascade="all, delete-orphan",
    )


class Employee(Base):
    __tablename__ = "employees"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, index=True)
    department_id: Mapped[int] = mapped_column(
        Integer,
        ForeignKey("departments.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )
    full_name: Mapped[str] = mapped_column(String(200), nullable=False)
    position: Mapped[str] = mapped_column(String(200), nullable=False)
    #just for 1 migration
    email: Mapped[str] = mapped_column(String(200), nullable=True)
    hired_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # Relationships
    department: Mapped["Department"] = relationship(
        "Department",
        back_populates="employees",
        lazy="select",
    )
