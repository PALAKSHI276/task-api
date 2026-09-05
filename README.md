# Task API

A small in-memory CRUD API for a to-do list, built with FastAPI. Data resets whenever the server restarts; this is intentional for this assignment.

## Run it

Requires Python 3.10+.

```bash
python -m pip install -r requirements.txt
python -m uvicorn main:app --reload
```

Open [http://localhost:8000/docs](http://localhost:8000/docs) to use the generated Swagger UI. Use **Try it out** to run the full create, read, update, and delete cycle.

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

## Swagger UI screenshot

Start the API and open `/docs`. The generated Swagger UI documents every endpoint and provides an interactive **Try it out** workflow.

## AI vs me (bonus)

Not completed: this project intentionally contains only the hand-built FastAPI implementation.
