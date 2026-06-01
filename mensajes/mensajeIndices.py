import logging

import yfinance as yf
yf.set_tz_cache_location("/tmp")
from datetime import datetime

logger = logging.getLogger(__name__)

def generar_mensaje_indices():
    tickers = {
        "^GSPC": "S&P 500",
        "^IXIC": "Nasdaq",
        "^DJI": "Dow Jones",
        "^VIX": "VIX (volatilidad)",
        "CL=F": "Petróleo WTI",
        "GC=F": "Oro",
        "ZS=F": "Soja",
        "^TNX": "Bono 10Y USA",
        "^IRX": "Bono 3M USA",
        "BTC-USD": "Bitcoin",
        "ETH-USD": "Ethereum"
    }

    categorias = {
        "📊 *Índices Globales*": ["^GSPC", "^IXIC", "^DJI", "^VIX"],
        "🛢️ *Materias Primas*": ["CL=F", "GC=F", "ZS=F"],
        "📊 *Tasas USA*": ["^TNX", "^IRX"],
        "🪙 *Criptomonedas*": ["BTC-USD", "ETH-USD"]
    }

    # Descargamos datos con group_by para mejor formato
    try:
        data = yf.download(
            tickers=list(tickers.keys()),
            period="3d",
            interval="1d",
            group_by="ticker",
            threads=True
        )
    except Exception:
        logger.exception("No se pudo obtener información del mercado.")
        raise

    if data.empty:
        logger.error("Datos vacíos del mercado.")
        raise RuntimeError("No se pudo obtener información del mercado.")

    mensaje = f"📈 *Impulso del Mercado - {datetime.today().strftime('%d/%m/%Y')}*\n\n"

    sp500 = nasdaq = oro = btc = vix = tasa = None

    for categoria, lista in categorias.items():
        mensaje += f"{categoria}\n"
        for t in lista:
            try:
                precios = data[t]["Close"].dropna()
                if len(precios) < 2:
                    mensaje += f"• ⚠️ *{tickers[t]}*: sin datos recientes.\n"
                    continue

                ayer, hoy = precios.iloc[-2], precios.iloc[-1]
                var = (hoy - ayer) / ayer * 100

                if var > 0.2:
                    emoji = f"🟢 {var:+.2f}%"
                elif var < -0.2:
                    emoji = f"🔴 {var:+.2f}%"
                else:
                    emoji = f"⚪ {var:+.2f}%"

                nombre = tickers[t]
                mensaje += f"• ➖ *{nombre}*: {hoy:.2f} ({emoji})\n"

                if t == "^GSPC": sp500 = var
                if t == "^IXIC": nasdaq = var
                if t == "GC=F": oro = var
                if t == "BTC-USD": btc = var
                if t == "^VIX": vix = var
                if t == "^TNX": tasa = var

            except Exception as e:
                mensaje += f"• ⚠️ *{tickers[t]}*: error ({str(e)}).\n"
        mensaje += "\n"

    # 🧠 Pulso del mercado
    mensaje += "🧠 *Pulso del mercado*:\n"

    if sp500 is not None and nasdaq is not None:
        if sp500 < -0.3 and nasdaq < -0.3:
            mensaje += "📉 Wall Street retrocediento, cierto pesimismo en la jornada.\n"
        elif sp500 > 0.3 and nasdaq > 0.3:
            mensaje += "📈 Buen avance en Wall Street, impulsos desde el sector tecnológico.\n"
        elif sp500 > 0.3 or nasdaq > 0.3:
            mensaje += "📊 Jornada mixta en EE.UU., sin dirección clara.\n"
        else:
            mensaje += "🔹 Sesión estable, sin grandes movimientos en los índices.\n"

    if oro is not None and oro > 0.5:
        mensaje += "🟡 El oro sube, señales de refugio.\n"
    if btc is not None:
        if btc > 1:
            mensaje += "₿ Bitcoin en alza, vuelve el apetito por riesgo.\n"
        elif btc < -1:
            mensaje += "₿ Bitcoin en baja, se enfría el entusiasmo cripto.\n"
    if vix is not None:
        if vix > 5:
            mensaje += "⚠️ La volatilidad se dispara, tensión en el aire, VIX al alza.\n"
        elif vix < -3:
            mensaje += "😌 El VIX baja fuerte, menor volatilidad, señales de calma.\n"
    if tasa is not None:
        if tasa > 1:
            mensaje += "💥 Las tasas largas suben, hay presión para el mercado.\n"
        elif tasa < -1:
            mensaje += "📉 Baja en tasas, posible alivio para activos de riesgo.\n"

    return mensaje.strip()

if __name__ == "__main__":
    print("\n" + generar_mensaje_indices() + "\n")
