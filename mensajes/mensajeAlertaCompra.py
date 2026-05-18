# mensajesAlertaCompra.py
import yfinance as yf
import random
import math
import datetime
import time
import os
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Lista de acciones
tickers_top = [
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
    'XLU', 'INTC', 'PEP', 'UPS', 'ADBE', 'MDT', 'PFE', 'BABA', 'SBUX', 'CSX'
]

# ID de Google Sheet
SHEET_ID = os.getenv("SHEET_ID", "1Z9gfXGPdhBktLMwAIj4KpJ5SI2hDKK5lXG2Z63DaMSI")

# Guarda en Google Sheets
def guardar_en_gsheet(fecha, ticker, precio, stop_loss, sheet_id):
    try:
        scope = [
            "https://spreadsheets.google.com/feeds",
            "https://www.googleapis.com/auth/drive"
        ]
        creds = ServiceAccountCredentials.from_json_keyfile_name("mensajes/credenciales.json", scope)
        client = gspread.authorize(creds)
        sheet = client.open_by_key(sheet_id).sheet1

        fila_vacia = len(sheet.get_all_values()) + 1
        sheet.update(f"A{fila_vacia}", [[fecha, ticker, precio, stop_loss]])

        print(f"✅ Datos guardados en Google Sheet (fila {fila_vacia})")
    except Exception as e:
        import traceback
        print("❌ Error al guardar en Google Sheet:")
        traceback.print_exc()

# Obtiene info de la acción
def obtener_datos_accion(ticker):
    accion = yf.Ticker(ticker)
    info = accion.info

    datos = {
        "ticker": ticker,
        "nombre": info.get("shortName"),
        "precio_actual": info.get("regularMarketPrice"),
        "variacion_pct": info.get("regularMarketChangePercent"),
        "max_dia": info.get("dayHigh"),
        "min_dia": info.get("dayLow"),
        "max_historico": accion.history(period="max")["High"].max() if not accion.history(period="max").empty else None,
        "capitalizacion_bursatil": info.get("marketCap"),
        "pe_ratio": info.get("trailingPE"),
        "rendimiento_dividendos": info.get("dividendYield"),
        "sector": info.get("sector"),
        "recomendacion": info.get("recommendationKey"),
    }

    return datos

# Genera la alerta
def generar_alerta(datos):
    precio_actual = datos["precio_actual"]
    max_historico = datos["max_historico"]
    recomendacion = datos["recomendacion"]

    if recomendacion is None or recomendacion.lower() == "none":
        recomendacion = "buy"

    if recomendacion.lower() in ["buy", "strong_buy", "strongbuy"] and precio_actual < 0.8 * max_historico:
        PE = math.floor(precio_actual)
        SL_pct = -random.uniform(6, 14) / 100
        SL = math.floor(PE * (1 + SL_pct))
        R = abs(SL_pct)

        TP1 = math.floor(PE * (1 + R * 0.9))
        TP2 = math.floor(PE * (1 + R * 1.8))
        TP3 = math.floor(PE * (1 + R * 2.6))

        mensaje = f"""
📢 *ALERTA ANÁLISIS* // ESPECULATIVO 
👉🏼 Perfil Agresivo❗
•Ticker: *{datos['ticker']}* ({datos['nombre']}) 🇺🇸
•Zona de compra: {PE} USD
⛔ STOP LOSS = *{round(SL_pct * 100)}%*
✅ DESARMES: ( {TP1} USD / {TP2} USD / {TP3} USD )
- - - - - - - - - - - - - - - - - - - - - - 
Recuerde operar bajo su propio riesgo y en la justa y considerada proporción de su cartera. (la misma no configura ninguna recomendación)
"""
        fecha_actual = datetime.date.today().strftime("%Y-%m-%d")
        guardar_en_gsheet(fecha_actual, datos['ticker'], precio_actual, SL, SHEET_ID)

        return mensaje.strip()
    else:
        return None

# Prueba tickers aleatorios
def generar_alerta_aleatoria():
    tickers_restantes = tickers_top.copy()
    random.shuffle(tickers_restantes)

    for ticker in tickers_restantes:
        try:
            datos = obtener_datos_accion(ticker)
            mensaje = generar_alerta(datos)
            if mensaje:
                return mensaje
            time.sleep(1)
        except Exception as e:
            print(f"⚠️ Error con {ticker}: {e}")
    return None

# Ejecutar
if __name__ == "__main__":
    alerta = generar_alerta_aleatoria()
    if alerta:
        print(alerta)
    else:
        print("No hay alertas en este momento.")
