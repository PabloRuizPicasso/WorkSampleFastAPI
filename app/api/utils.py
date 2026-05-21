"""
Business logic for departments and employees.
All DB-level operations live here; routers stay thin.
"""
from __future__ import annotations

import logging
from typing import Literal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database.models import Department, Employee
from app.schemas.schemas import DepartmentCreate, DepartmentPatch, EmployeeCreate

logger = logging.getLogger(__name__)


# ── helpers ───────────────────────────────────────────────────────────────────

async def _get_dept_or_404(db: AsyncSession, dept_id: int) -> Department:
    result = await db.execute(select(Department).where(Department.id == dept_id))
    dept = result.scalar_one_or_none()
    if dept is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"Department {dept_id} not found")
    return dept


async def _check_name_unique(
    db: AsyncSession, name: str, parent_id: int | None, exclude_id: int | None = None
) -> None:
    """Raise 409 if a sibling department with the same name already exists."""
    stmt = select(Department).where(
        Department.name == name,
        Department.parent_id == parent_id,
    )
    if exclude_id is not None:
        stmt = stmt.where(Department.id != exclude_id)
    result = await db.execute(stmt)
    if result.scalar_one_or_none() is not None:
        from fastapi import HTTPException
        raise HTTPException(
            status_code=409,
            detail=f"A department named '{name}' already exists under the same parent.",
        )


async def _collect_subtree_ids(db: AsyncSession, root_id: int) -> set[int]:
    """Return all department IDs in the subtree rooted at root_id (inclusive)."""
    visited: set[int] = set()
    queue = [root_id]
    while queue:
        current = queue.pop()
        if current in visited:
            continue
        visited.add(current)
        result = await db.execute(
            select(Department.id).where(Department.parent_id == current)
        )
        queue.extend(result.scalars().all())
    return visited


async def _build_tree(
    db: AsyncSession,
    dept: Department,
    depth: int,
    include_employees: bool,
    current_depth: int = 0,
) -> dict:
    """Recursively build the department tree response dict."""
    data: dict = {
        "id": dept.id,
        "name": dept.name,
        "parent_id": dept.parent_id,
        "created_at": dept.created_at,
        "employees": [],
        "children": [],
    }

    if include_employees:
        result = await db.execute(
            select(Employee)
            .where(Employee.department_id == dept.id)
            .order_by(Employee.full_name)
        )
        data["employees"] = result.scalars().all()

    if current_depth < depth:
        result = await db.execute(
            select(Department).where(Department.parent_id == dept.id)
        )
        children = result.scalars().all()
        for child in children:
            data["children"].append(
                await _build_tree(db, child, depth, include_employees, current_depth + 1)
            )

    return data


# ── Department CRUD ───────────────────────────────────────────────────────────

async def create_department(db: AsyncSession, payload: DepartmentCreate) -> Department:
    if payload.parent_id is not None:
        await _get_dept_or_404(db, payload.parent_id)

    await _check_name_unique(db, payload.name, payload.parent_id)

    dept = Department(name=payload.name, parent_id=payload.parent_id)
    db.add(dept)
    await db.flush()
    await db.refresh(dept)
    logger.info("Created department id=%d name='%s'", dept.id, dept.name)
    return dept


async def get_department_detail(
    db: AsyncSession,
    dept_id: int,
    depth: int,
    include_employees: bool,
) -> dict:
    dept = await _get_dept_or_404(db, dept_id)
    return await _build_tree(db, dept, depth, include_employees)


async def patch_department(db: AsyncSession, dept_id: int, payload: DepartmentPatch) -> Department:
    dept = await _get_dept_or_404(db, dept_id)

    new_name = payload.name if payload.name is not None else dept.name
    # parent_id key presence check: if the field was set (even to None) apply it
    new_parent_id = payload.parent_id if payload.model_fields_set and "parent_id" in payload.model_fields_set else dept.parent_id

    # Validate new parent
    if new_parent_id is not None and new_parent_id != dept.parent_id:
        await _get_dept_or_404(db, new_parent_id)

    # Cycle detection: new parent cannot be inside dept's subtree
    if new_parent_id is not None:
        subtree = await _collect_subtree_ids(db, dept_id)
        if new_parent_id in subtree:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail="Cannot move a department into its own subtree (cycle detected).",
            )

    # Self-parent check
    if new_parent_id == dept_id:
        from fastapi import HTTPException
        raise HTTPException(status_code=409, detail="A department cannot be its own parent.")

    # Uniqueness among siblings
    await _check_name_unique(db, new_name, new_parent_id, exclude_id=dept_id)

    dept.name = new_name
    dept.parent_id = new_parent_id
    await db.flush()
    await db.refresh(dept)
    logger.info("Patched department id=%d", dept_id)
    return dept


async def delete_department(
    db: AsyncSession,
    dept_id: int,
    mode: Literal["cascade", "reassign"],
    reassign_to: int | None,
) -> None:
    dept = await _get_dept_or_404(db, dept_id)

    if mode == "reassign":
        if reassign_to is None:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=422,
                detail="reassign_to_department_id is required when mode=reassign",
            )
        target = await _get_dept_or_404(db, reassign_to)
        if target.id == dept_id:
            from fastapi import HTTPException
            raise HTTPException(
                status_code=409,
                detail="Cannot reassign employees to the department being deleted.",
            )

        # Move direct employees
        await db.execute(
            update(Employee)
            .where(Employee.department_id == dept_id)
            .values(department_id=reassign_to)
        )
        logger.info(
            "Reassigned employees from dept=%d to dept=%d", dept_id, reassign_to
        )

        # Re-parent children
        await db.execute(
            update(Department)
            .where(Department.parent_id == dept_id)
            .values(parent_id=dept.parent_id)
        )

    # cascade: SQLAlchemy cascade + DB ondelete handles children & employees
    await db.delete(dept)
    await db.flush()
    logger.info("Deleted department id=%d mode=%s", dept_id, mode)


# ── Employee CRUD ─────────────────────────────────────────────────────────────

async def create_employee(
    db: AsyncSession, dept_id: int, payload: EmployeeCreate
) -> Employee:
    await _get_dept_or_404(db, dept_id)

    emp = Employee(
        department_id=dept_id,
        full_name=payload.full_name,
        position=payload.position,
        hired_at=payload.hired_at,
    )
    db.add(emp)
    await db.flush()
    await db.refresh(emp)
    logger.info("Created employee id=%d in dept=%d", emp.id, dept_id)
    return emp
