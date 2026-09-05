"""The Postgres storage layer for the Task API."""

from __future__ import annotations

import os
from contextlib import contextmanager
from typing import Iterator

import psycopg
from dotenv import load_dotenv
from psycopg.rows import dict_row


load_dotenv()
SEED_TASKS = [("Learn Docker", True), ("Connect Postgres", False), ("Run compose up", False)]


class TaskNotFoundError(Exception):
    def __init__(self, task_id: int) -> None:
        self.task_id = task_id


class TaskRepository:
    """All database access stays here so routes do not depend on Postgres details."""

    @staticmethod
    def database_url() -> str:
        url = os.getenv("DATABASE_URL")
        if not url:
            raise RuntimeError("DATABASE_URL is not set. Copy .env.example to .env.")
        return url

    @contextmanager
    def connection(self) -> Iterator[psycopg.Connection]:
        with psycopg.connect(self.database_url(), row_factory=dict_row) as connection:
            yield connection

    def initialise(self) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                """
                CREATE TABLE IF NOT EXISTS tasks (
                    id SERIAL PRIMARY KEY,
                    title TEXT NOT NULL,
                    done BOOLEAN NOT NULL DEFAULT FALSE
                )
                """
            )
            cursor.execute("SELECT COUNT(*) AS count FROM tasks")
            if cursor.fetchone()["count"] == 0:
                cursor.executemany("INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS)

    def ping(self) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT 1")

    def list(self, done: bool | None, search: str | None, limit: int | None, offset: int) -> list[dict[str, object]]:
        conditions: list[str] = []
        parameters: list[object] = []
        if done is not None:
            conditions.append("done = %s")
            parameters.append(done)
        if search:
            conditions.append("title ILIKE %s")
            parameters.append(f"%{search}%")
        query = "SELECT id, title, done FROM tasks"
        if conditions:
            query += " WHERE " + " AND ".join(conditions)
        query += " ORDER BY id LIMIT %s OFFSET %s"
        parameters.extend([limit if limit is not None else 2147483647, offset])
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(query, parameters)
            return list(cursor.fetchall())

    def get(self, task_id: int) -> dict[str, object]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT id, title, done FROM tasks WHERE id = %s", (task_id,))
            row = cursor.fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        return row

    def create(self, title: str) -> dict[str, object]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "INSERT INTO tasks (title, done) VALUES (%s, %s) RETURNING id, title, done",
                (title, False),
            )
            return cursor.fetchone()

    def update(self, task_id: int, title: str, done: bool) -> dict[str, object]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute(
                "UPDATE tasks SET title = %s, done = %s WHERE id = %s RETURNING id, title, done",
                (title, done, task_id),
            )
            row = cursor.fetchone()
        if row is None:
            raise TaskNotFoundError(task_id)
        return row

    def delete(self, task_id: int) -> None:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM tasks WHERE id = %s", (task_id,))
            if cursor.rowcount == 0:
                raise TaskNotFoundError(task_id)

    def stats(self) -> dict[str, int]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("SELECT COUNT(*) AS total, COUNT(*) FILTER (WHERE done) AS done FROM tasks")
            row = cursor.fetchone()
        return {"total": row["total"], "done": row["done"], "open": row["total"] - row["done"]}

    def reset(self) -> list[dict[str, object]]:
        with self.connection() as connection, connection.cursor() as cursor:
            cursor.execute("DELETE FROM tasks")
            cursor.executemany("INSERT INTO tasks (title, done) VALUES (%s, %s)", SEED_TASKS)
            cursor.execute("SELECT id, title, done FROM tasks ORDER BY id")
            return list(cursor.fetchall())
