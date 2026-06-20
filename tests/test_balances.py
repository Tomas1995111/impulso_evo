"""Tests para el mensaje de balances y el comando /balances."""

from __future__ import annotations

from datetime import datetime, timedelta
from unittest.mock import MagicMock, patch

import pandas as pd
import pytest

from flows.broadcast.broadcast import (
    MENSAJES_ESPECIALES,
    mensajes_semana,
    resolver_mensaje,
)


# ── Datos de prueba ──────────────────────────────────────────────────────────

FIXED_NOW = datetime(2026, 6, 22, 9, 0, 0)  # Lunes


def _make_earnings_df(rows: list[dict]) -> pd.DataFrame:
    df = pd.DataFrame(rows)
    if "reportDate" in df.columns:
        df["reportDate"] = pd.to_datetime(df["reportDate"])
    return df


def _sample_df() -> pd.DataFrame:
    return _make_earnings_df([
        {"reportDate": FIXED_NOW, "symbol": "GGAL", "name": "Grupo Financiero Galicia", "estimate": 45.20},
        {"reportDate": FIXED_NOW + timedelta(days=1), "symbol": "AAPL", "name": "Apple Inc.", "estimate": 1.52},
        {"reportDate": FIXED_NOW + timedelta(days=2), "symbol": "MSFT", "name": "Microsoft Corp.", "estimate": 2.90},
    ])


def _empty_df() -> pd.DataFrame:
    return pd.DataFrame(columns=["reportDate", "symbol", "name", "estimate"])


def _mock_response(csv_text: str = "") -> MagicMock:
    resp = MagicMock()
    resp.text = csv_text
    return resp


# ── Tests: generar_mensaje_balances ──────────────────────────────────────────

class TestGenerarMensajeBalances:
    @patch("mensajes.mensajeBalances.datetime")
    def test_formato_mensaje_con_datos(self, mock_dt):
        from mensajes.mensajeBalances import generar_mensaje_balances

        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        df = _sample_df()
        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=df):
            msg = generar_mensaje_balances()

        assert msg is not None
        assert isinstance(msg, str)
        assert "*Balances de la Semana*" in msg
        assert "📅" in msg
        assert "🇦🇷" in msg
        assert "🇺🇸" in msg
        assert "*GGAL*" in msg
        assert "*AAPL*" in msg
        assert "*MSFT*" in msg
        assert "EPS Est" in msg
        assert "$45.20" in msg
        assert "$1.52" in msg
        assert "$2.90" in msg

    @patch("mensajes.mensajeBalances.datetime")
    def test_agrupacion_por_dia(self, mock_dt):
        from mensajes.mensajeBalances import generar_mensaje_balances

        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        df = _make_earnings_df([
            {"reportDate": FIXED_NOW, "symbol": "GGAL", "name": "Galicia", "estimate": 10.0},
            {"reportDate": FIXED_NOW, "symbol": "YPFD", "name": "YPF", "estimate": 5.0},
            {"reportDate": FIXED_NOW + timedelta(days=3), "symbol": "AAPL", "name": "Apple", "estimate": 1.0},
        ])
        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=df):
            msg = generar_mensaje_balances()

        assert msg is not None
        assert msg.count("Lunes") == 1

    @patch("mensajes.mensajeBalances.datetime")
    def test_sin_balances_devuelve_mensaje_informativo(self, mock_dt):
        from mensajes.mensajeBalances import generar_mensaje_balances

        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=_empty_df()):
            msg = generar_mensaje_balances()

        assert msg is not None
        assert "No hay balances" in msg

    def test_api_error_retorna_none(self):
        from mensajes.mensajeBalances import generar_mensaje_balances
        import requests as req

        with patch("mensajes.mensajeBalances.requests.get", side_effect=req.ConnectionError("fail")):
            msg = generar_mensaje_balances()

        assert msg is None

    def test_rate_limit_devuelve_mensaje_aviso(self):
        from mensajes.mensajeBalances import generar_mensaje_balances

        resp = _mock_response("Thank you for using Alpha Vantage")
        with patch("mensajes.mensajeBalances.requests.get", return_value=resp):
            msg = generar_mensaje_balances()

        assert msg is not None
        assert "rate limit" in msg.lower()

    @patch("mensajes.mensajeBalances.datetime")
    def test_origen_arg_vs_usa(self, mock_dt):
        from mensajes.mensajeBalances import generar_mensaje_balances

        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        df = _make_earnings_df([
            {"reportDate": FIXED_NOW, "symbol": "GGAL", "name": "Galicia", "estimate": 10.0},
            {"reportDate": FIXED_NOW, "symbol": "AAPL", "name": "Apple", "estimate": 1.0},
        ])
        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=df):
            msg = generar_mensaje_balances()

        assert "🇦🇷 *GGAL*" in msg
        assert "🇺🇸 *AAPL*" in msg

    @patch("mensajes.mensajeBalances.datetime")
    def test_eps_none_no_muestra_eps(self, mock_dt):
        from mensajes.mensajeBalances import generar_mensaje_balances

        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        df = _make_earnings_df([
            {"reportDate": FIXED_NOW, "symbol": "GGAL", "name": "Galicia", "estimate": None},
        ])
        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=df):
            msg = generar_mensaje_balances()

        assert msg is not None
        assert "GGAL" in msg
        assert "EPS Est" not in msg


