"""Lógica compartida de alertas bursátiles (US y ARG)."""
import datetime
import logging
import math
import random
import time

import yfinance as yf

from core import config
from core import sheets_client

logger = logging.getLogger(__name__)

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

    hist = accion.history(period="1y")
    sma_50 = hist["Close"].rolling(50).mean().iloc[-1] if len(hist) >= 50 else None
    sma_200 = hist["Close"].rolling(200).mean().iloc[-1] if len(hist) >= 200 else None
    max_52w = hist["High"].max() if not hist.empty else None

    return {
        "ticker": ticker,
        "nombre": info.get("shortName"),
        "precio_actual": info.get("regularMarketPrice"),
        "variacion_pct": info.get("regularMarketChangePercent"),
        "max_dia": info.get("dayHigh"),
        "min_dia": info.get("dayLow"),
        "sma_50": sma_50,
        "sma_200": sma_200,
        "max_52w": max_52w,
        "capitalizacion_bursatil": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "rendimiento_dividendos": info.get("dividendYield"),
        "sector": info.get("sector"),
        "recomendacion": info.get("recommendationKey"),
    }


def _is_arg_ticker(ticker: str) -> bool:
    return ticker.upper().endswith(".BA")


def _calc_levels(precio: float, max_dia: float | None = None, min_dia: float | None = None) -> dict:
    """Calcula PE, stop loss y take profits basados en volatilidad diaria."""
    PE = math.floor(precio)

    # SL basado en rango diario, clamp 6%-18%
    raw_sl = 0.08
    if max_dia and min_dia and max_dia > min_dia:
        raw_sl = (max_dia - min_dia) * 2 / precio

    if raw_sl > 0.18:
        raise ValueError(f"SL calculado ({raw_sl*100:.0f}%) supera el máximo permitido de 18%")

    sl_pct = max(0.06, raw_sl)
    SL = round(PE * (1 - sl_pct))
    actual_pct = (PE - SL) / PE
    R = abs(actual_pct)

    return {
        "PE": PE,
        "SL": SL,
        "SL_pct": actual_pct,
        "TP1": round(PE * (1 + R * 0.9)),
        "TP2": round(PE * (1 + R * 1.8)),
        "TP3": round(PE * (1 + R * 2.6)),
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
    """Evalúa si el activo cumple condición de compra (score >= 3 de 4 criterios)."""
    precio = data.get("precio_actual")
    sma_50 = data.get("sma_50")
    sma_200 = data.get("sma_200")
    max_52w = data.get("max_52w")
    reco = data.get("recomendacion")

    if None in (precio, sma_50, sma_200):
        return False

    score = 0
    if precio > sma_50:
        score += 1
    if sma_50 > sma_200:
        score += 1
    if max_52w and 0.78 * max_52w < precio < 0.98 * max_52w:
        score += 1
    if reco and reco.lower() in ("buy", "strong_buy", "strongbuy"):
        score += 1

    return score >= 3


def generate_ticker_alert(ticker: str, sheet_id: str | None = None) -> str:
    """Genera alerta para un ticker sin filtrar por condición de compra."""
    data = fetch_stock_data(ticker)
    if not data.get("precio_actual"):
        return f"❌ No se pudieron obtener datos para {ticker}."
    try:
        levels = _calc_levels(data["precio_actual"], data.get("max_dia"), data.get("min_dia"))
    except ValueError as e:
        return f"❌ {ticker}: {e}"
    mensaje = build_alert_text(data, levels)

    fecha = datetime.date.today().strftime("%Y-%m-%d")
    sid = sheet_id or config.SHEET_ID
    try:
        sheets_client.append_alert_row(fecha, ticker, data["precio_actual"], levels["SL"], sid)
    except Exception:
            logger.exception("Error al guardar alerta de %s en Google Sheet", ticker)

    return mensaje


def search_alert_condition(tickers: list[str], sheet_id: str | None = None) -> str | None:
    """Busca aleatoriamente entre tickers el primero que cumpla condición de compra."""
    remaining = tickers.copy()
    random.shuffle(remaining)

    for ticker in remaining:
        try:
            data = fetch_stock_data(ticker)
            if _check_buy_condition(data):
                levels = _calc_levels(data["precio_actual"], data.get("max_dia"), data.get("min_dia"))
                mensaje = build_alert_text(data, levels)

                fecha = datetime.date.today().strftime("%Y-%m-%d")
                sid = sheet_id or config.SHEET_ID
                try:
                    sheets_client.append_alert_row(fecha, ticker, data["precio_actual"], levels["SL"], sid)
                except Exception:
                    logger.exception("Error al guardar alerta de %s en Google Sheet", ticker)

                return mensaje
            time.sleep(1)
        except Exception as e:
            logger.warning("Error con %s: %s", ticker, e)
    return None


def search_us_alert(*, sheet_id: str | None = None) -> str | None:
    """Busca aleatoriamente en tickers US. Para broadcast."""
    return search_alert_condition(TICKERS_US, sheet_id)


def search_arg_alert(*, sheet_id: str | None = None) -> str | None:
    """Busca aleatoriamente en tickers ARG. Para broadcast."""
    return search_alert_condition(TICKERS_ARG, sheet_id)


if __name__ == "__main__":
    alerta = search_us_alert() or search_arg_alert()
    logger.info(alerta or "No hay alertas en este momento.")
