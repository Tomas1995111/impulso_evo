"""Lógica compartida de alertas bursátiles (US y ARG)."""
import datetime
import math
import os
import random
import time
import traceback

import yfinance as yf

from core import config
from core import sheets_client

SHEET_ID = os.getenv("SHEET_ID", config.SHEET_ID)

TICKERS_US = [
    'NOW', 'SHW', 'COST', 'AZO', 'SNPS', 'META', 'LMT', 'CAT', 'TMO', 'UNH',
    'DE', 'ADSK', 'IBM', 'JPM', 'AAPL', 'UNP', 'HD', 'BLK', 'PNC', 'FDX',
    'NSC', 'AMZN', 'BRK-B', 'TMUS', 'CRM', 'MAR', 'RSG', 'EXPE', 'AXP', 'QCOM',
    'LOW', 'GE', 'CVX', 'RL', 'VST', 'LIN', 'CMI', 'ACN', 'MCD', 'MSFT', 'DIS',
    'JNJ', 'AMGN', 'HON', 'PG', 'MMM', 'BA', 'NVDA', 'KO', 'V', 'WMT',
    'VZ', 'GS', 'NKE', 'CSCO', 'MRK', 'NFLX', 'ASML', 'REGN', 'KLAC', 'BKNG',
    'MELI', 'MDB', 'MSTR', 'ZS', 'AMD', 'AVGO', 'GILD', 'TXN', 'TSLA', 'GOOG',
    'ROST', 'TTWO', 'WDAY', 'PLTR', 'CEG', 'MU', 'LLY', 'MCK', 'GOOGL', 'TSM',
    'MA', 'ORCL', 'XOM', 'SAP', 'BAC', 'ABBV', 'SPY', 'QQQ', 'DIA', 'IWM',
    'VTI', 'VEA', 'VWO', 'TLT', 'GLD', 'XLF', 'XLE', 'XLV', 'XLK', 'XLY',
    'XLU', 'INTC', 'PEP', 'UPS', 'ADBE', 'MDT', 'PFE', 'BABA', 'SBUX', 'CSX',
]

TICKERS_ARG = [
    "GGAL.BA", "YPFD.BA", "BMA.BA", "BBAR.BA", "PAMP.BA",
    "TGSU2.BA", "TXAR.BA", "SUPV.BA", "COME.BA", "BYMA.BA",
    "CEPU.BA", "ALUA.BA", "TRAN.BA", "LOMA.BA", "EDN.BA",
    "VALO.BA", "METR.BA", "IRSA.BA", "TECO2.BA", "TGNO4.BA",
    "CRES.BA", "MIRG.BA", "BOLT.BA", "AUSO.BA", "SAMI.BA",
    "MOLI.BA", "RICH.BA", "LEDE.BA", "CVH.BA", "BPAT.BA",
    "DGCU2.BA", "BHIP.BA", "CELU.BA", "AGRO.BA", "PATA.BA",
    "CECO2.BA", "A3.BA", "GRIM.BA", "MORI.BA", "HARG.BA",
    "GBAN.BA", "CGPA2.BA",
]


def fetch_stock_data(ticker: str) -> dict:
    """Obtiene datos de una acción via yfinance."""
    accion = yf.Ticker(ticker)
    info = accion.info

    hist = accion.history(period="max")
    max_historico = hist["High"].max() if not hist.empty else None

    return {
        "ticker": ticker,
        "nombre": info.get("shortName"),
        "precio_actual": info.get("regularMarketPrice"),
        "variacion_pct": info.get("regularMarketChangePercent"),
        "max_dia": info.get("dayHigh"),
        "min_dia": info.get("dayLow"),
        "max_historico": max_historico,
        "capitalizacion_bursatil": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "rendimiento_dividendos": info.get("dividendYield"),
        "sector": info.get("sector"),
        "recomendacion": info.get("recommendationKey"),
    }


def _is_arg_ticker(ticker: str) -> bool:
    return ticker.upper().endswith(".BA")


