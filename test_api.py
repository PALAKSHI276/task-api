from fastapi.testclient import TestClient

from main import app


client = TestClient(app)


def setup_function() -> None:
    client.post("/reset")


def test_root_and_health() -> None:
    assert client.get("/").json() == {"name": "Task API", "version": "1.0", "endpoints": ["/tasks"]}
    assert client.get("/health").json() == {"status": "ok"}


def test_read_endpoints_and_missing_task() -> None:
    assert len(client.get("/tasks").json()) == 3
    assert client.get("/tasks/1").status_code == 200
    response = client.get("/tasks/99")
    assert response.status_code == 404
    assert response.json() == {"error": "Task 99 not found"}


def test_create_validates_and_returns_201() -> None:
    assert client.post("/tasks", json={}).status_code == 400
    assert client.post("/tasks", json={"title": "   "}).status_code == 400
    response = client.post("/tasks", json={"title": "Buy milk"})
    assert response.status_code == 201
    assert response.json() == {"id": 4, "title": "Buy milk", "done": False}


def test_update_delete_and_extras() -> None:
    response = client.put("/tasks/2", json={"title": "Ship API", "done": True})
    assert response.status_code == 200
    assert response.json() == {"id": 2, "title": "Ship API", "done": True}
    assert client.put("/tasks/2", json={}).status_code == 400
    assert client.put("/tasks/99", json={"done": True}).status_code == 404
    assert client.get("/tasks", params={"done": True}).json()[0]["id"] == 1
    assert client.get("/tasks", params={"search": "ship"}).json()[0]["id"] == 2
    assert client.get("/stats").json() == {"total": 3, "done": 2, "open": 1}
    assert client.delete("/tasks/2").status_code == 204
    assert client.delete("/tasks/99").status_code == 404
