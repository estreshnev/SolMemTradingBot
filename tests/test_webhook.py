import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.webhook.server import create_app


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    return TestClient(app)


class TestHealthEndpoint:
    def test_health_returns_ok(self, client: TestClient) -> None:
        response = client.get("/health")
        assert response.status_code == 200
        assert response.json()["status"] == "healthy"


class TestWebhookEndpoint:
    def test_empty_payload(self, client: TestClient) -> None:
        response = client.post("/webhook", json={"transactions": []})
        assert response.status_code == 200
        assert response.json()["processed"] == 0

    def test_single_transaction(self, client: TestClient) -> None:
        payload = {
            "transactions": [
                {
                    "signature": "test_sig_123",
                    "type": "create",
                    "tokenAddress": "TokenABC",
                    "creator": "CreatorXYZ",
                }
            ]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 1

    def test_duplicate_transactions_deduplicated(self, client: TestClient) -> None:
        payload = {
            "transactions": [
                {"signature": "dup_sig", "type": "create", "tokenAddress": "Token1"},
                {"signature": "dup_sig", "type": "create", "tokenAddress": "Token1"},
            ]
        }
        response = client.post("/webhook", json=payload)
        result = response.json()
        assert result["processed"] == 1
        assert result["duplicates"] == 1
