from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_health_check():
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"


def test_upload_rejects_unsupported_file_type():
    response = client.post(
        "/upload",
        files={"file": ("test.png", b"fake image data", "image/png")},
    )
    assert response.status_code == 400


def test_list_documents_returns_list():
    response = client.get("/documents")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_list_conversations_returns_list():
    response = client.get("/conversations")
    assert response.status_code == 200
    assert isinstance(response.json(), list)