"""A Postgres-backed CRUD API for managing to-do tasks."""

from typing import Annotated

from fastapi import FastAPI, Query, Request, Response, status
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse
from pydantic import BaseModel, ConfigDict, field_validator, model_validator

from repository import TaskNotFoundError, TaskRepository


app = FastAPI(
    title="Task API",
    version="1.0",
    description="A containerized Postgres-backed CRUD API for a to-do list.",
)
repository = TaskRepository()


class Task(BaseModel):
    id: int
    title: str
    done: bool


class TaskCreate(BaseModel):
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


def to_task(row: dict[str, object]) -> Task:
    return Task(id=int(row["id"]), title=str(row["title"]), done=bool(row["done"]))


@app.exception_handler(RequestValidationError)
async def validation_error_handler(_: Request, exc: RequestValidationError) -> JSONResponse:
    return JSONResponse(status_code=400, content={"error": exc.errors()[0]["msg"]})


@app.exception_handler(TaskNotFoundError)
async def task_not_found_handler(_: Request, exc: TaskNotFoundError) -> JSONResponse:
    return JSONResponse(status_code=404, content={"error": f"Task {exc.task_id} not found"})


@app.on_event("startup")
def initialise_postgres() -> None:
    """Create the table and seed example rows once after Postgres becomes available."""
    repository.initialise()


@app.get("/", summary="Describe the API")
def root() -> dict[str, object]:
    return {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}


@app.get("/health", summary="Check API and database health")
def health() -> dict[str, str]:
    repository.ping()
    return {"status": "ok", "db": "ok"}


@app.get("/tasks", response_model=list[Task], summary="List tasks")
def list_tasks(
    done: bool | None = None,
    search: str | None = None,
    limit: Annotated[int | None, Query(ge=1)] = None,
    offset: Annotated[int, Query(ge=0)] = 0,
) -> list[Task]:
    return [to_task(row) for row in repository.list(done, search, limit, offset)]


@app.get("/tasks/{task_id}", response_model=Task, summary="Get one task")
def get_task(task_id: int) -> Task:
    return to_task(repository.get(task_id))


@app.post("/tasks", response_model=Task, status_code=status.HTTP_201_CREATED, summary="Create a task")
def create_task(new_task: TaskCreate) -> Task:
    return to_task(repository.create(new_task.title))


@app.put("/tasks/{task_id}", response_model=Task, summary="Update a task")
def update_task(task_id: int, changes: TaskUpdate) -> Task:
    current = repository.get(task_id)
    return to_task(
        repository.update(
            task_id,
            changes.title if changes.title is not None else str(current["title"]),
            changes.done if changes.done is not None else bool(current["done"]),
        )
    )


@app.delete("/tasks/{task_id}", status_code=status.HTTP_204_NO_CONTENT, summary="Delete a task")
def delete_task(task_id: int) -> Response:
    repository.delete(task_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@app.get("/stats", summary="Get task statistics")
def task_stats() -> dict[str, int]:
    return repository.stats()


@app.post("/reset", response_model=list[Task], summary="Reset sample data")
def reset_tasks() -> list[Task]:
    return [to_task(row) for row in repository.reset()]
