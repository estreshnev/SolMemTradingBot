"""Tests for webhook server."""

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


def make_raydium_tx(signature: str) -> dict:
    """Create a Helius transaction for testing."""
    return {
        "signature": signature,
        "type": "SWAP",
        "source": "RAYDIUM",
        "timestamp": 1706200000,
        "slot": 123456,
        "tokenTransfers": [],
        "nativeTransfers": [],
    }


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
        payload = {"transactions": [make_raydium_tx("test_sig_123")]}
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 1

    def test_duplicate_transactions_deduplicated(self, client: TestClient) -> None:
        payload = {
            "transactions": [
                make_raydium_tx("dup_sig_001"),
                make_raydium_tx("dup_sig_001"),
            ]
        }
        response = client.post("/webhook", json=payload)
        result = response.json()
        assert result["processed"] == 1
        assert result["duplicates"] == 1

    def test_list_format_accepted(self, client: TestClient) -> None:
        """Helius sends raw list, not wrapped in dict."""
        payload = [make_raydium_tx("list_sig_001")]
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 1