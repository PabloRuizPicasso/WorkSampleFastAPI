from httpx import AsyncClient


async def test_db_connection(client):
    response = await client.get("/departments/")  # любой живой эндпоинт
    assert response.status_code != 500

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

async def create_department(client: AsyncClient, name: str, parent_id: int | None = None) -> dict:
    payload = {"name": name}
    if parent_id is not None:
        payload["parent_id"] = parent_id
    response = await client.post("/departments/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def create_employee(client: AsyncClient, department_id: int, full_name: str, position: str, hired_at: str | None = None) -> dict:
    payload = {"full_name": full_name, "position": position}
    if hired_at:
        payload["hired_at"] = hired_at
    response = await client.post(f"/departments/{department_id}/employees/", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


# ===========================================================================
# POST /departments/
# ===========================================================================


class TestCreateDepartment:

    async def test_create_root_department(self, client: AsyncClient):
        """Создаём корневое подразделение без parent_id."""
        response = await client.post("/departments/", json={"name": "Engineering"})
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Engineering"
        assert data["parent_id"] is None
        assert "id" in data

    async def test_create_child_department(self, client: AsyncClient):
        """Создаём дочернее подразделение."""
        parent = await create_department(client, "Engineering")
        print(f"\nparent: {parent}")
        response = await client.post("/departments/", json={"name": "Backend", "parent_id": parent["id"]})
        print(f"status: {response.status_code}")
        print(f"body: {response.text}")
        assert response.status_code == 201
        data = response.json()
        assert data["name"] == "Backend"
        assert data["parent_id"] == parent["id"]

    async def test_create_department_trims_whitespace(self, client: AsyncClient):
        """Пробелы по краям названия должны триммиться."""
        response = await client.post("/departments/", json={"name": "  DevOps  "})
        assert response.status_code == 201
        assert response.json()["name"] == "DevOps"

    async def test_create_department_empty_name(self, client: AsyncClient):
        """Пустое название — 422."""
        response = await client.post("/departments/", json={"name": ""})
        assert response.status_code == 422

    async def test_create_department_name_too_long(self, client: AsyncClient):
        """Название длиннее 200 символов — 422."""
        response = await client.post("/departments/", json={"name": "A" * 201})
        assert response.status_code == 422

    async def test_create_department_duplicate_name_same_parent(self, client: AsyncClient):
        """Два одинаковых названия в одном parent — 409."""
        parent = await create_department(client, "Engineering")
        await create_department(client, "Backend", parent["id"])
        response = await client.post("/departments/", json={"name": "Backend", "parent_id": parent["id"]})
        assert response.status_code == 409

    async def test_create_department_duplicate_name_different_parents(self, client: AsyncClient):
        """Одинаковые названия в разных parent — допустимо."""
        parent1 = await create_department(client, "Division A")
        parent2 = await create_department(client, "Division B")
        await create_department(client, "Backend", parent1["id"])
        response = await client.post("/departments/", json={"name": "Backend", "parent_id": parent2["id"]})
        assert response.status_code == 201

    async def test_create_department_nonexistent_parent(self, client: AsyncClient):
        """Несуществующий parent_id — 404."""
        response = await client.post("/departments/", json={"name": "Ghost", "parent_id": 99999})
        assert response.status_code == 404


# ===========================================================================
# POST /departments/{id}/employees/
# ===========================================================================

class TestCreateEmployee:

    async def test_create_employee(self, client: AsyncClient):
        """Создаём сотрудника в существующем подразделении."""
        dept = await create_department(client, "Engineering")
        response = await client.post(f"/departments/{dept['id']}/employees/", json={
            "full_name": "Ivan Petrov",
            "position": "Developer",
            "hired_at": "2023-01-15"
        })
        assert response.status_code == 201
        data = response.json()
        assert data["full_name"] == "Ivan Petrov"
        assert data["position"] == "Developer"
        assert data["hired_at"] == "2023-01-15"

    async def test_create_employee_without_hired_at(self, client: AsyncClient):
        """hired_at опционален."""
        dept = await create_department(client, "HR")
        response = await client.post(f"/departments/{dept['id']}/employees/", json={
            "full_name": "Anna Ivanova",
            "position": "HR Manager"
        })
        assert response.status_code == 201
        assert response.json()["hired_at"] is None

    async def test_create_employee_nonexistent_department(self, client: AsyncClient):
        """Сотрудник в несуществующем подразделении — 404."""
        response = await client.post("/departments/99999/employees/", json={
            "full_name": "Ghost User",
            "position": "Nobody"
        })
        assert response.status_code == 404

    async def test_create_employee_empty_full_name(self, client: AsyncClient):
        """Пустое full_name — 422."""
        dept = await create_department(client, "QA")
        response = await client.post(f"/departments/{dept['id']}/employees/", json={
            "full_name": "",
            "position": "Tester"
        })
        assert response.status_code == 422

    async def test_create_employee_empty_position(self, client: AsyncClient):
        """Пустая position — 422."""
        dept = await create_department(client, "QA")
        response = await client.post(f"/departments/{dept['id']}/employees/", json={
            "full_name": "Test User",
            "position": ""
        })
        assert response.status_code == 422

    async def test_create_employee_name_too_long(self, client: AsyncClient):
        """full_name длиннее 200 символов — 422."""
        dept = await create_department(client, "QA")
        response = await client.post(f"/departments/{dept['id']}/employees/", json={
            "full_name": "A" * 201,
            "position": "Tester"
        })
        assert response.status_code == 422


# ===========================================================================
# GET /departments/{id}
# ===========================================================================

class TestGetDepartment:

    async def test_get_department_basic(self, client: AsyncClient):
        """Базовое получение подразделения."""
        dept = await create_department(client, "Engineering")
        response = await client.get(f"/departments/{dept['id']}")
        assert response.status_code == 200
        data = response.json()
        assert data["id"] == dept["id"]
        assert data["name"] == "Engineering"

    async def test_get_department_includes_employees_by_default(self, client: AsyncClient):
        """По умолчанию include_employees=true."""
        dept = await create_department(client, "Engineering")
        await create_employee(client, dept["id"], "Ivan Petrov", "Developer")
        response = await client.get(f"/departments/{dept['id']}")
        assert response.status_code == 200
        data = response.json()
        assert "employees" in data
        assert len(data["employees"]) == 1
        assert data["employees"][0]["full_name"] == "Ivan Petrov"

    async def test_get_department_exclude_employees(self, client: AsyncClient):
        """include_employees=false — сотрудников нет в ответе."""
        dept = await create_department(client, "Engineering")
        await create_employee(client, dept["id"], "Ivan Petrov", "Developer")
        response = await client.get(f"/departments/{dept['id']}?include_employees=false")
        assert response.status_code == 200
        data = response.json()
        assert data.get("employees") == [] or "employees" not in data

    async def test_get_department_with_children_depth1(self, client: AsyncClient):
        """depth=1 — только прямые дети."""
        parent = await create_department(client, "Engineering")
        child = await create_department(client, "Backend", parent["id"])
        grandchild = await create_department(client, "Python Team", child["id"])

        response = await client.get(f"/departments/{parent['id']}?depth=1")
        assert response.status_code == 200
        data = response.json()
        children = data["children"]
        assert len(children) == 1
        assert children[0]["id"] == child["id"]
        # внук не должен быть в ответе
        assert children[0].get("children", []) == []

    async def test_get_department_with_children_depth2(self, client: AsyncClient):
        """depth=2 — дети и внуки."""
        parent = await create_department(client, "Engineering")
        child = await create_department(client, "Backend", parent["id"])
        grandchild = await create_department(client, "Python Team", child["id"])

        response = await client.get(f"/departments/{parent['id']}?depth=2")
        assert response.status_code == 200
        data = response.json()
        children = data["children"]
        assert len(children) == 1
        grandchildren = children[0]["children"]
        assert len(grandchildren) == 1
        assert grandchildren[0]["id"] == grandchild["id"]

    async def test_get_department_depth_max_5(self, client: AsyncClient):
        """depth > 5 — 422."""
        dept = await create_department(client, "Engineering")
        response = await client.get(f"/departments/{dept['id']}?depth=6")
        assert response.status_code == 422

    async def test_get_department_not_found(self, client: AsyncClient):
        """Несуществующий id — 404."""
        response = await client.get("/departments/99999")
        assert response.status_code == 404

    async def test_get_department_employees_sorted(self, client: AsyncClient):
        """Сотрудники отсортированы по full_name или created_at."""
        dept = await create_department(client, "Engineering")
        await create_employee(client, dept["id"], "Zara Smith", "Designer")
        await create_employee(client, dept["id"], "Anna Jones", "Developer")

        response = await client.get(f"/departments/{dept['id']}")
        assert response.status_code == 200
        employees = response.json()["employees"]
        names = [e["full_name"] for e in employees]
        assert names == sorted(names)  # проверяем алфавитный порядок


# ===========================================================================
# PATCH /departments/{id}
# ===========================================================================

class TestPatchDepartment:

    async def test_rename_department(self, client: AsyncClient):
        """Переименование подразделения."""
        dept = await create_department(client, "Engineering")
        response = await client.patch(f"/departments/{dept['id']}", json={"name": "Tech"})
        assert response.status_code == 200
        assert response.json()["name"] == "Tech"

    async def test_move_department_to_new_parent(self, client: AsyncClient):
        """Перемещение подразделения в другого родителя."""
        parent1 = await create_department(client, "Division A")
        parent2 = await create_department(client, "Division B")
        child = await create_department(client, "Backend", parent1["id"])

        response = await client.patch(f"/departments/{child['id']}", json={"parent_id": parent2["id"]})
        assert response.status_code == 200
        assert response.json()["parent_id"] == parent2["id"]

    async def test_cannot_set_self_as_parent(self, client: AsyncClient):
        """Нельзя сделать подразделение родителем самого себя — 409 или 400."""
        dept = await create_department(client, "Engineering")
        response = await client.patch(f"/departments/{dept['id']}", json={"parent_id": dept["id"]})
        assert response.status_code in (400, 409)

    async def test_cannot_create_cycle(self, client: AsyncClient):
        """Нельзя создать цикл: переместить родителя внутрь своего дочернего — 409 или 400."""
        parent = await create_department(client, "Engineering")
        child = await create_department(client, "Backend", parent["id"])

        # пытаемся переместить parent внутрь child — цикл
        response = await client.patch(f"/departments/{parent['id']}", json={"parent_id": child["id"]})
        assert response.status_code in (400, 409)

    async def test_patch_nonexistent_department(self, client: AsyncClient):
        """Patch несуществующего — 404."""
        response = await client.patch("/departments/99999", json={"name": "Ghost"})
        assert response.status_code == 404

    async def test_patch_duplicate_name_in_same_parent(self, client: AsyncClient):
        """Нельзя переименовать в уже существующее имя в том же parent — 409."""
        parent = await create_department(client, "Engineering")
        await create_department(client, "Backend", parent["id"])
        frontend = await create_department(client, "Frontend", parent["id"])

        response = await client.patch(f"/departments/{frontend['id']}", json={"name": "Backend"})
        assert response.status_code == 409


# ===========================================================================
# DELETE /departments/{id}
# ===========================================================================

class TestDeleteDepartment:

    async def test_delete_cascade(self, client: AsyncClient):
        """cascade — удаляет подразделение, детей и сотрудников."""
        parent = await create_department(client, "Engineering")
        child = await create_department(client, "Backend", parent["id"])
        await create_employee(client, child["id"], "Ivan Petrov", "Developer")

        response = await client.delete(f"/departments/{parent['id']}?mode=cascade")
        assert response.status_code in (200, 204)

        # проверяем что parent удалён
        assert (await client.get(f"/departments/{parent['id']}")).status_code == 404
        # проверяем что child удалён
        assert (await client.get(f"/departments/{child['id']}")).status_code == 404

    async def test_delete_reassign(self, client: AsyncClient):
        """reassign — сотрудники переходят в другое подразделение."""
        source = await create_department(client, "Old Dept")
        target = await create_department(client, "New Dept")
        employee = await create_employee(client, source["id"], "Ivan Petrov", "Developer")

        response = await client.delete(
            f"/departments/{source['id']}?mode=reassign&reassign_to_department_id={target['id']}"
        )
        assert response.status_code in (200, 204)

        # подразделение удалено
        assert (await client.get(f"/departments/{source['id']}")).status_code == 404

        # сотрудник теперь в target
        target_data = (await client.get(f"/departments/{target['id']}")).json()
        employee_ids = [e["id"] for e in target_data["employees"]]
        assert employee["id"] in employee_ids

    async def test_delete_reassign_without_target(self, client: AsyncClient):
        """reassign без reassign_to_department_id — 422."""
        dept = await create_department(client, "Engineering")
        response = await client.delete(f"/departments/{dept['id']}?mode=reassign")
        assert response.status_code == 422

    async def test_delete_reassign_nonexistent_target(self, client: AsyncClient):
        """reassign в несуществующий target — 404."""
        dept = await create_department(client, "Engineering")
        response = await client.delete(
            f"/departments/{dept['id']}?mode=reassign&reassign_to_department_id=99999"
        )
        assert response.status_code == 404

    async def test_delete_invalid_mode(self, client: AsyncClient):
        """Неверный mode — 422."""
        dept = await create_department(client, "Engineering")
        response = await client.delete(f"/departments/{dept['id']}?mode=invalid")
        assert response.status_code == 422

    async def test_delete_nonexistent_department(self, client: AsyncClient):
        """Удаление несуществующего — 404."""
        response = await client.delete("/departments/99999?mode=cascade")
        assert response.status_code == 404