# ── Tests: integración con broadcast ────────────────────────────────────────

class TestBalancesEnBroadcast:
    def test_balances_en_especiales(self):
        assert "balances" in MENSAJES_ESPECIALES

    def test_balances_es_funcion(self):
        func = MENSAJES_ESPECIALES["balances"]
        assert callable(func)

    @patch("mensajes.mensajeBalances.datetime")
    def test_resolver_mensaje_balances(self, mock_dt):
        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=_empty_df()):
            resultado = resolver_mensaje("balances")

        assert isinstance(resultado, str)
        assert "Balances" in resultado

    def test_balances_lunes_0900_en_mensajes_semana(self):
        lunes = [m for m in mensajes_semana if m["mensaje"] == "balances"]
        assert len(lunes) == 1
        msg = lunes[0]
        assert "mon" in msg["dias"]
        assert msg["hora"] == "09:00"
        assert msg["grupo"] is not None

    def test_resolver_mensaje_con_error_devuelve_none(self):
        with patch.dict(
            "flows.broadcast.broadcast.MENSAJES_ESPECIALES",
            {"balances": MagicMock(side_effect=Exception("boom"))},
            clear=False,
        ):
            resultado = resolver_mensaje("balances")
        assert resultado is None


# ── Tests: comando /balances ─────────────────────────────────────────────────

class TestCmdBalances:
    @patch("mensajes.mensajeBalances.datetime")
    def test_cmd_balances_llama_funcion(self, mock_dt, mock_evolution_post):
        from flows.inbound.commands import handle_command

        mock_dt.now.return_value = FIXED_NOW
        mock_dt.side_effect = lambda *a, **k: datetime(*a, **k)
        mock_dt.strftime = datetime.strftime
        mock_dt.__class__ = datetime

        resp = _mock_response("reportDate,symbol,name,estimate\n")

        with patch("mensajes.mensajeBalances.requests.get", return_value=resp), \
             patch("mensajes.mensajeBalances.pd.read_csv", return_value=_sample_df()):
            result = handle_command("120363000000000000@g.us", "/balances")

        assert result is True
        assert mock_evolution_post.called

    def test_cmd_balances_api_error(self, mock_evolution_post):
        from flows.inbound.commands import handle_command
        import requests as req

        with patch("mensajes.mensajeBalances.requests.get", side_effect=req.ConnectionError("fail")):
            result = handle_command("120363000000000000@g.us", "/balances")

        assert result is True
        assert mock_evolution_post.called
