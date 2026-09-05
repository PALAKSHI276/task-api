"""A small in-memory CRUD API for managing to-do tasks."""

from typing import Annotated

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator, model_validator


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A small in-memory CRUD API for a to-do list.",
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


SEED_TASKS = [
    Task(id=1, title="Learn FastAPI", done=True),
    Task(id=2, title="Build a CRUD API", done=False),
    Task(id=3, title="Test it in Swagger UI", done=False),
]
tasks: list[Task] = [task.model_copy() for task in SEED_TASKS]


class TaskNotFoundError(Exception):
    """Raised when a requested task ID does not exist."""

    def __init__(self, task_id: int) -> None:
        self.task_id = task_id


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    """Use the assignment's 400 status for malformed or invalid request bodies."""
    message = exc.errors()[0]["msg"]
    return JSONResponse(status_code=400, content={"error": message})


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(_: Request, exc: TaskNotFoundError) -> JSONResponse:
    """Return the assignment's JSON error shape for an unknown task."""
    return JSONResponse(status_code=404, content={"error": f"Task {exc.task_id} not found"})


def get_task_or_404(task_id: int) -> Task:
    for task in tasks:
        if task.id == task_id:
            return task
    raise TaskNotFoundError(task_id)


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
    """List tasks, optionally filtering by completion status or title."""
    result = tasks
    if done is not None:
        result = [task for task in result if task.done == done]
    if search:
        result = [task for task in result if search.lower() in task.title.lower()]
    return result[offset:] if limit is None else result[offset : offset + limit]


@app.get("/tasks/{task_id}", response_model=Task, summary="Get one task")
def get_task(task_id: int) -> Task:
    """Return a task by its ID, or a JSON 404 error if it does not exist."""
    return get_task_or_404(task_id)


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create a task")
def create_task(new_task: TaskCreate) -> Task:
    """Create a task with the next ID and an initial `done` value of false."""
    next_id = max((task.id for task in tasks), default=0) + 1
    task = Task(id=next_id, title=new_task.title, done=False)
    tasks.append(task)
    return task


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, changes: TaskUpdate) -> Task:
    """Update a task title and/or completion status."""
    task = get_task_or_404(task_id)
    update_data = changes.model_dump(exclude_unset=True)
    updated = task.model_copy(update=update_data)
    tasks[tasks.index(task)] = updated
    return updated


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
def delete_task(task_id: int) -> Response:
    """Delete a task and return no response body."""
    task = get_task_or_404(task_id)
    tasks.remove(task)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/stats", summary="Get task statistics")
def task_stats() -> dict[str, int]:
    """Count all, completed, and open tasks."""
    done_count = sum(task.done for task in tasks)
    return {"total": len(tasks), "done": done_count, "open": len(tasks) - done_count}


@app.post("/reset", response_model=list[Task], summary="Reset sample data")
def reset_tasks() -> list[Task]:
    """Restore the three example tasks for a clean demo."""
    tasks[:] = [task.model_copy() for task in SEED_TASKS]
    return tasks
