"""Consulta rápida de cotización de acciones (sin SL ni desarmes)."""
from core import alerts


def generar_cotizacion_precio(ticker: str) -> str:
    data = alerts.fetch_stock_data(ticker)
    precio = data.get("precio_actual")
    var = data.get("variacion_pct")
    max_dia = data.get("max_dia")
    min_dia = data.get("min_dia")
    nombre = data.get("nombre") or ticker

    if precio is None:
        return f"❌ No se pudo obtener cotización de *{ticker}*."

    var_fmt = f"{var:+.2f}%" if var is not None else "—"
    flecha = " 📈" if (var or 0) > 0 else (" 📉" if (var or 0) < 0 else " ➡️")
    max_fmt = f"${max_dia:,.2f}" if max_dia else "—"
    min_fmt = f"${min_dia:,.2f}" if min_dia else "—"

    return (
        f"📊 *{ticker}* — {nombre}\n"
        f"Precio: ${precio:,.2f}\n"
        f"Variación: {var_fmt}{flecha}\n"
        f"Máx día: {max_fmt} | Mín día: {min_fmt}"
    )
