# Task API

A SQLite-backed CRUD API for a to-do list, built with FastAPI. It continues the Week 2 API without changing its CRUD contract; only the storage layer has changed from an in-memory list to a database.

## Run it

Requires Python 3.10+.

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to use the generated Swagger UI. Use **Try it out** to run the full create, read, update, and delete cycle.

On the first start, the application creates `tasks.db`, creates the `tasks` table, and seeds three example tasks. SQLite was chosen because it is a single portable file, requires no separate database server or setup, and preserves data across server restarts. `tasks.db` is git-ignored so each clone starts fresh and creates its own database automatically.

## Endpoints

| Method | Endpoint | Purpose | Success status |
| --- | --- | --- | --- |
| GET | `/` | API description | 200 |
| GET | `/health` | Health check | 200 |
| GET | `/tasks` | List tasks; supports `done`, `search`, `limit`, `offset` | 200 |
| GET | `/tasks/{id}` | Get one task | 200 |
| POST | `/tasks` | Create a task | 201 |
| PUT | `/tasks/{id}` | Update title and/or done status | 200 |
| DELETE | `/tasks/{id}` | Delete a task | 204 |
| GET | `/stats` | Count total, done, and open tasks | 200 |
| POST | `/reset` | Restore the example data | 200 |

Missing tasks return a JSON 404 error. Invalid create or update bodies return a JSON 400 error.

## Example request

```console
$ curl -i -X POST http://localhost:8000/tasks -H "Content-Type: application/json" -d '{"title":"Buy milk"}'
HTTP/1.1 201 Created
content-type: application/json

{"id":4,"title":"Buy milk","done":false}
```

## Verify

```bash
python -m pytest -q
```

## SQLite query example

Open `tasks.db` in DB Browser for SQLite and run:

```sql
SELECT * FROM tasks WHERE done = 1;
```

This returns every completed task. Because the API and DB Browser access the same `tasks.db` file, manual changes are reflected by the API immediately.

## Persistence check

Create a task, stop the server, then run the same startup command again. `GET /tasks` still includes the task because it was inserted into SQLite instead of stored in application memory.

## AI vs me (bonus)

Not completed: this project intentionally contains only the hand-built FastAPI implementation.
