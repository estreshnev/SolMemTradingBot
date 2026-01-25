"""Tests for webhook server."""

import pytest
from fastapi.testclient import TestClient

from src.config import Settings
from src.webhook.server import MigrationParser, create_app


@pytest.fixture
def settings() -> Settings:
    return Settings()


@pytest.fixture
def client(settings: Settings) -> TestClient:
    app = create_app(settings)
    return TestClient(app)


def make_pump_fun_tx(
    signature: str,
    token_mint: str = "TokenMint123456789abcdefghijklmnopqrstuvwx",
    include_pool_program: bool = True,
) -> dict:
    """Create a Pump.fun migration transaction for testing."""
    tx: dict = {
        "signature": signature,
        "type": "SWAP",
        "source": "PUMP_FUN",
        "timestamp": 1706200000,
        "slot": 123456,
        "tokenTransfers": [
            {
                "mint": token_mint,
                "tokenAmount": 1000000.0,
                "fromUserAccount": "seller",
                "toUserAccount": "buyer",
            },
            {
                "mint": "So11111111111111111111111111111111111111112",
                "tokenAmount": 100.0,
                "fromUserAccount": "buyer",
                "toUserAccount": "seller",
            },
        ],
        "nativeTransfers": [],
        "accountKeys": [],
        "instructions": [],
    }

    if include_pool_program:
        tx["accountKeys"] = [
            {"pubkey": "675kPX9MHTjS2zt1qfr1NYHuzeLXfQM9H24wFSUt1Mp8"},  # Raydium AMM
        ]

    return tx


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
        payload = {"transactions": [make_pump_fun_tx("test_sig_123")]}
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        result = response.json()
        assert result["processed"] == 1
        assert result["migrations_detected"] == 1

    def test_duplicate_transactions_deduplicated(self, client: TestClient) -> None:
        payload = {
            "transactions": [
                make_pump_fun_tx("dup_sig_001"),
                make_pump_fun_tx("dup_sig_001"),
            ]
        }
        response = client.post("/webhook", json=payload)
        result = response.json()
        assert result["processed"] == 1
        assert result["duplicates"] == 1

    def test_non_pump_fun_ignored(self, client: TestClient) -> None:
        """Transactions from other sources should not be detected as migrations."""
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
        result = response.json()
        assert result["processed"] == 1
        assert result["migrations_detected"] == 0

    def test_list_format_accepted(self, client: TestClient) -> None:
        """Helius sends raw list, not wrapped in dict."""
        payload = [make_pump_fun_tx("list_sig_001")]
        response = client.post("/webhook", json=payload)
        assert response.status_code == 200
        assert response.json()["processed"] == 1


class TestMigrationParser:
    def test_parse_valid_migration(self) -> None:
        tx = make_pump_fun_tx("sig123", "MyTokenMint")
        result = MigrationParser.parse(tx)

        assert result is not None
        assert result.tx_signature == "sig123"
        assert result.token_mint == "MyTokenMint"

    def test_parse_non_pump_fun_returns_none(self) -> None:
        tx = {
            "signature": "sig123",
            "source": "RAYDIUM",
            "tokenTransfers": [],
        }
        result = MigrationParser.parse(tx)
        assert result is None

    def test_parse_no_token_mint_returns_none(self) -> None:
        tx = {
            "signature": "sig123",
            "source": "PUMP_FUN",
            "tokenTransfers": [],
            "accountData": [],
        }
        result = MigrationParser.parse(tx)
        assert result is None

    def test_skips_common_tokens(self) -> None:
        """Should skip wrapped SOL and return the memecoin mint."""
        tx = make_pump_fun_tx("sig123", "MyMemecoin")
        result = MigrationParser.parse(tx)

        assert result is not None
        assert result.token_mint == "MyMemecoin"
        # Should not return wrapped SOL
        assert result.token_mint != "So11111111111111111111111111111111111111112"