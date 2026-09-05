# Task API

A containerized FastAPI CRUD API backed by PostgreSQL. The API keeps the same endpoints introduced in Weeks 2 and 3; only the storage layer has changed, from memory to SQLite and now to Postgres.

## Run it

Requires Docker Desktop. Copy `.env.example` to `.env`, then start the complete API and database stack with one command:

```bash
docker compose up --build
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to use the generated Swagger UI. Use **Try it out** to run the full create, read, update, and delete cycle.

The API is available at `http://localhost:8000`, with Swagger UI at `http://localhost:8000/docs`. The `db` service runs Postgres, and the `taskdata` Docker volume preserves rows across `docker compose down` and `docker compose up`.

`.env` holds the database password and is deliberately git-ignored. `.env.example` documents the required variables without committing a real secret.

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

## Postgres query example

With the stack running, inspect the database directly:

```bash
docker compose exec db psql -U postgres -d tasks -c "SELECT * FROM tasks WHERE done = true;"
```

This returns every completed task. The API and `psql` access the same Postgres database, so manual changes are reflected by the API immediately.

## Persistence check

Create a task, run `docker compose down`, then run `docker compose up` again. `GET /tasks` still includes the task because the Docker volume preserves the Postgres data.

## AI vs me (bonus)

Not completed: this project intentionally contains only the hand-built FastAPI implementation.
