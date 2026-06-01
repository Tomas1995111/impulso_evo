"""Tests para el comando /precio (core/precio.py)."""

from unittest.mock import patch

import pytest


class TestGenerarCotizacionPrecio:
    def test_precio_valido_formatea_correctamente(self, mock_yfinance_ticker):
        from core.precio import generar_cotizacion_precio

        msg = generar_cotizacion_precio("AAPL")
        assert "AAPL" in msg
        assert "Test Corp" in msg
        assert "$150" in msg
        assert "📈" in msg
        assert "Máx día" in msg
        assert "Mín día" in msg

    def test_precio_variacion_negativa_muestra_flecha_roja(self):
        from core.precio import generar_cotizacion_precio
        import core.alerts as alerts

        with patch.object(alerts, "fetch_stock_data") as mock_fetch:
            mock_fetch.return_value = {
                "ticker": "KO",
                "nombre": "Coca-Cola Co",
                "precio_actual": 65.0,
                "variacion_pct": -2.3,
                "max_dia": 67.0,
                "min_dia": 64.0,
                "max_historico": 100.0,
                "capitalizacion_bursatil": 280000000000,
                "pe_ratio": 22.0,
                "rendimiento_dividendos": 0.03,
                "sector": "Consumer Defensive",
                "recomendacion": "buy",
            }
            msg = generar_cotizacion_precio("KO")
            assert "📉" in msg
            assert "%" in msg

    def test_precio_sin_datos_retorna_error(self):
        from core.precio import generar_cotizacion_precio
        import core.alerts as alerts

        with patch.object(alerts, "fetch_stock_data") as mock_fetch:
            mock_fetch.return_value = {
                "ticker": "INVALID",
                "nombre": None,
                "precio_actual": None,
                "variacion_pct": None,
                "max_dia": None,
                "min_dia": None,
            }
            msg = generar_cotizacion_precio("INVALID")
            assert "No se pudo" in msg

    def test_precio_sin_variacion_muestra_flecha_plana(self):
        from core.precio import generar_cotizacion_precio
        import core.alerts as alerts

        with patch.object(alerts, "fetch_stock_data") as mock_fetch:
            mock_fetch.return_value = {
                "ticker": "SPY",
                "nombre": "SPDR S&P 500",
                "precio_actual": 500.0,
                "variacion_pct": 0.0,
                "max_dia": 502.0,
                "min_dia": 498.0,
            }
            msg = generar_cotizacion_precio("SPY")
            assert "➡️" in msg
