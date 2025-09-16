# main.py
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from pathlib import Path
import json

app = FastAPI()

BASE_DIR = Path(__file__).resolve().parent
INDEX_HTML = BASE_DIR / "templates/index.html"
TODO_FILE = BASE_DIR / "todo.json"

class TodoItem(BaseModel):
    id: int
    title: str
    description: str
    completed: bool

def init_json():
    if not TODO_FILE.exists():
        TODO_FILE.write_text("[]", encoding="utf-8")
        return
    try:
        json.loads(TODO_FILE.read_text(encoding="utf-8"))
    except json.JSONDecodeError:
        TODO_FILE.write_text("[]", encoding="utf-8")

# JSON 파일에서 To-Do 항목 로드
def load_todos():
    init_json()
    return json.loads(TODO_FILE.read_text(encoding="utf-8"))

# JSON 파일에 To-Do 항목 저장
def save_todos(todos):
    TODO_FILE.write_text(json.dumps(todos, indent=4, ensure_ascii=False), encoding="utf-8")

# To-Do 목록 조회
@app.get("/todos", response_model=list[TodoItem])
def get_todos():
    return load_todos()

# 신규 To-Do 항목 추가
@app.post("/todos", response_model=TodoItem)
def create_todo(todo: TodoItem):
    todos = load_todos()
    if any(t["id"] == todo.id for t in todos):
        raise HTTPException(status_code=400, detail="Duplicate id")
    todos.append(todo.dict())
    save_todos(todos)
    return todo

# To-Do 항목 수정
@app.put("/todos/{todo_id}", response_model=TodoItem)
def update_todo(todo_id: int, updated_todo: TodoItem):
    todos = load_todos()
    for i, t in enumerate(todos):
        if t["id"] == todo_id:
            todos[i] = updated_todo.dict()
            save_todos(todos)
            return updated_todo
    raise HTTPException(status_code=404, detail="To-Do item not found")

# To-Do 항목 삭제
@app.delete("/todos/{todo_id}")
def delete_todo(todo_id: int):
    # todos = load_todos()
    # new_todos = [t for t in todos if t["id"] != todo_id]
    # if len(new_todos) == len(todos):
    #     raise HTTPException(status_code=404, detail="To-Do item not found")
    # save_todos(new_todos)
    todos = load_todos()
    todos = [todo for todo in todos if todo["id"] != todo_id]
    save_todos(todos)
    return {"message": "To-Do item deleted"}

# HTML 파일 서빙
@app.get("/", response_class=HTMLResponse)
def read_root():
    with open("templates/index.html", "r") as file:
        content = file.read()
    return HTMLResponse(content=content)