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


def make_pump_tx(signature: str, tx_type: str = "SWAP", token: str = "TestTokenpump") -> dict:
    """Create a valid Helius Pump.fun transaction for testing."""
    return {
        "signature": signature,
        "type": tx_type,
        "source": "PUMP_FUN",
        "timestamp": 1706200000,
        "slot": 123456,
        "feePayer": "TestCreator123",
        "tokenTransfers": [
            {
                "mint": token,
                "tokenAmount": 1000000.0,
                "fromUserAccount": "seller",
                "toUserAccount": "buyer",
            }
        ],
        "nativeTransfers": [
            {"amount": 100000000, "fromUserAccount": "buyer", "toUserAccount": "seller"}
        ],
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
        payload = {"transactions": [make_pump_tx("test_sig_123")]}
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 1

    def test_duplicate_transactions_deduplicated(self, client: TestClient) -> None:
        payload = {
            "transactions": [
                make_pump_tx("dup_sig_001"),
                make_pump_tx("dup_sig_001"),
            ]
        }
        response = client.post("/webhook", json=payload)
        result = response.json()
        assert result["processed"] == 1
        assert result["duplicates"] == 1

    def test_non_pump_fun_ignored(self, client: TestClient) -> None:
        """Transactions from other sources should be ignored."""
        payload = {
            "transactions": [
                {
                    "signature": "other_sig",
                    "type": "SWAP",
                    "source": "RAYDIUM",
                    "tokenTransfers": [],
                }
            ]
        }
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 0

    def test_list_format_accepted(self, client: TestClient) -> None:
        """Helius sends raw list, not wrapped in dict."""
        payload = [make_pump_tx("list_sig_001")]
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 1