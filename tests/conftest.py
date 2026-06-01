"""Fixtures compartidos para tests de broadcast, CRM e inbound."""

from __future__ import annotations

import os
from typing import Generator
from unittest.mock import MagicMock, patch

import fakeredis
import pytest

os.environ["EVOLUTION_API_URL"] = "http://test:8080"
os.environ["EVOLUTION_API_KEY"] = "test-key"
os.environ["EVOLUTION_INSTANCE_NAME"] = "TestInstance"
os.environ["GRUPO_DEFAULT"] = "120363000000000000@g.us"
os.environ["GRUPO_PREMIUM"] = "120363000000000001@g.us"
os.environ["GRUPO_FREE"] = "120363000000000002@g.us"
os.environ["GRUPO_REVISION"] = "120363000000000003@g.us"
os.environ["SHEET_ID"] = "test-sheet-id"
os.environ["LEADS_SHEET_ID"] = "test-leads-sheet"
os.environ["LEADS_SHEET_TAB"] = "Maestro"
os.environ["TRIAL_GROUP_JID"] = "120363000000000004@g.us"
os.environ["INBOUND_WEBHOOK_SECRET"] = ""
os.environ["GEMINI_API_KEY"] = "test-gemini-key"


@pytest.fixture
def fake_redis() -> fakeredis.FakeRedis:
    return fakeredis.FakeRedis(decode_responses=True)


@pytest.fixture
def mock_evolution_post() -> Generator[MagicMock, None, None]:
    with patch("core.evolution_client.requests.post") as mock:
        mock.return_value.status_code = 200
        mock.return_value.ok = True
        mock.return_value.json.return_value = {}
        yield mock


@pytest.fixture
def mock_evolution_get() -> Generator[MagicMock, None, None]:
    with patch("core.evolution_client.requests.get") as mock:
        mock.return_value.status_code = 200
        mock.return_value.json.return_value = {"instance": {"state": "open"}}
        yield mock


@pytest.fixture
def mock_sheets_append() -> Generator[MagicMock, None, None]:
    with patch("core.sheets_client.append_lead_row") as mock:
        yield mock


@pytest.fixture(autouse=True)
def mock_phone_exists() -> Generator[MagicMock, None, None]:
    """Por defecto, phone_exists() retorna False (número no registrado).
    Tests específicos pueden sobreescribir con @patch directo."""
    with patch("core.sheets_client.phone_exists", return_value=False) as mock:
        yield mock


@pytest.fixture
def mock_yfinance_ticker() -> Generator[MagicMock, None, None]:
    mock_ticker = MagicMock()
    mock_info = {
        "shortName": "Test Corp",
        "regularMarketPrice": 150.0,
        "regularMarketChangePercent": 1.5,
        "dayHigh": 155.0,
        "dayLow": 148.0,
        "marketCap": 1000000000,
        "trailingPE": 20.0,
        "dividendYield": 0.02,
        "sector": "Technology",
        "recommendationKey": "buy",
    }
    mock_ticker.info = mock_info
    mock_history = MagicMock()
    mock_history.empty = False
    mock_history.__getitem__.return_value.max.return_value = 200.0
    mock_ticker.history.return_value = mock_history

    with patch("yfinance.Ticker", return_value=mock_ticker):
        yield
