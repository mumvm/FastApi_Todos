import os
import sys
import asyncio
import json
import types

import pytest
from fastapi.testclient import TestClient

sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))
import main


@pytest.fixture(autouse=True)
def patch_storage(tmp_path, monkeypatch):
    todo_file = tmp_path / "todo.json"
    index_html = tmp_path / "index.html"
    monkeypatch.setattr(main, "TODO_FILE", todo_file)
    monkeypatch.setattr(main, "INDEX_HTML", index_html)
    yield {"todo_file": todo_file, "index_html": index_html}


@pytest.fixture
def client(patch_storage):
    return TestClient(main.app)


def test_ensure_todo_file_creates_when_missing(patch_storage):
    todo_file = patch_storage["todo_file"]
    assert not todo_file.exists()

    main.ensure_todo_file()

    assert todo_file.exists()
    assert json.loads(todo_file.read_text(encoding="utf-8")) == []


def test_ensure_todo_file_resets_corrupt_file(patch_storage):
    todo_file = patch_storage["todo_file"]
    todo_file.write_text("{ invalid json", encoding="utf-8")

    main.ensure_todo_file()

    assert json.loads(todo_file.read_text(encoding="utf-8")) == []


def test_save_and_load_round_trip(patch_storage):
    todos = [
        {
            "id": 1,
            "title": "Round trip",
            "description": "Save then load",
            "completed": False,
            "due_datetime": None,
            "category": "Work",
        }
    ]

    main.save_todos(todos)
    assert main.load_todos() == todos


def test_get_todos_empty(client):
    response = client.get("/todos")

    assert response.status_code == 200
    assert response.json() == []


def test_get_todos_with_items(client):
    main.save_todos(
        [
            {
                "id": 1,
                "title": "Test",
                "description": "Test description",
                "completed": False,
                "due_datetime": "2024-01-01T12:00",
                "category": "Work",
            }
        ]
    )

    response = client.get("/todos")

    assert response.status_code == 200
    body = response.json()
    assert len(body) == 1
    assert body[0]["title"] == "Test"
    assert body[0]["due_datetime"] == "2024-01-01T12:00"
    assert body[0]["category"] == "Work"


def test_create_todo_assigns_defaults(client):
    todo = {
        "title": "Test",
        "description": "Test description",
        "completed": False,
    }

    response = client.post("/todos", json=todo)

    assert response.status_code == 200
    created = response.json()
    assert created["title"] == "Test"
    assert created["category"] == "미분류"
    assert created["due_datetime"] is None
    assert created["id"] == 1


def test_create_todo_invalid_payload(client):
    response = client.post("/todos", json={"title": "Test"})

    assert response.status_code == 422


def test_update_todo_success(client):
    main.save_todos(
        [
            {
                "id": 1,
                "title": "Test",
                "description": "Test description",
                "completed": False,
                "due_datetime": None,
                "category": "Default",
            }
        ]
    )
    updated_todo = {
        "title": "Updated",
        "description": "Updated description",
        "completed": True,
        "due_datetime": "2024-05-05T10:30",
        "category": "UpdatedCat",
    }

    response = client.put("/todos/1", json=updated_todo)

    assert response.status_code == 200
    body = response.json()
    assert body["title"] == "Updated"
    assert body["due_datetime"] == "2024-05-05T10:30"
    assert body["category"] == "UpdatedCat"


def test_update_todo_not_found(client):
    updated_todo = {
        "title": "Updated",
        "description": "Updated description",
        "completed": True,
        "due_datetime": None,
        "category": "None",
    }

    response = client.put("/todos/1", json=updated_todo)

    assert response.status_code == 404


def test_delete_todo(client):
    main.save_todos(
        [
            {
                "id": 1,
                "title": "Test",
                "description": "Test description",
                "completed": False,
                "due_datetime": None,
                "category": "Default",
            }
        ]
    )

    response = client.delete("/todos/1")

    assert response.status_code == 200
    assert response.json()["message"] == "To-Do item deleted"
    assert main.load_todos() == []


def test_read_root_returns_index_content(client, patch_storage):
    index_html = patch_storage["index_html"]
    index_html.write_text("<h1>Hello</h1>", encoding="utf-8")

    response = client.get("/")

    assert response.status_code == 200
    assert "<h1>Hello</h1>" in response.text


def test_read_root_returns_fallback_when_missing(client):
    response = client.get("/")

    assert response.status_code == 200
    assert "index.html 파일이 없습니다" in response.text


def test_log_requests_records_message(monkeypatch, patch_storage):
    recorded = {}

    def fake_info(msg):
        recorded["msg"] = msg

    monkeypatch.setattr(main.custom_logger, "info", fake_info)
    request = types.SimpleNamespace(
        client=types.SimpleNamespace(host="127.0.0.1"),
        method="GET",
        url=types.SimpleNamespace(path="/todos"),
    )
    response = types.SimpleNamespace(status_code=204)

    async def call_next(req):
        return response

    result = asyncio.run(main.log_requests(request, call_next))

    assert result is response
    assert 'GET /todos' in recorded["msg"]
