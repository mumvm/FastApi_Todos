from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
import json
import os
from prometheus_fastapi_instrumentator import Instrumentator

app = FastAPI()

# Prometheus 메트릭스 엔드포인트 (/metrics)
Instrumentator().instrument(app).expose(app, endpoint="/metrics")

BASE_DIR = Path(__file__).resolve().parent
INDEX_HTML = BASE_DIR / "templates/index.html"
TODO_FILE = BASE_DIR / "todo.json"


# To-Do 항목 모델
class TodoItem(BaseModel):
    id: int | None = None
    title: str
    description: str
    completed: bool


def ensure_todo_file():
    """todo.json이 없거나 깨져 있으면 초기화"""
    if not TODO_FILE.exists():
        TODO_FILE.write_text("[]", encoding="utf-8")
        return
    try:
        json.loads(TODO_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        TODO_FILE.write_text("[]", encoding="utf-8")


def load_todos():
    ensure_todo_file()
    return json.loads(TODO_FILE.read_text(encoding="utf-8"))


def save_todos(todos):
    TODO_FILE.write_text(
        json.dumps(todos, indent=4, ensure_ascii=False),
        encoding="utf-8"
    )


@app.get("/todos")
def get_todos():
    return load_todos()


@app.post("/todos")
def create_todo(todo: TodoItem):
    todos = load_todos()
    new_id = max([t["id"] for t in todos], default=0) + 1
    new_todo = {
        "id": new_id,
        "title": todo.title,
        "description": todo.description,
        "completed": todo.completed,
    }
    todos.append(new_todo)
    save_todos(todos)
    return new_todo


@app.put("/todos/{todo_id}")
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for i, t in enumerate(todos):
        if t.get("id") == todo_id:
            todos[i] = {
                "id": todo_id,
                "title": updated_todo.title,
                "description": updated_todo.description,
                "completed": updated_todo.completed,
            }
            save_todos(todos)
            return todos[i]
    raise HTTPException(status_code=404, detail="To-Do item not found")


@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    todos = load_todos()
    new_todos = [t for t in todos if t.get("id") != todo_id]
    save_todos(new_todos)
    return {"message": "To-Do item deleted"}   # 항상 200 반환


@app.get("/", response_class=HTMLResponse)
def read_root():
    try:
        return INDEX_HTML.read_text(encoding="utf-8")
    except FileNotFoundError:
        return HTMLResponse("<h1>index.html 파일이 없습니다</h1>", status_code=200)