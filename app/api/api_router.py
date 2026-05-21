from typing import Annotated, Literal

from fastapi import APIRouter, Depends, Query, Response
from sqlalchemy.ext.asyncio import AsyncSession

from app.database.session import get_db
from app.schemas.schemas import (
    DepartmentBase,
    DepartmentCreate,
    DepartmentDetail,
    DepartmentPatch,
    EmployeeCreate,
    EmployeeResponse,
)
from app.api import utils

api_router = APIRouter(prefix="/departments", tags=["Departments"])

DbDep = Annotated[AsyncSession, Depends(get_db)]


@api_router.post("/", response_model=DepartmentBase, status_code=201, summary="Создать подразделение")
async def create_department(payload: DepartmentCreate, db: DbDep):
    dept = await utils.create_department(db, payload)
    return dept


@api_router.get("/{dept_id}", response_model=DepartmentDetail, summary="Получить подразделение")
async def get_department(
    dept_id: int,
    db: DbDep,
    depth: int = Query(default=1, ge=1, le=5, description="Глубина вложенных подразделений (1–5)"),
    include_employees: bool = Query(default=True, description="Включать сотрудников в ответ"),
):
    return await utils.get_department_detail(db, dept_id, depth, include_employees)


@api_router.patch("/{dept_id}", response_model=DepartmentBase, summary="Обновить подразделение")
async def patch_department(dept_id: int, payload: DepartmentPatch, db: DbDep):
    return await utils.patch_department(db, dept_id, payload)


@api_router.delete(
    "/{dept_id}",
    status_code=204,
    summary="Удалить подразделение",
    responses={204: {"description": "Успешно удалено"}},
)
async def delete_department(
    dept_id: int,
    db: DbDep,
    mode: Literal["cascade", "reassign"] = Query(
        ..., description="cascade — каскадное удаление; reassign — перевод сотрудников"
    ),
    reassign_to_department_id: int | None = Query(
        default=None, description="Обязателен при mode=reassign"
    ),
):
    await utils.delete_department(db, dept_id, mode, reassign_to_department_id)
    return Response(status_code=204)


@api_router.post(
    "/{dept_id}/employees/",
    response_model=EmployeeResponse,
    status_code=201,
    summary="Создать сотрудника",
)
async def create_employee(dept_id: int, payload: EmployeeCreate, db: DbDep):
    return await utils.create_employee(db, dept_id, payload)
