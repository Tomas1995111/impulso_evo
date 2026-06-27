"""Generador de mensaje semanal de balances clave (Argentina + USA)."""

import io
import logging
from collections import defaultdict
from datetime import datetime, timedelta

import pandas as pd
import requests

from core import config

logger = logging.getLogger(__name__)

DIAS_ES = {
    0: "Lunes",
    1: "Martes",
    2: "Miércoles",
    3: "Jueves",
    4: "Viernes",
    5: "Sábado",
    6: "Domingo",
}

argentina_top = {
    "GGAL", "YPFD", "BMA", "BBAR", "PAMP", "TGSU2", "TXAR", "SUPV", "COME", "BYMA",
    "CEPU", "ALUA", "TRAN", "LOMA", "EDN", "VALO", "METR", "IRSA", "TECO2", "TGNO4",
    "CRES", "MIRG", "BOLT", "AUSO", "SAMI", "MOLI", "RICH", "LEDE", "CVH", "BPAT",
    "DGCU2", "BHIP", "CELU", "AGRO", "PATA", "CECO2", "A3", "GRIM", "MORI", "HARG",
    "GBAN", "CGPA2", "DESP", "BIOX",
}

usa_top = {
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
    'XLU', 'INTC', 'PEP', 'UPS', 'ADBE', 'MDT', 'PFE', 'BABA', 'SBUX', 'CSX', 'PYPL',
    'WFC', 'DESP', 'BIOX',
    'SPCX', 'AMAT', 'TCEHY', 'LRCX', 'ARM', 'MS', 'HSBC', 'SNDK', 'NVS', 'AZN',
    'GEV', 'PM', 'RY', 'RTX', 'DELL', 'PANW', 'C', 'MRVL', 'MUFG', 'SHEL',
    'NVO', 'STX', 'WDC', 'BHP', 'TM', 'APH', 'ANET', 'CRWD', 'ABT', 'APP',
    'WELL', 'SCHW', 'T', 'IBKR', 'UBER', 'SHOP', 'DHR', 'CVS', 'PLD', 'UL',
    'CB', 'PGR', 'VRTX', 'ENB', 'BMY', 'SONY', 'FTNT', 'SO', 'PDD', 'HWM',
    'PBR', 'GSK', 'CM', 'BP', 'SPOT', 'BK', 'BCS', 'ITUB', 'ING', 'HOOD',
    'RCL', 'ABNB', 'SNOW', 'NET', 'CME', 'DASH', 'ECL', 'MDLZ', 'MCO', 'HLT',
    'NOK', 'CVNA', 'NOC', 'GM', 'XIACF', 'SLB', 'WBD', 'RACE', 'TGT', 'B',
    'DAL', 'F', 'MET', 'CTVA', 'NUE', 'RKLB', 'EA', 'ABEV', 'EBAY', 'VIK',
    'UAL', 'GRMN', 'CCL', 'CMG', 'MSCI', 'IRM', 'COIN', 'BBD', 'TRI', 'KMB',
    'BIDU', 'HMC', 'JD', 'RBLX', 'RDDT', 'VOD', 'BIIB', 'LVS', 'TWLO', 'KHC',
    'WSM', 'MRNA', 'PHG', 'DG', 'FSLR', 'LUV', 'TCOM', 'ZM', 'SOFI', 'ULTA',
    'TSN', 'ROKU', 'FOX', 'LTM'
}

tickers_filtro_estricto = argentina_top.union(usa_top)


def generar_mensaje_balances() -> str | None:
    """Genera el mensaje semanal de balances clave para Argentina y USA.

    Retorna un string formateado para WhatsApp o None si hay error.
    """
    desde_fecha = datetime.now()
    hasta_fecha = desde_fecha + timedelta(days=6)

    api_key = config.ALPHA_VANTAGE_API_KEY
    url = f"https://www.alphavantage.co/query?function=EARNINGS_CALENDAR&horizon=3month&apikey={api_key}"

    try:
        respuesta = requests.get(url, timeout=15)
    except requests.RequestException as e:
        logger.error("Error al consultar Alpha Vantage: %s", e)
        return None

    if "Thank you for using Alpha Vantage" in respuesta.text or "Note" in respuesta.text:
        logger.warning("Límite de Alpha Vantage alcanzado.")
        return "⚠️ *Balances*\nNo se pudo obtener el calendario de balances en este momento (rate limit). Intentá de nuevo más tarde."

    try:
        df = pd.read_csv(io.StringIO(respuesta.text))
    except Exception as e:
        logger.error("Error al procesar CSV de Alpha Vantage: %s", e)
        return None

    if df.empty:
        return _mensaje_sin_balances(desde_fecha, hasta_fecha)

    df['reportDate'] = pd.to_datetime(df['reportDate'])
    df_semanal = df[(df['reportDate'] >= desde_fecha) & (df['reportDate'] <= hasta_fecha)].copy()

    if df_semanal.empty:
        return _mensaje_sin_balances(desde_fecha, hasta_fecha)

    df_resumen = df_semanal[df_semanal['symbol'].isin(tickers_filtro_estricto)].copy()

    if df_resumen.empty:
        return _mensaje_sin_balances(desde_fecha, hasta_fecha)

    df_resumen = df_resumen.sort_values('reportDate')
    df_resumen['Origen'] = df_resumen['symbol'].apply(lambda x: 'ARG' if x in argentina_top else 'USA')
    df_resumen['dia_semana'] = df_resumen['reportDate'].apply(lambda x: DIAS_ES[x.weekday()])
    df_resumen['fecha_str'] = df_resumen['reportDate'].dt.strftime('%d/%m')

    por_dia = defaultdict(list)
    for _, row in df_resumen.iterrows():
        por_dia[(row['dia_semana'], row['fecha_str'])].append(row)

    return _formatear_mensaje(por_dia, desde_fecha, hasta_fecha)


def _mensaje_sin_balances(desde: datetime, hasta: datetime) -> str:
    return (
        f"📋 *Balances de la Semana* ({desde.strftime('%d/%m')} - {hasta.strftime('%d/%m')})\n\n"
        "✅ No hay balances de empresas clave programados para esta semana."
    )


def _formatear_mensaje(por_dia: dict, desde: datetime, hasta: datetime) -> str:
    partes = []
    header = f"📋 *Balances de la Semana* ({desde.strftime('%d/%m')} - {hasta.strftime('%d/%m')})"
    partes.append(header)

    for (dia, fecha_str), rows in por_dia.items():
        partes.append(f"\n📅 *{dia} {fecha_str}*")
        for row in rows:
            emoji = "🇦🇷" if row['Origen'] == 'ARG' else "🇺🇸"
            ticker = row['symbol']
            empresa = row.get('name', ticker)
            eps = row.get('estimate')
            eps_str = f" — EPS Est: *${eps:.2f}*" if pd.notna(eps) else ""
            partes.append(f"{emoji} *{ticker}* — {empresa}{eps_str}")

    return "\n".join(partes)


if __name__ == "__main__":
    msg = generar_mensaje_balances()
    print(msg)
