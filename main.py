"""A SQLite-backed CRUD API for managing to-do tasks."""

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Annotated, Iterator

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


DATABASE_PATH = Path(__file__).with_name("tasks.db")
SEED_TASKS = [
    ("Learn SQLite", 1),
    ("Connect the CRUD API", 0),
    ("Verify persistence", 0),
]

app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small SQLite-backed CRUD API for a to-do list.",
)


class Task(BaseModel):
    """The task returned by the API."""

    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
    """The body accepted when creating a task."""

    model_config = ConfigDict(extra="forbid")
    title: str

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str) -> str:
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        return value


class TaskUpdate(BaseModel):
    """The body accepted when changing a task."""

    model_config = ConfigDict(extra="forbid")
    title: str | None = None
    done: bool | None = None

    @field_validator("title")
    @classmethod
    def title_must_not_be_empty(cls, value: str | None) -> str | None:
        if value is None:
            return value
        value = value.strip()
        if not value:
            raise ValueError("title must not be empty")
        return value

    @model_validator(mode="after")
    def at_least_one_field_is_supplied(self) -> "TaskUpdate":
        if self.title is None and self.done is None:
            raise ValueError("provide at least one of title or done")
        return self


class TaskNotFoundError(Exception):
    """Raised when a requested task ID does not exist."""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id


@contextmanager
def database() -> Iterator[sqlite3.Connection]:
    """Open a short-lived connection for each database operation."""
    connection = sqlite3.connect(DATABASE_PATH)
    connection.row_factory = sqlite3.Row
    try:
        yield connection
        connection.commit()
    finally:
        connection.close()


def task_from_row(row: sqlite3.Row) -> Task:
    return Task(id=row["id"], title=row["title"], done=bool(row["done"]))


def initialise_database() -> None:
    """Create the schema and add example tasks only when the table is empty."""
    with database() as connection:
        connection.execute(
            """
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY,
                title TEXT NOT NULL,
                done INTEGER NOT NULL CHECK (done IN (0, 1))
            )
            """
        )
        task_count = connection.execute("SELECT COUNT(*) FROM tasks").fetchone()[0]
        if task_count == 0:
            connection.executemany(
                "INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS
            )


# Create the database for imports and command-line tools as well as server startup.
initialise_database()


def get_task_or_404(task_id: int) -> Task:
    with database() as connection:
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    if row is None:
        raise TaskNotFoundError(task_id)
    return task_from_row(row)


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Use the assignment's 400 status for malformed or invalid request bodies."""
    return JSONResponse(status_code=400, content={"error": exc.errors()[0]["msg"]})


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(_: Request, exc: TaskNotFoundError) -> JSONResponse:
    """Return the assignment's JSON error shape for an unknown task."""
    return JSONResponse(status_code=404, content={"error": f"Task {exc.task_id} not found"})


@app.on_event("startup")
def create_database_on_startup() -> None:
    """Ensure a clean clone creates its database automatically on first run."""
    initialise_database()


@app.get("/", summary="Describe the API")
def root() -> dict[str, object]:
    """Return the Task API's name, version, and main endpoint."""
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Check server health")
def health() -> dict[str, str]:
    """Confirm that the server is running."""
    return {"status": "ok"}


@app.get("/tasks", response_model=list[Task], summary="List tasks")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    limit: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Task]:
    """List tasks, filtering and paginating with SQL when requested."""
    conditions: list[str] = []
    parameters: list[object] = []
    if done is not None:
        conditions.append("done = ?")
        parameters.append(int(done))
    if search:
        conditions.append("title LIKE ?")
        parameters.append(f"%{search}%")

    query = "SELECT id, title, done FROM tasks"
    if conditions:
        query += " WHERE " + " AND ".join(conditions)
    query += " ORDER BY id LIMIT ? OFFSET ?"
    parameters.extend([limit if limit is not None else -1, offset])

    with database() as connection:
        rows = connection.execute(query, parameters).fetchall()
    return [task_from_row(row) for row in rows]


@app.get("/tasks/{task_id}", response_model=Task, summary="Get one task")
def get_task(task_id: int) -> Task:
    """Return a task by its ID, or a JSON 404 error if it does not exist."""
    return get_task_or_404(task_id)


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create a task")
def create_task(new_task: TaskCreate) -> Task:
    """Insert a task and return the ID assigned by SQLite."""
    with database() as connection:
        cursor = connection.execute(
            "INSERT INTO tasks (title, done) VALUES (?, ?)", (new_task.title, 0)
        )
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (cursor.lastrowid,)
        ).fetchone()
    return task_from_row(row)


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, changes: TaskUpdate) -> Task:
    """Update the supplied task fields using parameterized SQL."""
    current = get_task_or_404(task_id)
    title = changes.title if changes.title is not None else current.title
    done = changes.done if changes.done is not None else current.done
    with database() as connection:
        connection.execute(
            "UPDATE tasks SET title = ?, done = ? WHERE id = ?",
            (title, int(done), task_id),
        )
        row = connection.execute(
            "SELECT id, title, done FROM tasks WHERE id = ?", (task_id,)
        ).fetchone()
    return task_from_row(row)


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
def delete_task(task_id: int) -> Response:
    """Delete a task and return no response body."""
    with database() as connection:
        cursor = connection.execute("DELETE FROM tasks WHERE id = ?", (task_id,))
    if cursor.rowcount == 0:
        raise TaskNotFoundError(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/stats", summary="Get task statistics")
def task_stats() -> dict[str, int]:
    """Calculate task statistics in SQLite rather than in Python."""
    with database() as connection:
        row = connection.execute(
            "SELECT COUNT(*) AS total, COALESCE(SUM(done), 0) AS done FROM tasks"
        ).fetchone()
    return {"total": row["total"], "done": row["done"], "open": row["total"] - row["done"]}


@app.post("/reset", response_model=list[Task], summary="Reset sample data")
def reset_tasks() -> list[Task]:
    """Restore the three example tasks with a single database transaction."""
    with database() as connection:
        connection.execute("DELETE FROM tasks")
        connection.executemany("INSERT INTO tasks (title, done) VALUES (?, ?)", SEED_TASKS)
        rows = connection.execute("SELECT id, title, done FROM tasks ORDER BY id").fetchall()
    return [task_from_row(row) for row in rows]