def _calc_levels(precio: float) -> dict:
    """Calcula PE, stop loss y take profits."""
    PE = math.floor(precio)
    SL_pct = -random.uniform(6, 14) / 100
    SL = math.floor(PE * (1 + SL_pct))
    R = abs(SL_pct)
    return {
        "PE": PE,
        "SL": SL,
        "SL_pct": SL_pct,
        "TP1": math.floor(PE * (1 + R * 0.9)),
        "TP2": math.floor(PE * (1 + R * 1.8)),
        "TP3": math.floor(PE * (1 + R * 2.6)),
    }


def build_alert_text(data: dict, levels: dict | None = None) -> str:
    """Arma el mensaje formateado de alerta."""
    if levels is None:
        levels = _calc_levels(data["precio_actual"])

    is_arg = _is_arg_ticker(data["ticker"])
    flag = "🇦🇷" if is_arg else "🇺🇸"
    moneda = "ARS" if is_arg else "USD"
    lv = levels

    return (
        f"📢 *ALERTA ANÁLISIS* // ESPECULATIVO \n"
        f"👉🏼 Perfil Agresivo❗\n"
        f"•Ticker: *{data['ticker']}* ({data['nombre']}) {flag}\n"
        f"•Zona de compra: {lv['PE']} {moneda}\n"
        f"⛔ STOP LOSS = *{round(lv['SL_pct'] * 100)}%*\n"
        f"✅ DESARMES: ( {lv['TP1']} {moneda} / {lv['TP2']} {moneda} / {lv['TP3']} {moneda} )\n"
        f"- - - - - - - - - - - - - - - - - - - - - - \n"
        f"Recuerde operar bajo su propio riesgo y en la justa y considerada proporción de su cartera. (la misma no configura ninguna recomendación)"
    )


def _check_buy_condition(data: dict) -> bool:
    """Evalúa si el activo cumple condición de compra (recomendación buy + descuento de max histórico)."""
    precio = data.get("precio_actual")
    max_hist = data.get("max_historico")
    reco = data.get("recomendacion")

    if max_hist is None or precio is None:
        return False
    if reco is None or str(reco).lower() == "none":
        reco = "buy"

    return reco.lower() in ("buy", "strong_buy", "strongbuy") and precio < 0.8 * max_hist


def generate_ticker_alert(ticker: str, sheet_id: str | None = None) -> str:
    """Genera alerta para un ticker sin filtrar por condición de compra."""
    data = fetch_stock_data(ticker)
    levels = _calc_levels(data["precio_actual"])
    mensaje = build_alert_text(data, levels)

    fecha = datetime.date.today().strftime("%Y-%m-%d")
    sid = sheet_id or SHEET_ID
    try:
        sheets_client.append_alert_row(fecha, ticker, data["precio_actual"], levels["SL"], sid)
    except Exception:
        print(f"❌ Error al guardar alerta de {ticker} en Google Sheet")
        traceback.print_exc()

    return mensaje


def search_alert_condition(tickers: list[str], sheet_id: str | None = None) -> str | None:
    """Busca aleatoriamente entre tickers el primero que cumpla condición de compra. (legacy)"""
    remaining = tickers.copy()
    random.shuffle(remaining)

    for ticker in remaining:
        try:
            data = fetch_stock_data(ticker)
            if _check_buy_condition(data):
                levels = _calc_levels(data["precio_actual"])
                mensaje = build_alert_text(data, levels)

                fecha = datetime.date.today().strftime("%Y-%m-%d")
                sid = sheet_id or SHEET_ID
                try:
                    sheets_client.append_alert_row(fecha, ticker, data["precio_actual"], levels["SL"], sid)
                except Exception:
                    print(f"❌ Error al guardar alerta de {ticker} en Google Sheet")
                    traceback.print_exc()

                return mensaje
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error con {ticker}: {e}")
    return None


def search_us_alert(*, sheet_id: str | None = None) -> str | None:
    """Busca aleatoriamente en tickers US. Para broadcast."""
    return search_alert_condition(TICKERS_US, sheet_id)


def search_arg_alert(*, sheet_id: str | None = None) -> str | None:
    """Busca aleatoriamente en tickers ARG. Para broadcast."""
    return search_alert_condition(TICKERS_ARG, sheet_id)


if __name__ == "__main__":
    alerta = search_us_alert() or search_arg_alert()
    print(alerta or "No hay alertas en este momento.")
